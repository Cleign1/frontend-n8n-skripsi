# blueprints/api/routes.py
import os
import json
import datetime
from itertools import count

from flask import Blueprint, jsonify, request, current_app
from .utils import update_app_status_via_api, current_app_status
from ..tasks.utils import get_all_tasks, remove_task_from_list, store_task_info
from ..main.tasks import process_csv_in_batches  # Import the task
from celery_app import celery
import os
from celery.contrib.abortable import AbortableAsyncResult

api_bp = Blueprint('api', __name__)


# --- BATCH AND STATUS API ---
@api_bp.route('/start_batch_process', methods=['POST'])
def start_batch_process():
    # Update app status when starting
    update_app_status_via_api("🚀 Memulai proses batch...")
    redis_conn = current_app.redis_conn
    if redis_conn:
        status_str = redis_conn.get("batch_job_status")
        if status_str and json.loads(status_str).get('is_running'):
            return jsonify({"error": "Proses batch lain sedang berjalan."}), 409

    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Filename tidak disertakan"}), 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER')

    # Check if file exists
    filepath = os.path.join(upload_folder, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": f"File {filename} tidak ditemukan"}), 404

    external_api_url = os.getenv('EXTERNAL_API_URL')
    if not external_api_url:
        print("External api url not set")

    try:
        task = process_csv_in_batches.delay(filename, external_api_url)

        # Store task information
        task_name = f"Update Stok {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        store_task_info(task.id, task_name, filename, datetime.datetime.now().isoformat())

        print(f"Task started with ID: {task.id}")
        return jsonify({
            "message": "Proses pengiriman batch telah dimulai.",
            "task_id": task.id
        }), 202
    except Exception as e:
        print(f"Error starting task: {e}")
        update_app_status_via_api("❌ Error memulai proses")
        return jsonify({"error": f"Gagal memulai proses: {e}"}), 500

@api_bp.route('/batch_status', methods=['GET'])
def get_batch_status():
    redis_conn = current_app.redis_conn
    if redis_conn:
        status_json = redis_conn.get("batch_job_status")
        if status_json:
            return jsonify(json.loads(status_json))

    return jsonify({
        'is_running': False,
        'message': 'Belum ada proses yang berjalan.',
        'progress': 0
    })

@api_bp.route('/status', methods=['GET', 'POST'])
def status_endpoint():
    global current_app_status
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Data tidak valid"}), 400
        current_app_status['status'] = data.get('status')
        current_app_status['last_updated'] = datetime.datetime.now().isoformat()
        return jsonify({"message": "Status berhasil diperbarui"}), 200
    else:
        return jsonify(current_app_status)

# --- TASK MANAGEMENT API ---
@api_bp.route('/tasks', methods=['GET'])
def get_tasks_api():
    from ..tasks.utils import get_all_tasks
    tasks = get_all_tasks()
    return jsonify(tasks)


@api_bp.route('/tasks/<task_id>/abort', methods=['POST'])
def abort_task(task_id):
    """Sends the abort signal to a running task."""
    try:
        task_result = AbortableAsyncResult(task_id)

        # This sets the official state in the backend
        task_result.abort()

        # --- FIX: Set a simple, explicit flag in Redis for the worker to check ---
        # The worker will look for this key. We set a timeout (e.g., 1 hour)
        # so it gets cleaned up automatically if something goes wrong.
        redis_conn = current_app.redis_conn
        if redis_conn:
            redis_conn.set(f"task-aborted:{task_id}", "1", ex=3600)

            # Also update the main status for immediate feedback in the UI
            redis_conn.hset(f"task:{task_id}", "status", "ABORTED")
            redis_conn.hset(f"task:{task_id}", "last_message", "Abort signal sent by user.")

        print(f"Abort signal and Redis flag set for task {task_id}")
        return jsonify({"message": f"Abort signal sent to task {task_id}"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to send abort signal: {e}"}), 500

@api_bp.route('/tasks/<task_id>/remove', methods=['DELETE'])
def remove_task(task_id):
    try:
        # Remove from active tasks list
        remove_task_from_list(task_id)

        # Delete task info from Redis
        redis_conn = current_app.redis_conn
        if redis_conn:
            redis_conn.delete(f"task:{task_id}")

        return jsonify({"message": f"Task {task_id} telah dihapus dari daftar"}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menghapus task: {e}"}), 500

@api_bp.route('/tasks/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    try:
        celery_task = celery.AsyncResult(task_id)

        task_info = {
            'task_id': task_id,
            'status': celery_task.status,
            'result': str(celery_task.result) if celery_task.result else None
        }

        # Get additional info from Redis
        redis_conn = current_app.redis_conn
        if redis_conn:
            redis_info = redis_conn.hgetall(f"task:{task_id}")
            task_info.update(redis_info)

        return jsonify(task_info)
    except Exception as e:
        return jsonify({"error": f"Gagal mendapatkan status task: {e}"}), 500