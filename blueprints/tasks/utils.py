# blueprints/tasks/utils.py
from flask import current_app
from celery_app import celery
import json


def get_all_tasks():
    """Get all active tasks"""
    redis_conn = current_app.redis_conn
    if not redis_conn:
        return []

    tasks = []
    task_ids = redis_conn.lrange("active_tasks", 0, -1)

    for task_id in task_ids:
        task_info = redis_conn.hgetall(f"task:{task_id}")
        if not task_info:
            continue

        if task_id.startswith('prediksi_') or task_id.startswith('workflow_'):
            # Check if there's a definitive final state saved for workflows
            if task_id.startswith('workflow_'):
                finish_state_json = redis_conn.hget(f"workflow_state:{task_id}", "workflow_finish")
                if finish_state_json:
                    try:
                        finish_state = json.loads(finish_state_json)
                        # Use the status from workflow_finish if it's success or fail
                        if finish_state.get('status') in ['success', 'fail']:
                             # Map 'success'/'fail' from workflow state to 'SUCCESS'/'FAILURE' for consistency
                            task_info['status'] = "SUCCESS" if finish_state['status'] == 'success' else "FAILURE"
                            task_info['last_message'] = finish_state.get('message', task_info.get('last_message'))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode workflow_finish JSON for task {task_id}")
                        # Keep the status already present in task_info if decoding fails

            # Append the potentially updated task_info
            tasks.append(task_info)
            continue

    return tasks


def store_task_info(task_id, task_name, filename, created_at, status='PENDING', last_message='', workflow_type=None):
    """Store task information in Redis, now including workflow_type."""
    redis_conn = current_app.redis_conn
    if redis_conn:
        task_info = {
            'task_id': task_id,
            'task_name': task_name,
            'filename': filename,
            'created_at': created_at,
            'status': status,
            'last_message': last_message
        }
        # Add workflow_type to the stored data if provided
        if workflow_type:
            task_info['workflow_type'] = workflow_type
            
        redis_conn.hset(f"task:{task_id}", mapping=task_info)
        redis_conn.lpush("active_tasks", task_id)
        redis_conn.expire(f"task:{task_id}", 86400)  # 24 hours


def remove_task_from_list(task_id):
    """Remove task from active list"""
    redis_conn = current_app.redis_conn
    if redis_conn:
        redis_conn.lrem("active_tasks", 0, task_id)