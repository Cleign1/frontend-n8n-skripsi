# blueprints/summary/routes.py
import datetime
import json
import redis
import gdown
import os
import csv
import io
from flask import Blueprint, render_template, jsonify, current_app, abort

# Import the new task
from .task import trigger_n8n_summary_workflow
from ..tasks.utils import store_task_info

summary_bp = Blueprint('summary', __name__, template_folder='../../templates')


@summary_bp.route('/rangkuman')
def rangkuman():
    """
    Renders the summary agent page, displaying a list of historical tasks
    with data received from the n8n workflow.
    """
    tasks = []
    try:
        redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                                   decode_responses=True)
        # Get the list of task IDs from the history
        task_ids = redis_client.lrange('summary_task_history', 0, -1)
        for task_id in task_ids:
            # For each ID, get the full result data stored by the n8n callback
            task_data_json = redis_client.get(f'summary_result:{task_id}')
            if task_data_json:
                task_data = json.loads(task_data_json)
                task_data['task_id'] = task_id # Add task_id for the template
                tasks.append(task_data)

    except redis.exceptions.ConnectionError:
        # If Redis is down, show an empty list instead of crashing
        pass
    return render_template('rangkuman.html', tasks=tasks)


@summary_bp.route('/summary/start', methods=['POST'])
def start_summary():
    """
    Triggers the background task to start the n8n workflow.
    """
    try:
        # Use the new task
        task = trigger_n8n_summary_workflow.delay()

        # Log initial task info for the main /tasks page
        task_name = f"Inventory Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        store_task_info(task.id, task_name, "n8n Workflow", datetime.datetime.now().isoformat(), status='PENDING')

        return jsonify({
            "message": "Summary agent task has been started.",
            "task_id": task.id
        }), 202
    except Exception as e:
        return jsonify({"error": f"Failed to start summary agent task: {e}"}), 500


@summary_bp.route('/rangkuman/<task_id>')
def show_summary_result(task_id):
    """
    Displays the final analysis result, including a table view of the file
    downloaded from Google Drive.
    """
    try:
        redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                                   decode_responses=True)

        result_data_json = redis_client.get(f'summary_result:{task_id}')
        if not result_data_json:
            abort(404, description="Result for this task not found. It might still be processing.")

        result_data = json.loads(result_data_json)
        file_id = result_data.get('file_id')

        csv_headers = []
        csv_rows = []
        file_content_error = None

        if file_id:
            download_dir = os.path.join(current_app.instance_path, 'gdrive_reports')
            os.makedirs(download_dir, exist_ok=True)
            output_path = os.path.join(download_dir, f"{task_id}_report.csv") # Changed extension to .csv

            try:
                gdown.download(id=file_id, output=output_path, quiet=False)
                with open(output_path, 'r', encoding='utf-8') as f:
                    # Use the csv module to parse the file content
                    csv_reader = csv.reader(f)
                    parsed_data = list(csv_reader)
                    if parsed_data:
                        csv_headers = parsed_data[0] # First row as headers
                        csv_rows = parsed_data[1:]   # The rest as data rows
            except Exception as e:
                file_content_error = f"--- ERROR DOWNLOADING OR PARSING FILE ---\n{e}"
        else:
            file_content_error = "No file ID was provided in the result."


        return render_template('hasil_rangkuman.html',
                               result=result_data,
                               task_id=task_id,
                               csv_headers=csv_headers,
                               csv_rows=csv_rows,
                               file_content_error=file_content_error)

    except redis.exceptions.ConnectionError:
        abort(503, "Could not connect to the database to retrieve results.")
    except Exception as e:
        abort(500, f"An unexpected error occurred: {e}")