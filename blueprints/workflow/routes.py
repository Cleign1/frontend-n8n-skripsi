# blueprints/workflow/routes.py
from flask import Blueprint, render_template, request, jsonify, current_app, abort
from app import socketio
from ..tasks.utils import store_task_info
from ..api.utils import update_app_status_via_api
from datetime import datetime
from dateutil import tz
import json

workflow_bp = Blueprint('workflow', __name__, template_folder='../../templates')

@workflow_bp.route('/workflow/<workflow_type>/<task_id>')
def timeline(workflow_type, task_id):
    """Renders the real-time workflow timeline page for a specific task and workflow."""
    workflow_definition = current_app.config['WORKFLOWS'].get(workflow_type)
    if not workflow_definition:
        abort(404, description=f'Tipe Workflow {workflow_type} tidak ditemukan.')

    redis_conn = current_app.redis_conn
    workflow_state = {}
    if redis_conn:
        state_data = redis_conn.hgetall(f'workflow_state:{task_id}')
        for step_id, step_data_json in state_data.items():
            # --- FIX: Add error handling for invalid JSON ---
            try:
                workflow_state[step_id] = json.loads(step_data_json)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON for step {step_id} in task {task_id}")
                # Optionally set a default error state or skip
                workflow_state[step_id] = {'status': 'fail', 'message': 'Error loading state'}
            # --- END FIX ---

    return render_template(
        'workflow_timeline.html',
        task_id=task_id,
        workflow_title=workflow_definition['title'],
        steps=workflow_definition['steps'],
        workflow_state=workflow_state
    )

@workflow_bp.route('/workflow/debug')
def workflow_debug():
    """Renders the workflow API debug page."""
    return render_template('workflow_debug.html')

@workflow_bp.route('/api/workflow/update', methods=['POST'])
def workflow_webhook():
    """
    This is the webhook endpoint that n8n will call to post status updates.
    It receives a status update and broadcasts it to the correct client via WebSockets.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    task_id = data.get('flask_task_id') or data.get('task_id') # Prioritize flask_task_id
    step_id = data.get('step_id')
    status = data.get('status')
    message = data.get('message')
    workflow_type = data.get('workflow_type')

    # --- Add Logging ---
    print("\n--- Webhook Received ---")
    print(f"Timestamp: {datetime.now(tz.gettz('Asia/Jakarta')).isoformat()}")
    print(f"Task ID (from payload): {task_id}")
    print(f"Step ID: {step_id}")
    print(f"Status: {status}")
    print(f"Workflow Type: {workflow_type}")
    print(f"Message: {message}")
    # --- End Logging ---

    if not all([task_id, step_id, status, workflow_type]):
        print("Webhook Error: Missing required fields") # Add Logging
        return jsonify({"error": "Missing required fields: task_id (or flask_task_id), step_id, status, workflow_type"}), 400

    redis_conn = current_app.redis_conn
    if redis_conn:
        step_state = {'status': status, 'message': message}
        try:
            redis_conn.hset(f'workflow_state:{task_id}', step_id, json.dumps(step_state))
            redis_conn.expire(f'workflow_state:{task_id}', 604800) # Expire in 7 days
            print(f"Saved state for step '{step_id}' to Redis key 'workflow_state:{task_id}'.") # Add Logging
        except Exception as e:
            print(f"ERROR saving step state to Redis: {e}") # Add Logging for Redis errors

    # Broadcast update via SocketIO
    print(f"Broadcasting SocketIO 'status_update' for step '{step_id}' to room '{task_id}'.") # Add Logging
    socketio.emit('status_update', {
        'step_id': step_id,
        'status': status,
        'message': message,
        'workflow_type': workflow_type,
    }, room=task_id)

    # Check if this is the final step
    workflow_definition = current_app.config['WORKFLOWS'].get(workflow_type)
    final_step_id = None # Initialize
    if workflow_definition and 'steps' in workflow_definition and workflow_definition['steps']:
        final_step_id = workflow_definition['steps'][-1]['id']
        print(f"Checking against final step ID from config: '{final_step_id}'") # Add Logging
    else:
        print(f"Warning: No steps found in config for workflow_type '{workflow_type}'") # Add Logging

    final_workflow_status = None
    final_workflow_message = ""
    global_status_message = ""

    if status == 'fail':
        print(f"Workflow '{workflow_type}' failed at step '{step_id}'.") # Add Logging
        final_workflow_status = 'fail'
        final_workflow_message = f"Workflow gagal pada langkah: {step_id}. Pesan: {message}"
        global_status_message = f"❌ Workflow '{workflow_type}' Gagal ({task_id})"

    # --- Ensure final_step_id is not None before comparing ---
    elif final_step_id is not None and step_id == final_step_id and status == "success":
        print(f"SUCCESS: Final step condition met for step '{step_id}'.") # Add Logging
        final_workflow_status = 'success'
        final_workflow_message = "Semua langkah berhasil diselesaikan."
        global_status_message = f"✅ Workflow '{workflow_type}' Selesai ({task_id})"
    # --- End Check ---
    elif status == "success":
         print(f"Step '{step_id}' succeeded, but it's not the final step ('{final_step_id}').") # Add Logging
    else:
         print(f"Step '{step_id}' has status '{status}', not checking final step condition.") # Add Logging


    if final_workflow_status:
        print(f"Attempting to save final workflow status '{final_workflow_status}' to Redis.") # Add Logging
        if redis_conn:
            finish_step_state = {'status': final_workflow_status, 'message': final_workflow_message}
            try:
                # Save 'workflow_finish' state
                redis_conn.hset(f'workflow_state:{task_id}', 'workflow_finish', json.dumps(finish_step_state))
                print(f"Saved 'workflow_finish' state to Redis key 'workflow_state:{task_id}'.") # Add Logging

                # Update main task status (for /tasks page)
                task_page_status = "SUCCESS" if final_workflow_status == 'success' else "FAILURE"
                redis_conn.hset(f"task:{task_id}", "status", task_page_status)
                redis_conn.hset(f"task:{task_id}", "last_message", final_workflow_message)
                print(f"Updated main task status in Redis key 'task:{task_id}' to '{task_page_status}'.") # Add Logging

            except Exception as e:
                print(f"ERROR saving final workflow state to Redis: {e}") # Add Logging for Redis errors

        if global_status_message:
            update_app_status_via_api(global_status_message)

    return jsonify({"status": "received"}), 200

# --- WebSocket Event Handlers ---
@socketio.on('join')
def on_join(data):
    """Allows a client to join a room for a specific task."""
    from flask_socketio import join_room
    task_id = data['room']
    join_room(task_id)
    print(f"Client joined room: {task_id}")

@socketio.on('leave')
def on_leave(data):
    """Allows a client to leave a room."""
    from flask_socketio import leave_room
    task_id = data['room']
    leave_room(task_id)
    print(f"Client left room: {task_id}")