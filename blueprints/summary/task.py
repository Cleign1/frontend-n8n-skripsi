# blueprints/summary/task.py
import requests
from flask import current_app
from celery_app import celery


@celery.task(bind=True)
def trigger_n8n_summary_workflow(self):
    """
    Celery task that triggers the n8n summary workflow via a webhook
    and waits for a callback.
    """
    task_id = self.request.id
    self.update_state(state='PENDING', meta={'status': 'Triggering n8n workflow...'})

    try:
        # Get the webhook URL from the application configuration
        webhook_url = current_app.config.get("N8N_SUMMARY_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("N8N_SUMMARY_WEBHOOK_URL is not configured.")

        # Add the Flask task_id to the webhook URL as a query parameter
        # This allows n8n to send the result back to the correct task.
        url_with_task_id = f"{webhook_url}?flask_task_id={task_id}"

        response = requests.get(url_with_task_id, timeout=15)
        response.raise_for_status()  # Raise an exception for bad status codes

        # The task state will be updated by the n8n callback via the API
        self.update_state(state='STARTED', meta={'status': 'Workflow triggered. Waiting for n8n to complete and call back.'})
        return {'status': 'SUCCESS', 'message': f'Successfully triggered n8n workflow. Task ID: {task_id}'}

    except requests.exceptions.RequestException as e:
        self.update_state(state='FAILURE', meta={'status': f'Failed to trigger n8n: {e}'})
        return {'status': 'FAILURE', 'message': f'Failed to trigger n8n: {e}'}
    except ValueError as e:
        self.update_state(state='FAILURE', meta={'status': f'Configuration error: {e}'})
        return {'status': 'FAILURE', 'message': f'Configuration error: {e}'}