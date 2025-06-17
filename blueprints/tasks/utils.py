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
        if task_info:
            # Get current task status from Celery
            try:
                celery_task = celery.AsyncResult(task_id)
                task_info['status'] = celery_task.status
                task_info['result'] = str(celery_task.result) if celery_task.result else None

                # Update status in Redis
                redis_conn.hset(f"task:{task_id}", "status", task_info['status'])

                tasks.append(task_info)
            except Exception as e:
                print(f"Error getting task status for {task_id}: {e}")
                task_info['status'] = 'UNKNOWN'
                tasks.append(task_info)

    return tasks


def store_task_info(task_id, task_name, filename, created_at):
    """Store task information in Redis"""
    redis_conn = current_app.redis_conn
    if redis_conn:
        task_info = {
            'task_id': task_id,
            'task_name': task_name,
            'filename': filename,
            'created_at': created_at,
            'status': 'PENDING'
        }
        redis_conn.hset(f"task:{task_id}", mapping=task_info)
        redis_conn.lpush("active_tasks", task_id)
        redis_conn.expire(f"task:{task_id}", 86400)  # 24 hours

def remove_task_from_list(task_id):
    """Remove task from active list"""
    redis_conn = current_app.redis_conn
    if redis_conn:
        redis_conn.lrem("active_tasks", 0, task_id)