# blueprints/tasks/utils.py
from flask import current_app
from celery_app import celery


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

        if task_id.startswith('prediksi_'):
            tasks.append(task_info)
            continue

        try:
            celery_task = celery.AsyncResult(task_id)
            current_celery_status = celery_task.status
            if task_info.get('status') != current_celery_status:
                redis_conn.hset(f"task:{task_id}", "status", current_celery_status)
            task_info['status'] = current_celery_status
            task_info['result'] = str(celery_task.result) if celery_task.result else None
            tasks.append(task_info)
        except Exception as e:
            print(f"Error getting task status for {task_id}: {e}")
            task_info['status'] = 'UNKNOWN'
            tasks.append(task_info)

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