# blueprints/workflow/routes.py
from flask import Blueprint, render_template, request, jsonify, current_app, abort
from app import socketio
from ..tasks.utils import store_task_info
import datetime
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
            workflow_state[step_id] = json.loads(step_data_json)
            
    return render_template(
        'workflow_timeline.html',
        task_id=task_id,
        workflow_title=workflow_definition['title'],
        steps=workflow_definition['steps'],  # <-- THIS LINE WAS MISSING
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

    # Extract data sent from the n8n workflow
    task_id = data.get('task_id')
    step_id = data.get('step_id')
    status = data.get('status')
    message = data.get('message')
    workflow_type = data.get('workflow_type')

    if not all([task_id, step_id, status, workflow_type]):
        return jsonify({"error": "Missing required fields: task_id, step_id, status, workflow_type"}), 400
    
    redis_conn = current_app.redis_conn
    if redis_conn:
        step_state = {'status': status, 'message': message}
        redis_conn.hset(f'workflow_state:{task_id}', step_id, json.dumps(step_state))
        redis_conn.expire(f'workflow_state:{task_id}', 604800)

    # Broadcast the update to the specific 'room' for this task_id.
    print(f"Broadcasting update for workflow {workflow_type} task {task_id}: step {step_id} is {status}")
    socketio.emit('status_update', {
        'step_id': step_id,
        'status': status,
        'message': message,
        'workflow_type': workflow_type,
    }, room=task_id)

    workflow_definition = current_app.config['WORKFLOWS'].get(workflow_type)
    if workflow_definition:
        final_step_id = workflow_definition['steps'][-1]['id']
        if status == 'fail' or (step_id == final_step_id and status == "success"):
            final_status = "FAILURE" if status == 'fail' else "SUCCESS"
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