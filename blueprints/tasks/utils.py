# blueprints/tasks/utils.py
from flask import current_app
from celery_app import celery
import json


def get_all_tasks():
    """Get all active tasks"""
    redis_conn = current_app.redis_conn
    if not redis_conn:
        print("Warning: Redis connection not available in get_all_tasks.")
        return []

    tasks = []
    task_ids_from_list = []
    try:
        # Get the list of active task IDs from Redis
        task_ids_from_list = redis_conn.lrange("active_tasks", 0, -1)
        if not task_ids_from_list:
            print("No active tasks found in Redis list 'active_tasks'.")
            return [] # Return empty list if no IDs are found
    except Exception as e:
        print(f"Error reading 'active_tasks' list from Redis: {e}")
        return [] # Return empty on error

    print(f"Found active task IDs in Redis list: {task_ids_from_list}") # Debugging line

    unique_task_ids = set(task_ids_from_list)
    print(f'Memproses {len(unique_task_ids)} unique task IDs from Redis list.') # Debugging line

    for task_id in unique_task_ids:
        task_info = {}
        try:
            # Fetch the details for each task ID
            task_info = redis_conn.hgetall(f"task:{task_id}")
        except Exception as e:
            print(f"Error fetching details for task '{task_id}' from Redis: {e}")
            continue # Skip this task if details can't be fetched

        if not task_info:
            # This can happen if the task info expired or was manually deleted
            print(f"Warning: No task details found in Redis hash for task ID '{task_id}' (from active_tasks list). Skipping.")
            continue

        print(f"Processing task details for ID '{task_id}': {task_info}") # Debugging line

        # --- START FIX: Process ALL tasks, but apply special logic for workflows ---

        # Keep the logic to update status based on workflow finish state
        if task_id.startswith('workflow_'):
            finish_state_json = None
            try:
                finish_state_json = redis_conn.hget(f"workflow_state:{task_id}", "workflow_finish")
            except Exception as e:
                 print(f"Error fetching workflow_finish state for task '{task_id}': {e}")

            if finish_state_json:
                try:
                    finish_state = json.loads(finish_state_json)
                    # Use the status from workflow_finish if it's success or fail
                    if finish_state.get('status') in ['success', 'fail']:
                        # Map 'success'/'fail' from workflow state to 'SUCCESS'/'FAILURE'
                        task_info['status'] = "SUCCESS" if finish_state['status'] == 'success' else "FAILURE"
                        task_info['last_message'] = finish_state.get('message', task_info.get('last_message', '')) # Use existing message as fallback
                        print(f"Updated task '{task_id}' status from workflow_finish state.") # Debugging line
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode workflow_finish JSON for task {task_id}")
                except Exception as e:
                    print(f"Error processing workflow_finish state for task '{task_id}': {e}")


        # Append ALL valid task_info objects retrieved from Redis hashes
        tasks.append(task_info)
        # --- END FIX ---

    print(f"Returning {len(tasks)} tasks to be displayed.") # Debugging line
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