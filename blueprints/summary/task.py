# blueprints/summary/task.py
import requests
from flask import current_app
from celery_app import celery
import os


@celery.task(bind=True)
def trigger_n8n_summary_workflow(self, workflow_task_id, date_str):
    """
    Celery task that triggers the n8n summary workflow via a webhook
    using the provided workflow_task_id (workflow_<uuid>) and date.
    n8n should call back to /api/save-summary-result?flask_task_id=<workflow_task_id>
    with the final JSON payload (ideally including 'date').
    """
    # Keep Celery's own state tracking for visibility
    self.update_state(state='PENDING', meta={'status': 'Triggering n8n workflow...'})

    try:
        webhook_url = current_app.config.get("N8N_SUMMARY_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("N8N_SUMMARY_WEBHOOK_URL is not configured.")

        # Pass workflow_task_id to n8n via query parameter for callback mapping
        url_with_task_id = f"{webhook_url}?flask_task_id={workflow_task_id}"

        # Also include the workflow_task_id + date in the JSON body
        payload = {
            "workflow_task_id": workflow_task_id,
            "date": date_str,
            'flask_webhook_url': f'{os.getenv("INTERNAL_API_BASE_URL", "http://localhost:5000")}/api/workflow/update'
        }

        response = requests.post(url_with_task_id, json=payload, timeout=15)
        response.raise_for_status()

        # The final status will be updated by the n8n callback via /api/save-summary-result
        self.update_state(state='STARTED', meta={
            'status': 'Workflow triggered. Waiting for n8n to complete and call back.',
            'workflow_task_id': workflow_task_id
        })
        return {
            'status': 'SUCCESS',
            'message': f'Successfully triggered n8n workflow.',
            'workflow_task_id': workflow_task_id
        }

    except requests.exceptions.RequestException as e:
        self.update_state(state='FAILURE', meta={'status': f'Failed to trigger n8n: {e}'})
        return {'status': 'FAILURE', 'message': f'Failed to trigger n8n: {e}', 'workflow_task_id': workflow_task_id}
    except ValueError as e:
        self.update_state(state='FAILURE', meta={'status': f'Configuration error: {e}'})
        return {'status': 'FAILURE', 'message': f'Configuration error: {e}', 'workflow_task_id': workflow_task_id}