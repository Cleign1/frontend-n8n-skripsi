# blueprints/workflow/routes.py
from flask import Blueprint, render_template, request, jsonify
from app import socketio
from ..tasks.utils import store_task_info
import datetime

# Define the blueprint for workflow-related routes
workflow_bp = Blueprint('workflow', __name__, template_folder='../../templates')

@workflow_bp.route('/workflow/<task_id>')
def timeline(task_id):
    """Renders the real-time workflow timeline page for a specific task."""
    return render_template('workflow_timeline.html', task_id=task_id)

@workflow_bp.route('/api/workflow/update', methods=['POST'])
def workflow_webhook():
    """
    This is the webhook endpoint that n8n will call to post status updates.
    It receives a status update and broadcasts it to the correct client via WebSockets.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract data sent from the n8n workflow
    task_id = data.get('task_id')
    step_id = data.get('step_id')
    status = data.get('status')
    message = data.get('message')

    if not all([task_id, step_id, status]):
        return jsonify({"error": "Missing required fields: task_id, step_id, status"}), 400

    # Broadcast the update to the specific 'room' for this task_id.
    # The frontend will be listening in this room.
    print(f"Broadcasting update for task {task_id}: step {step_id} is {status}")
    socketio.emit('status_update', {
        'step_id': step_id,
        'status': status,
        'message': message
    }, room=task_id)

    # If the workflow fails or the final step succeeds, update the overall task status in Redis
    # The final step_id is 'db9ca7f7-135d-4392-bf0a-36f1f688eb39'
    is_final_step_success = (step_id == "db9ca7f7-135d-4392-bf0a-36f1f688eb39" and status == "success")
    if status == 'fail' or is_final_step_success:
        final_status = "FAILURE" if status == 'fail' else "SUCCESS"
        from flask import current_app
        redis_conn = current_app.redis_conn
        if redis_conn:
             redis_conn.hset(f"task:{task_id}", "status", final_status)
             redis_conn.hset(f"task:{task_id}", "last_message", message)

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
