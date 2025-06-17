# blueprints/main/tasks.py
import os
import csv
import json
import datetime
import requests
from flask import current_app
from celery_app import celery
from ..api.utils import update_app_status_via_api


@celery.task(bind=True)
def process_csv_in_batches(self, filename, external_api_url):
    """
    Processes a CSV file in batches and sends the data to an external API.
    This task is abortable and has robust error handling.
    """
    task_id = self.request.id
    redis_conn = current_app.redis_conn
    status_key = "batch_job_status"

    # --- FIX: The check function now looks at the Redis flag ---
    def check_aborted():
        """
        Checks if an abort flag has been set for this task in Redis.
        This is more reliable than self.is_aborted() alone.
        """
        if redis_conn and redis_conn.exists(f"task-aborted:{task_id}"):
            # Clean up the flag once we've seen it
            redis_conn.delete(f"task-aborted:{task_id}")
            raise Exception("Task aborted by user")

    def update_status_in_redis(status_dict):
        # ... (this function is correct) ...
        if redis_conn:
            redis_conn.set(status_key, json.dumps(status_dict))
            redis_conn.hset(f"task:{task_id}", "last_message", status_dict.get('message', ''))

    def update_all_status(status_text, detailed_message=None):
        # ... (this function is correct) ...
        update_app_status_via_api(status_text)
        if detailed_message and redis_conn:
            redis_conn.hset(f"task:{task_id}", "last_message", detailed_message)

    # --- Task Execution Starts Here ---
    try:
        check_aborted()

        # STEP 1: Initialization and Reading the File
        initial_status = {
            'is_running': True, 'message': f"Membaca file {filename}...", 'progress': 0,
            'log': [f"[{datetime.datetime.now():%H:%M:%S}] Proses Celery dimulai."]
        }
        update_status_in_redis(initial_status)
        update_all_status("🔄 Memproses file CSV...", f"Membaca file {filename}...")

        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)

        with open(filepath, newline='', encoding='utf-8') as csvfile:
            rows = list(csv.DictReader(csvfile))
        print(f"Successfully read {len(rows)} rows from {filename}")

        # STEP 2: Main Processing Loop
        batch_size = 500
        total_rows = len(rows)
        total_batches = (total_rows + batch_size - 1) // batch_size
        update_all_status(f"📤 Mengirim data ({total_rows} baris)", f"Ditemukan {total_rows} baris.")

        for i in range(total_batches):
            check_aborted()  # This will now work correctly!

            start_index, end_index = i * batch_size, i * batch_size + batch_size
            batch = rows[start_index:end_index]
            progress = int(((i + 1) / total_batches) * 100)

            status_update = {
                'is_running': True, 'progress': progress, 'message': f"Mengirim batch {i + 1}/{total_batches}...",
                'log': json.loads(redis_conn.get(status_key) or '{}').get('log', []) + [
                    f"[{datetime.datetime.now():%H:%M:%S}] Mengirim batch {i + 1}."]
            }
            update_status_in_redis(status_update)
            update_all_status(f"📤 Mengirim batch {i + 1}/{total_batches}", f"Mengirim batch {i + 1}...")

            response = requests.post(external_api_url, json=batch, timeout=20)
            response.raise_for_status()

        # STEP 3: Finalization if loop completes successfully
        final_msg = f'Semua {total_batches} batch berhasil dikirim!'
        final_status = {
            'is_running': False, 'message': final_msg, 'progress': 100,
            'log': json.loads(redis_conn.get(status_key) or '{}').get('log', []) + [
                f"[{datetime.datetime.now():%H:%M:%S}] Proses selesai."]
        }
        update_status_in_redis(final_status)
        update_all_status("✅ Proses selesai", final_msg)

        return {"success": final_msg, "batches_sent": total_batches}

    except Exception as e:
        # --- ROBUST EXCEPTION HANDLER ---
        current_status = json.loads(redis_conn.get(status_key) or '{}') if redis_conn else {}
        log = current_status.get('log', [])

        if "aborted by user" in str(e).lower():
            message = "Task dihentikan oleh user"
            log.append(f"[{datetime.datetime.now():%H:%M:%S}] {message}")
            aborted_status = {
                'is_running': False, 'message': message, 'progress': current_status.get('progress', 0), 'log': log
            }
            update_status_in_redis(aborted_status)
            update_all_status("⏹️ Task dihentikan", message)
            return {"revoked": message}
        else:
            error_message = f"Error tak terduga dalam task: {e}"
            log.append(f"[{datetime.datetime.now():%H:%M:%S}] {error_message}")
            error_status = {
                'is_running': False, 'message': error_message, 'progress': current_status.get('progress', 0), 'log': log
            }
            update_status_in_redis(error_status)
            update_all_status("❌ Error", error_message)
            raise e
