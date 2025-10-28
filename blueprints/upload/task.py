# blueprints/upload/task.py
import os
import boto3
from flask import current_app
import redis
from celery_app import celery
from ..tasks.utils import store_task_info
from datetime import datetime
from dateutil import tz
import uuid

@celery.task(bind=True)
def upload_file_to_r2(self, server_filename, selected_date):
    """
    Upload file to Cloudflare R2
    """
    jakarta_tz = tz.gettz('Asia/Jakarta')
    
    task_id = self.request.id
    task_name = f"R2 Upload - {server_filename}"
    created_at_iso = datetime.now(jakarta_tz).isoformat()
    
    # get redis connection
    redis_conn = None
    try:
        if hasattr(current_app, 'redis_conn') and current_app.redis_conn:
             redis_conn = current_app.redis_conn
        else:
             redis_conn = redis.StrictRedis(
                 host=current_app.config['REDIS_HOST'],
                 port=current_app.config['REDIS_PORT'],
                 db=current_app.config['REDIS_DB'],
                 decode_responses=True
            )
        redis_conn.ping()
    except Exception as e:
        print(f"ERROR: Could not get Redis connection in Celery task: {e}")
        # Update Celery state even without Redis task tracking
        self.update_state(state='FAILURE', meta={'status': f'Redis connection failed: {e}'})
        raise # Re-raise to mark task as failed

    # --- Initial Task Status Update ---
    self.update_state(state='PENDING', meta={'status': 'Initializing R2 upload...'})
    # This call creates the initial record
    store_task_info(
        task_id=task_id,
        task_name=task_name,
        filename=server_filename,
        created_at=created_at_iso,
        status='STARTED',
        last_message='Connecting to R2...',
    )

    try:
        # --- R2 Configuration ---
        # (Keep the R2 config loading as before)
        r2_access_key = current_app.config.get('R2_ACCESS_KEY_ID')
        r2_secret_key = current_app.config.get('R2_SECRET_ACCESS_KEY')
        r2_account_id = current_app.config.get('R2_ACCOUNT_ID')
        r2_endpoint_url = current_app.config.get('R2_ENDPOINT_URL')
        r2_region = current_app.config.get('R2_REGION', 'auto')
        r2_bucket = current_app.config.get('R2_BUCKET_NAME', 'skripsi')

        if not r2_endpoint_url:
            if not r2_account_id:
                raise ValueError("R2 endpoint not configured. Set R2_ENDPOINT_URL or R2_ACCOUNT_ID.")
            r2_endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"

        if not (r2_access_key and r2_secret_key):
            raise ValueError("R2 credentials not configured. Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY.")


        # --- File Path and New Filename ---
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], server_filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Server file {server_filename} not found at {filepath}.")

        new_filename = f"daily_sales_{selected_date}.csv"
        object_key = f"daily_sales/{new_filename}"

        # --- Boto3 S3 Client ---
        s3 = boto3.client(
            's3',
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
            endpoint_url=r2_endpoint_url,
            region_name=r2_region,
        )

        # --- Update Status Before Upload using store_task_info ---
        upload_message = f'Uploading to R2 bucket: {r2_bucket}/{object_key}...'
        self.update_state(state='STARTED', meta={'status': upload_message})
        # --- CORRECTED CALL ---
        store_task_info(
            task_id=task_id,
            task_name=task_name,          # Provide existing name
            filename=server_filename,    # Provide existing filename
            created_at=created_at_iso,   # Provide existing timestamp
            status='STARTED',            # Update status
            last_message=upload_message  # Update message
        )

        # --- Perform Upload ---
        print(f"Attempting to upload R2 object: Bucket='{r2_bucket}', Key='{object_key}', File='{filepath}'")
        with open(filepath, 'rb') as f:
            s3.upload_fileobj(f, r2_bucket, object_key, ExtraArgs={'ContentType': 'application/vnd.ms-excel'})
        print(f"Successfully uploaded {object_key} to R2.")
     
        # --- Final Status Update using store_task_info ---
        final_message = f'File {new_filename} uploaded successfully to R2 bucket {r2_bucket}.'
        self.update_state(state='SUCCESS', meta={'status': final_message, 'result': object_key})
        # --- CORRECTED CALL ---
        store_task_info(
            task_id=task_id,
            task_name=task_name,          # Provide existing name
            filename=server_filename,    # Provide existing filename
            created_at=created_at_iso,   # Provide existing timestamp
            status='SUCCESS',            # Update status
            last_message=final_message   # Update message
        )

        return {'status': 'SUCCESS', 'message': final_message, 'object_key': object_key, 'task_id': task_id}

    except Exception as e:
        error_message = f"R2 Upload Error: {e}"
        print(error_message)
        self.update_state(state='FAILURE', meta={'status': error_message, 'exc_type': type(e).__name__, 'exc_message': str(e)})
        # --- CORRECTED CALL ---
        # Update status to FAILURE using store_task_info
        store_task_info(
            task_id=task_id,
            task_name=task_name,          # Provide existing name
            filename=server_filename,    # Provide existing filename
            created_at=created_at_iso,   # Provide existing timestamp
            status='FAILURE',            # Update status
            last_message=error_message   # Update message
        )
        # Re-raise the exception so Celery knows it failed
        raise e