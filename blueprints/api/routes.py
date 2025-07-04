# blueprints/api/routes.py
import os
import json
import datetime
import requests
import redis
from flask import Blueprint, jsonify, request, current_app
from .utils import update_app_status_via_api, current_app_status
from ..tasks.utils import get_all_tasks, remove_task_from_list, store_task_info
from ..main.tasks import process_csv_in_batches  # Import the task
from celery_app import celery
import os
from celery.contrib.abortable import AbortableAsyncResult

api_bp = Blueprint('api', __name__)

@api_bp.route('/forward_prediction', methods=['POST'])
def forward_prediction():
    """
    Acts as a server-side proxy to the n8n webhook to avoid CORS issues.
    It receives the prediction request from the frontend and forwards it to the n8n service.
    """
    data_to_forward = request.get_json()
    task_id = data_to_forward.get('task_id')
    redis_conn = current_app.redis_conn

    # Get the target webhook URL from environment variables
    n8n_webhook_url = current_app.config.get("N8N_WEBHOOK_URL")

    if not n8n_webhook_url:
        error_msg = 'N8N_WEBHOOK_URL is not configured in the backend.'
        print(f"ERROR: {error_msg}")
        # Update task status to FAILURE
        if task_id and redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "FAILURE")
            redis_conn.hset(f"task:{task_id}", "last_message", error_msg)
        return jsonify({"error": error_msg}), 500

    try:
        # Update global app status to show we're sending the request
        update_app_status_via_api(f"📤 Mengirim permintaan prediksi untuk task: {task_id}")

        # Make the server-to-server request
        response = requests.post(
            n8n_webhook_url,
            json=data_to_forward,
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30-second timeout
        )
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        print(f"Successfully forwarded prediction request for task {task_id} to n8n.")
        return jsonify({"message": "Request successfully forwarded to n8n"}), 200

    except requests.exceptions.RequestException as e:
        error_msg = f"Gagal mengirim request ke n8n: {e}"
        print(f"ERROR: {error_msg}")
        # Update task status to FAILURE
        if task_id and redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "FAILURE")
            redis_conn.hset(f"task:{task_id}", "last_message", error_msg)
        # 502 Bad Gateway is a fitting error code for a proxy failure
        return jsonify({"error": str(e)}), 502

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

@api_bp.route('/tasks/create', methods=['POST'])
def create_task_api():
    data = request.get_json()
    task_id = data.get('task_id')
    task_name = data.get('task_name')
    filename = data.get('filename')
    created_at = data.get('created_at')
    status = data.get('status')
    last_message = data.get('last_message')

    if not task_id or not task_name:
        return jsonify({"error": "task_id and task_name are required"}), 400

    store_task_info(task_id, task_name, filename, created_at, status, last_message)

    # --- CHANGE: If it's a prediction task, update the global app status ---
    if task_id and task_id.startswith('prediksi_'):
        update_app_status_via_api(f"📤 Mengirim prediksi untuk task: {task_id}")

    return jsonify({"status": "success"}), 201

@api_bp.route('/tasks/<task_id>/update', methods=['POST'])
def update_task_api(task_id):
    data = request.get_json()
    status = data.get('status')
    last_message = data.get('last_message')

    redis_conn = current_app.redis_conn
    if redis_conn:
        if status:
            redis_conn.hset(f"task:{task_id}", "status", status)
        if last_message:
            redis_conn.hset(f"task:{task_id}", "last_message", last_message)
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "redis connection failed"}), 500


@api_bp.route('/save-summary-result', methods=['POST'])
def save_summary_result():
    """
    Webhook endpoint for n8n to post the final analysis result.
    It expects a `flask_task_id` in the query string to link the result
    to the correct Celery task.
    """
    # Get the task_id that we originally sent to the n8n webhook
    task_id = request.args.get('flask_task_id')
    if not task_id:
        return jsonify({"error": "Query parameter 'flask_task_id' is required"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    try:
        redis_client = redis.Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], db=0,
                                   decode_responses=True)

        # Store the entire JSON result from n8n
        redis_client.set(f'summary_result:{task_id}', json.dumps(data), ex=604800) # Expires in 7 days

        # Add the task_id to a persistent list for the history view
        redis_client.lpush('summary_task_history', task_id)

        # Update the status of the original Celery task
        redis_client.hset(f"task:{task_id}", "status", "Prediksi Selesai")
        redis_client.hset(f"task:{task_id}", "last_message", "Analysis complete. Report received from n8n.")

        return jsonify({"status": "success", "message": f"Result for task {task_id} saved."}), 200
    except redis.exceptions.ConnectionError as e:
        return jsonify({"error": "Could not connect to Redis", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
