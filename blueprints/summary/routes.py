# blueprints/summary/routes.py
import datetime
import json
import redis
import os
import csv
import io
import uuid
import boto3
from flask import Blueprint, render_template, jsonify, current_app, abort, request

from .task import trigger_n8n_summary_workflow
from ..tasks.utils import store_task_info

summary_bp = Blueprint('summary', __name__, template_folder='../../templates')


@summary_bp.route('/rangkuman')
def rangkuman():
    """
    Renders the summary agent page, displaying a list of historical tasks
    with data received from the n8n workflow.
    """
    tasks = []
    try:
        redis_client = redis.Redis(
            host=current_app.config['REDIS_HOST'],
            port=current_app.config['REDIS_PORT'],
            db=0,
            decode_responses=True
        )
        task_ids = redis_client.lrange('summary_task_history', 0, -1)
        for task_id in task_ids:
            task_data_json = redis_client.get(f'summary_result:{task_id}')
            if task_data_json:
                task_data = json.loads(task_data_json)
                # Backward-compatible key plus new explicit workflow_task_id
                task_data['task_id'] = task_id
                task_data['workflow_task_id'] = task_id
                tasks.append(task_data)

    except redis.exceptions.ConnectionError:
        pass
    return render_template('rangkuman.html', tasks=tasks)


@summary_bp.route('/summary/start', methods=['POST'])
def start_summary():
    """
    Starts the summary workflow by:
    - Generating workflow_task_id (format: workflow_<uuid>)
    - Enqueuing a Celery task that triggers the n8n summary webhook with workflow_task_id and date
    - Recording the task in the timeline/history
    - Returning the workflow_task_id to the client

    Expected JSON body:
    {
        "date": "YYYY-MM-DD"
    }
    """
    try:
        body = request.get_json(silent=True) or {}
        date_str = body.get('date')
        if not date_str:
            return jsonify({"error": "Invalid request, 'date' is required (YYYY-MM-DD)."}), 400

        # Generate the workflow-scoped ID (not Celery's task id)
        workflow_task_id = f"workflow_{uuid.uuid4()}"

        # Kick off Celery worker to call n8n webhook
        trigger_n8n_summary_workflow.delay(workflow_task_id, date_str)

        # Record the task in the task list/timeline using workflow_task_id
        task_name = f"Inventory Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        store_task_info(
            workflow_task_id,
            task_name,
            "n8n Workflow",
            datetime.datetime.now().isoformat(),
            status='PENDING',
            workflow_type='summary'
        )

        return jsonify({
            "message": "Summary agent workflow started.",
            "workflow_task_id": workflow_task_id
        }), 202

    except Exception as e:
        return jsonify({"error": f"Failed to start summary workflow: {e}"}), 500


@summary_bp.route('/rangkuman/<task_id>')
def show_summary_result(task_id):
    """
    Displays the final analysis result, including a table view of the file
    downloaded from Cloudflare R2 (S3-compatible) using the file_id
    provided by the n8n workflow result. Ensures the file_id has .csv.
    Sorts the displayed CSV data by Product ID.
    """
    try:
        redis_client = redis.Redis(
            host=current_app.config['REDIS_HOST'],
            port=current_app.config['REDIS_PORT'],
            db=0,
            decode_responses=True
        )

        result_data_json = redis_client.get(f'summary_result:{task_id}')
        if not result_data_json:
            abort(404, description="Result for this task not found. It might still be processing.")

        result_data = json.loads(result_data_json)

        object_key = result_data.get('file_id')

        if not object_key:
            return render_template(
                'hasil_rangkuman.html', result=result_data, task_id=task_id, csv_headers=[], csv_rows=[],
                file_content_error=f"Report file path ('file_id') not found in the summary result for task {task_id}."
            )

        if not object_key.lower().endswith('.csv'):
            object_key += '.csv'
            print(f"Appended .csv to object_key. Now using: {object_key}")


        # Cloudflare R2 S3-compatible configuration
        r2_access_key = current_app.config.get('R2_ACCESS_KEY_ID')
        r2_secret_key = current_app.config.get('R2_SECRET_ACCESS_KEY')
        r2_account_id = current_app.config.get('R2_ACCOUNT_ID')
        r2_endpoint_url = current_app.config.get('R2_ENDPOINT_URL')
        r2_region = current_app.config.get('R2_REGION', 'auto')
        r2_bucket = current_app.config.get('R2_BUCKET_NAME', 'skripsi')

        if not r2_endpoint_url:
            if not r2_account_id:
                return render_template(
                    'hasil_rangkuman.html', result=result_data, task_id=task_id, csv_headers=[], csv_rows=[],
                    file_content_error="R2 endpoint not configured. Set R2_ENDPOINT_URL or R2_ACCOUNT_ID."
                )
            r2_endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"

        if not (r2_access_key and r2_secret_key):
            return render_template(
                'hasil_rangkuman.html', result=result_data, task_id=task_id, csv_headers=[], csv_rows=[],
                file_content_error="R2 credentials not configured. Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY."
            )

        s3 = boto3.client(
            's3',
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
            endpoint_url=r2_endpoint_url,
            region_name=r2_region,
        )

        csv_headers = []
        csv_rows = []
        file_content_error = None

        try:
            print(f"Attempting to download R2 object: Bucket='{r2_bucket}', Key='{object_key}'")
            obj = s3.get_object(Bucket=r2_bucket, Key=object_key)
            with io.TextIOWrapper(obj['Body'], encoding='utf-8') as f:
                reader = csv.reader(f)
                temp_rows = [] # Use a temporary list to store rows before sorting
                for i, row in enumerate(reader):
                    if i == 0:
                        csv_headers = row
                    else:
                        temp_rows.append(row) # Add to temporary list

            print(f"Successfully downloaded {len(temp_rows)} data rows from {object_key}")

            # --- START SORTING LOGIC ---
            if temp_rows:
                # Find the index of 'PRODUCT ID' (case-insensitive)
                product_id_index = -1
                if csv_headers:
                    try:
                        # Find the index, ignoring case and stripping whitespace
                        product_id_index = [h.strip().lower() for h in csv_headers].index('product id')
                    except ValueError:
                        print("Warning: 'PRODUCT ID' header not found. Cannot sort by Product ID.")
                        csv_rows = temp_rows # Use unsorted rows if header not found

                if product_id_index != -1:
                    def sort_key(row):
                        try:
                            # Attempt to convert the value at the found index to an integer
                            return int(row[product_id_index])
                        except (ValueError, IndexError):
                            # If conversion fails or index is out of bounds,
                            # return a large number to place it at the end
                            return float('inf')

                    temp_rows.sort(key=sort_key)
                    print(f"Sorted {len(temp_rows)} rows by Product ID (Column Index: {product_id_index}).")
                    csv_rows = temp_rows[:501] # Apply limit *after* sorting
                else:
                    csv_rows = temp_rows[:501] # Apply limit even if sorting failed
            # --- END SORTING LOGIC ---


        except s3.exceptions.NoSuchKey:
             file_content_error = f"Error: The specified report file was not found in R2: '{r2_bucket}/{object_key}'"
             print(file_content_error)
        except Exception as e:
            file_content_error = f"Failed to download or parse R2 object '{r2_bucket}/{object_key}': {e}"
            print(f"Error details: {e}")

        return render_template(
            'hasil_rangkuman.html',
            result=result_data,
            task_id=task_id,
            csv_headers=csv_headers,
            csv_rows=csv_rows, # Pass the sorted (and limited) rows
            file_content_error=file_content_error
        )

    except redis.exceptions.ConnectionError:
        abort(503, description="Could not connect to the database to retrieve results.")
    except Exception as e:
        abort(500, description=f"An unexpected error occurred: {e}")