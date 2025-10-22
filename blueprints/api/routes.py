# blueprints/api/routes.py
import uuid
import json
import datetime
import requests
import redis
import os
from flask import Blueprint, jsonify, request, current_app
from .utils import update_app_status_via_api, get_current_app_status
from ..tasks.utils import get_all_tasks, remove_task_from_list, store_task_info
from ..main.tasks import process_csv_in_batches  # Import the task
from celery_app import celery
from celery.contrib.abortable import AbortableAsyncResult

api_bp = Blueprint('api', __name__)

@api_bp.route('/predict_stok', methods=['POST'])
def predict_stok():
    """
    Acts as a server-side proxy to the stock prediction service (WORKFLOW_2) to avoid CORS issues.
    """
    data_to_forward = request.get_json()
    # The payload is a JSON object, get the task_id from it
    task_id = data_to_forward.get('task_id')
    redis_conn = current_app.redis_conn

    # Get the target webhook URL from environment variables
    workflow_2_url = current_app.config.get("WORKFLOW_2")

    if not workflow_2_url:
        error_msg = 'The WORKFLOW_2 environment variable is not set in the backend.'
        print(f"ERROR: {error_msg}")
        if task_id and redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "FAILURE")
            redis_conn.hset(f"task:{task_id}", "last_message", error_msg)
        return jsonify({"error": error_msg}), 500

    try:
        # --- FIX: Add request_time as required by the Go backend ---
        data_to_forward["request_time"] = datetime.datetime.now().isoformat()
        # --- END FIX ---

        update_app_status_via_api(f"📤 Mengirim permintaan prediksi stok untuk task: {task_id}")

        response = requests.post(
            workflow_2_url,
            json=data_to_forward, # This now includes request_time
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()

        print(f"Successfully forwarded stock prediction request for task {task_id}.")
        return jsonify({"message": "Request successfully forwarded"}), 200

    except requests.exceptions.RequestException as e:
        error_msg = f"Gagal mengirim request ke layanan prediksi: {e}"
        print(f"ERROR: {error_msg}")
        if task_id and redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "FAILURE")
            redis_conn.hset(f"task:{task_id}", "last_message", error_msg)
        return jsonify({"error": str(e)}), 502

@api_bp.route('/status', methods=['GET', 'POST'])
def status_endpoint():
    # Remove 'global current_app_status'
    if request.method == 'POST':
        # POST is now primarily handled by update_app_status_via_api
        # But we keep this for direct external updates if needed
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Data tidak valid"}), 400
        # Call the central update function
        update_app_status_via_api(data.get('status')) 
        return jsonify({"message": "Status berhasil diperbarui"}), 200
    else:
        # GET reads the current status from Redis
        current_status = get_current_app_status() 
        return jsonify(current_status)

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

@api_bp.route('/workflow/start', methods=['POST'])
def start_workflow():
    """
    Starts an n8n workflow OR the Go prediction workflow.
    """
    data = request.get_json()
    workflow_type = data.get('workflow_type', 'update')
    date_str = data.get('date')

    if not date_str:
        return jsonify({"error": "Invalid request, 'date' is required"}), 400

    workflows_config = current_app.config.get('WORKFLOWS')
    if not workflows_config:
        return jsonify({"error": "WORKFLOWS definition not found in configuration."}), 500

    n8n_webhook_url = None
    n8n_payload = None

    task_id = f'workflow_{uuid.uuid4()}'

    workflow_title = workflows_config.get(workflow_type, {}).get('title', 'Unknown Workflow')
    task_name = f'{workflow_title} - {datetime.datetime.now().strftime("%Y-%m-%d")}'

    if workflow_type == 'update':
        n8n_webhook_url = current_app.config.get("N8N_WEBHOOK_URL")
        if not n8n_webhook_url:
            return jsonify({"error": "N8N_WEBHOOK_URL environment variable is not set."}), 500

        n8n_payload = [{
            'date': date_str,
            'flask_task_id': task_id,
            'workflow_type': workflow_type,
            'flask_webhook_url': f'{os.getenv("INTERNAL_API_BASE_URL", "http://localhost:5000")}/api/workflow/update'
        }]

    elif workflow_type == 'prediction':
        n8n_webhook_url = current_app.config.get("WORKFLOW_2") # Get the Go backend URL
        if not n8n_webhook_url:
             return jsonify({"error": "WORKFLOW_2 (prediction workflow) environment variable is not set."}), 500

        go_task_id = f"prediksi_{int(datetime.datetime.now().timestamp() * 1000)}"

        n8n_payload = {
            "prediction_date": date_str,
            "request_time": datetime.datetime.now().isoformat(),
            "task_id": go_task_id,
            "flask_task_id": task_id,
            "workflow_type": workflow_type,
            "flask_webhook_url": f'{os.getenv("INTERNAL_API_BASE_URL", "http://localhost:5000")}/api/workflow/update'
        }

    else:
        return jsonify({"error": f"Unknown workflow_type: {workflow_type}"}), 400

    store_task_info(
        task_id,
        task_name,
        f'Prediction for {date_str}' if workflow_type == 'prediction' else f'daily_sales_{date_str}.csv',
        datetime.datetime.now().isoformat(),
        status="Dimulai",
        last_message='Task dibuat, proses akan segera dimulai.',
        workflow_type=workflow_type
    )

    try:
        update_app_status_via_api(f"🚀 Memulai Workflow '{workflow_type}' ({task_id})")

        # --- FIX: Increased timeout from 10 to 30 seconds ---
        response = requests.post(n8n_webhook_url, json=n8n_payload, timeout=30)
        # --- END FIX ---

        response.raise_for_status()

        return jsonify({
            "message": f"Workflow '{workflow_type}' dimulai",
            "task_id": task_id,
            "workflow_type": workflow_type
        }), 202

    except requests.exceptions.RequestException as e:
        # Check if the error is a timeout
        error_message = f"Gagal memicu n8n: {e}"
        if isinstance(e, requests.exceptions.Timeout):
            error_message = f"Gagal memicu n8n: Timeout menunggu respon dari {n8n_webhook_url} setelah 30 detik."
            update_app_status_via_api(f"⏳ Timeout memulai Workflow '{workflow_type}' ({task_id})")
        else:
             update_app_status_via_api(f"❌ Gagal memulai Workflow '{workflow_type}' ({task_id})")

        redis_conn = current_app.redis_conn
        if redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "FAILURE")
            redis_conn.hset(f"task:{task_id}", "last_message", error_message)
        # Return 504 Gateway Timeout specifically for timeout errors
        status_code = 504 if isinstance(e, requests.exceptions.Timeout) else 500
        return jsonify({"error": error_message}), status_code