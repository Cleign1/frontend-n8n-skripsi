import csv
import io
import requests
from flask import current_app
from celery_app import celery
from google.cloud import storage
from google.api_core import exceptions


@celery.task(bind=True)
def run_gcs_summary_task(self):
    """
    Celery task to download the latest CSV from GCS, batch it, and send to n8n.
    """
    self.update_state(state='PROGRESS', meta={'status': 'Task started...', 'progress': 0})

    # --- Get Configuration ---
    try:
        bucket_name = current_app.config['GCS_BUCKET_NAME']
        webhook_url = current_app.config['N8N_SUMMARY_WEBHOOK_URL']
        if not bucket_name or not webhook_url:
            raise ValueError("GCS_BUCKET_NAME or N8N_SUMMARY_WEBHOOK_URL is not configured.")
    except Exception as e:
        self.update_state(state='FAILURE', meta={'status': f'Configuration error: {e}', 'progress': 0})
        return {'status': 'FAILURE', 'message': f'Configuration error: {e}'}

    # --- 1. Download Latest File from GCS ---
    try:
        self.update_state(state='PROGRESS', meta={'status': f'Connecting to GCS bucket: {bucket_name}', 'progress': 10})
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = sorted(list(bucket.list_blobs()), key=lambda x: x.time_created, reverse=True)
        if not blobs:
            raise FileNotFoundError("No files found in the bucket.")

        latest_blob = blobs[0]
        self.update_state(state='PROGRESS',
                          meta={'status': f'Downloading latest file: {latest_blob.name}', 'progress': 25})
        csv_data_string = latest_blob.download_as_text()

    except exceptions.NotFound:
        self.update_state(state='FAILURE', meta={'status': f'Error: Bucket "{bucket_name}" not found.', 'progress': 10})
        return {'status': 'FAILURE', 'message': f'Bucket "{bucket_name}" not found.'}
    except FileNotFoundError as e:
        self.update_state(state='FAILURE', meta={'status': str(e), 'progress': 10})
        return {'status': 'FAILURE', 'message': str(e)}
    except Exception as e:
        self.update_state(state='FAILURE', meta={'status': f'GCS download failed: {e}', 'progress': 10})
        return {'status': 'FAILURE', 'message': f'GCS download failed: {e}'}

    # --- 2. Process CSV and Send in Batches ---
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Parsing CSV data...', 'progress': 50})
        csv_file = io.StringIO(csv_data_string)
        reader = csv.DictReader(csv_file)
        all_rows = list(reader)
        total_rows = len(all_rows)
        batch_size = 500
        total_batches = (total_rows + batch_size - 1) // batch_size

        self.update_state(state='PROGRESS',
                          meta={'status': f'Found {total_rows} rows. Preparing to send {total_batches} batches.',
                                'progress': 60})

        for i in range(total_batches):
            start_index = i * batch_size
            end_index = start_index + batch_size
            batch = all_rows[start_index:end_index]
            progress = 60 + int((i / total_batches) * 40)
            self.update_state(state='PROGRESS', meta={'status': f'Sending batch {i + 1} of {total_batches} to n8n...',
                                                      'progress': progress})
            response = requests.post(webhook_url, json=batch, timeout=60)
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        self.update_state(state='FAILURE', meta={'status': f'Failed to send data to n8n: {e}', 'progress': progress})
        return {'status': 'FAILURE', 'message': f'Failed to send data to n8n: {e}'}
    except Exception as e:
        self.update_state(state='FAILURE', meta={'status': f'Data processing failed: {e}', 'progress': 50})
        return {'status': 'FAILURE', 'message': f'Data processing failed: {e}'}

    # --- 3. Finalize ---
    final_message = f'Successfully processed {total_rows} rows and sent {total_batches} batches to n8n.'
    self.update_state(state='SUCCESS', meta={'status': final_message, 'progress': 100})
    return {'status': 'SUCCESS', 'message': final_message}