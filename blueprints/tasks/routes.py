# blueprints/tasks/routes.py
from flask import Blueprint, render_template, request, jsonify
from .utils import get_all_tasks
from ..api.utils import update_app_status_via_api

tasks_bp = Blueprint('tasks_ui', __name__)


@tasks_bp.route('/tasks')
def tasks():
    tasks_list = get_all_tasks()
    return render_template('tasks.html', tasks=tasks_list)


@tasks_bp.route('/prediksi-stok', methods=['GET', 'POST'])
def prediksi_stok_task():
    if request.method == 'POST':
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Request must be a valid JSON"}), 400

        task_id = data.get('task_id')
        # --- FIX: Get status and message from the request payload ---
        new_status = data.get('status')
        new_message = data.get('last_message')

        if task_id:
            from flask import current_app
            redis_conn = current_app.redis_conn
            if redis_conn:
                # Use the new status and message if they exist in the request
                if new_status:
                    redis_conn.hset(f"task:{task_id}", "status", new_status)
                if new_message:
                    redis_conn.hset(f"task:{task_id}", "last_message", new_message)

            # Update global status
            update_app_status_via_api(f"✅ Task {task_id} updated by webhook.")

        return jsonify({"status": "success"}), 200

    return render_template('prediksi_stok.html')