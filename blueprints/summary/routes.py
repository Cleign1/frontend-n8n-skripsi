import datetime
import json
import redis
from flask import Blueprint, render_template, jsonify, current_app
from .task import run_gcs_summary_task
from ..tasks.utils import store_task_info

summary_bp = Blueprint('summary', __name__, template_folder='../../templates')


@summary_bp.route('/rangkuman')
def rangkuman():
    """
    Renders the summary agent page, now with a list of historical tasks.
    """
    try:
        redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                                   decode_responses=True)
        task_history_json = redis_client.lrange('gcs_summary_tasks', 0, -1)
        tasks = [json.loads(item) for item in task_history_json]
    except redis.exceptions.ConnectionError:
        tasks = []  # If Redis is down, show an empty list instead of crashing
    return render_template('rangkuman.html', tasks=tasks)


@summary_bp.route('/summary/start', methods=['POST'])
def start_summary():
    """
    Triggers the background task and logs it to the history list.
    """
    try:
        task = run_gcs_summary_task.delay()

        # Log for the main /tasks page
        task_name = f"GCS Summary Agent - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        store_task_info(task.id, task_name, "GCS Latest File", datetime.datetime.now().isoformat())

        # Log for the new history table on the rangkuman page
        redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                                   decode_responses=True)
        task_data = {
            "task_id": task.id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        redis_client.lpush('gcs_summary_tasks', json.dumps(task_data))

        return jsonify({
            "message": "Summary agent task has been started.",
            "task_id": task.id
        }), 202
    except Exception as e:
        return jsonify({"error": f"Failed to start summary agent task: {e}"}), 500


@summary_bp.route('/rangkuman/<task_id>')
def show_summary_result(task_id):
    """
    Displays the final analysis result for a given task_id.
    """
    redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                               decode_responses=True)

    # Fetch the result saved by the n8n webhook
    result_data = redis_client.get(f'summary_result:{task_id}')

    # Find the original task metadata for the timestamp
    task_info = {}
    task_history_json = redis_client.lrange('gcs_summary_tasks', 0, -1)
    for item in task_history_json:
        task_item = json.loads(item)
        if task_item['task_id'] == task_id:
            task_info = task_item
            break

    return render_template('hasil_rangkuman.html', result=result_data, task_info=task_info)