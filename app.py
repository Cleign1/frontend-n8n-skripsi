from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
from dotenv import load_dotenv
from pathlib import Path
import csv
import json
import requests
import datetime
import redis
from celery import Celery

# inisiasiasi env dengan dotenv
env_path = Path("./.env")
load_dotenv(dotenv_path=env_path)

# inisialisasi flask dan konfig secret key
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# setting upload folder dan celery
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Celery BEFORE creating the celery instance
app.config.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    # Windows-specific configurations
    worker_pool='solo',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# pastiin folder uploads ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

current_app_status = {
    "status": "Idle",
    "last_updated": datetime.datetime.now().isoformat()
}

# --- Integrasi Celery (Cara yang Disederhanakan) ---
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['broker_url']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Create celery instance AFTER configuration
celery = make_celery(app)

# Additional Windows-friendly Celery configurations
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=50,  # Lower for Windows
    # Make revocation more immediate
    worker_disable_rate_limits=True,
    task_always_eager=False,
    # Windows-specific
    worker_pool='solo',
    broker_connection_retry_on_startup=True,
)


# --- Koneksi Redis untuk Status ---
try:
    redis_conn = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    # Test connection
    redis_conn.ping()
    print("Redis connection successful!")
except redis.ConnectionError:
    print("Warning: Redis connection failed. Make sure Redis server is running.")
    redis_conn = None

# Task storage for tracking
def store_task_info(task_id, task_name, filename, created_at):
    """Store task information in Redis"""
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

def get_all_tasks():
    """Get all active tasks"""
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

def remove_task_from_list(task_id):
    """Remove task from active list"""
    if redis_conn:
        redis_conn.lrem("active_tasks", 0, task_id)

# Add this function to update status via API
def update_app_status_via_api(status_text):
    """Send status update via POST to /api/status"""
    try:
        payload = {"status": status_text}
        response = requests.post(
            'http://localhost:5000/api/status',
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            print(f"Status updated via API: {status_text}")
        else:
            print(f"Failed to update status via API: {response.status_code}")
    except Exception as e:
        print(f"Error updating status via API: {e}")

# --- Celery Task untuk Proses Latar Belakang ---
@celery.task(bind=True)
def process_csv_in_batches(self, filename, external_api_url):
    print(f"Task started: {self.request.id}")
    print(f"Filename: {filename}")
    print(f"URL: {external_api_url}")
    
    status_key = "batch_job_status"
    task_id = self.request.id
    
    def check_revoked():
        """Check if task has been revoked and raise exception if so"""
        try:
            # Use AsyncResult to check if task is revoked
            task_result = celery.AsyncResult(task_id)
            if task_result.state == 'REVOKED':
                raise Exception("Task was revoked by user")
        except Exception as e:
            # If we can't check revocation status, continue
            pass
    
    def update_status_in_redis(status_dict):
        if redis_conn:
            redis_conn.set(status_key, json.dumps(status_dict))
            redis_conn.hset(f"task:{task_id}", "last_message", status_dict.get('message', ''))
    
    def update_all_status(status_text, detailed_message=None):
        """Update both global app status and task-specific status"""
        global current_app_status
        current_app_status['status'] = status_text
        current_app_status['last_updated'] = datetime.datetime.now().isoformat()
        
        # Send via API
        update_app_status_via_api(status_text)
        
        # Update task-specific message
        if detailed_message and redis_conn:
            redis_conn.hset(f"task:{task_id}", "last_message", detailed_message)

    # Check for revocation at the start
    check_revoked()

    # Inisialisasi status di Redis
    initial_status = {
        'is_running': True, 
        'message': f"Membaca file {filename}...", 
        'progress': 0,
        'log': [f"[{datetime.datetime.now():%H:%M:%S}] Proses Celery dimulai."]
    }
    update_status_in_redis(initial_status)
    update_all_status("🔄 Memproses file CSV...", f"Membaca file {filename}...")

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    try:
        # Check for revocation before file operations
        check_revoked()
        
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            rows = list(csv.DictReader(csvfile))
            print(f"Successfully read {len(rows)} rows from {filename}")
    except Exception as e:
        if "revoked" in str(e).lower():
            # Handle revocation
            revoked_status = {
                'is_running': False, 
                'message': "Task dihentikan oleh user", 
                'progress': 0,
                'log': initial_status['log'] + [f"[{datetime.datetime.now():%H:%M:%S}] Task dihentikan"]
            }
            update_status_in_redis(revoked_status)
            update_all_status("⏹️ Task dihentikan", "Task dihentikan oleh user")
            return {"revoked": "Task was terminated by user"}
        
        error_msg = f"Error: Gagal membaca file. {e}"
        error_status = { 
            'is_running': False, 
            'message': error_msg, 
            'progress': 100, 
            'log': initial_status['log'] + [f"[{datetime.datetime.now():%H:%M:%S}] {error_msg}"]
        }
        update_status_in_redis(error_status)
        update_all_status("❌ Error membaca file", error_msg)
        return {"error": error_msg}

    batch_size = 500
    total_rows = len(rows)
    total_batches = (total_rows + batch_size - 1) // batch_size
    
    current_status = initial_status.copy()
    current_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] Ditemukan {total_rows} baris, akan dikirim dalam {total_batches} batch.")
    update_status_in_redis(current_status)
    update_all_status(f"📤 Mengirim data ({total_rows} baris)", f"Ditemukan {total_rows} baris, akan dikirim dalam {total_batches} batch")

    successful_batches = 0
    for i in range(total_batches):
        # Check for revocation at the start of each batch
        try:
            check_revoked()
        except Exception as e:
            revoked_status = json.loads(redis_conn.get(status_key)) if redis_conn else current_status
            revoked_status.update({
                'is_running': False, 
                'message': "Task dihentikan oleh user", 
                'progress': int(((i) / total_batches) * 100)
            })
            revoked_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] Task dihentikan pada batch {i + 1}")
            update_status_in_redis(revoked_status)
            update_all_status("⏹️ Task dihentikan", f"Task dihentikan pada batch {i + 1}")
            return {"revoked": f"Task was terminated at batch {i + 1}"}
        
        start_index, end_index = i * batch_size, i * batch_size + batch_size
        batch = rows[start_index:end_index]
        progress = int(((i + 1) / total_batches) * 100)
        
        current_status = json.loads(redis_conn.get(status_key)) if redis_conn else current_status
        current_status.update({
            'progress': progress, 
            'message': f"Mengirim batch {i + 1} dari {total_batches}..."
        })
        current_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] {current_status['message']}")
        update_status_in_redis(current_status)
        update_all_status(f"📤 Mengirim batch {i + 1}/{total_batches}", f"Mengirim batch {i + 1} dari {total_batches}...")

        try:
            print(f"Sending batch {i + 1} with {len(batch)} rows to {external_api_url}")
            
            # Use shorter timeout to make termination more responsive
            response = requests.post(external_api_url, json=batch, timeout=10)
            print(f"Batch {i + 1} response: {response.status_code}")
            
            if response.status_code == 200:
                successful_batches += 1
            else:
                print(f"Warning: Batch {i + 1} returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            # Check if this might be due to revocation
            try:
                check_revoked()
            except:
                # Task was revoked during HTTP request
                revoked_status = json.loads(redis_conn.get(status_key)) if redis_conn else current_status
                revoked_status.update({
                    'is_running': False, 
                    'message': "Task dihentikan selama pengiriman data", 
                    'progress': progress
                })
                revoked_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] Task dihentikan selama pengiriman batch {i + 1}")
                update_status_in_redis(revoked_status)
                update_all_status("⏹️ Task dihentikan", f"Task dihentikan selama pengiriman batch {i + 1}")
                return {"revoked": f"Task was terminated during batch {i + 1} send"}
            
            error_msg = f"Error pada batch {i + 1}: {e}"
            print(error_msg)
            error_status = json.loads(redis_conn.get(status_key)) if redis_conn else current_status
            error_status.update({
                'is_running': False, 
                'message': error_msg, 
                'progress': progress
            })
            error_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] {error_msg}")
            update_status_in_redis(error_status)
            update_all_status("❌ Error mengirim data", error_msg)
            return {"error": error_msg}

    final_msg = f'Semua {successful_batches} batch berhasil dikirim!'
    final_status = json.loads(redis_conn.get(status_key)) if redis_conn else current_status
    final_status.update({
        'is_running': False, 
        'message': final_msg, 
        'progress': 100
    })
    final_status['log'].append(f"[{datetime.datetime.now():%H:%M:%S}] Proses selesai.")
    update_status_in_redis(final_status)
    update_all_status("✅ Proses selesai", final_msg)
    
    print(f"Process completed successfully. Sent {successful_batches} batches.")
    return {"success": final_msg, "batches_sent": successful_batches}


# --- Fungsi Helper ---
def list_uploaded_files():
    files = []
    try:
        for f in os.listdir(UPLOAD_FOLDER):
            if f.lower().endswith('.csv'):
                files.append(f)
    except FileNotFoundError:
        pass
    return sorted(files)

# --- Route untuk Halaman ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update-stok', methods=['GET', 'POST'])
def update_stok():
    json_data = None
    files = list_uploaded_files()
    selected_file = None

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        uploaded_file = request.files.get('file')
        
        if selected_file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(filepath):
                with open(filepath, newline='', encoding='utf-8') as csvfile:
                    rows = list(csv.DictReader(csvfile))[:20]
                    json_data = json.dumps(rows, indent=2)
        elif uploaded_file and uploaded_file.filename:
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
            uploaded_file.save(save_path)
            files = list_uploaded_files()
            selected_file = uploaded_file.filename
            with open(save_path, newline='', encoding='utf-8') as csvfile:
                rows = list(csv.DictReader(csvfile))[:20]
                json_data = json.dumps(rows, indent=2)
                
    return render_template('upload_stok.html', json_data=json_data, files=files, selected_file=selected_file)

@app.route('/prediksi-stok')
def prediksi_stok():
    return render_template('prediksi_stok.html')

@app.route('/rangkuman')
def rangkuman():
    return render_template('rangkuman.html')

@app.route('/tasks')
def tasks():
    tasks = get_all_tasks()
    return render_template('tasks.html', tasks=tasks)

# --- Route untuk API ---
@app.route('/api/start_batch_process', methods=['POST'])
def start_batch_process():
    # Update app status when starting
    update_app_status_via_api("🚀 Memulai proses batch...")
    
    if redis_conn:
        status_str = redis_conn.get("batch_job_status")
        if status_str and json.loads(status_str).get('is_running'):
            return jsonify({"error": "Proses batch lain sedang berjalan."}), 409

    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Filename tidak disertakan"}), 400
    
    # Check if file exists
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": f"File {filename} tidak ditemukan"}), 404
    
    # external_api_url = "https://n8n.ibnukhaidar.live/webhook/update_stock"
    external_api_url = "http://localhost:8084/635f71d7-5aff-4615-b7be-20373c1b9f55"
    
    try:
        task = process_csv_in_batches.delay(filename, external_api_url)
        
        # Store task information
        task_name = f"Update Stok {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        store_task_info(task.id, task_name, filename, datetime.datetime.now().isoformat())
        
        print(f"Task started with ID: {task.id}")
        return jsonify({
            "message": "Proses pengiriman batch telah dimulai.", 
            "task_id": task.id
        }), 202
    except Exception as e:
        print(f"Error starting task: {e}")
        update_app_status_via_api("❌ Error memulai proses")
        return jsonify({"error": f"Gagal memulai proses: {e}"}), 500

@app.route('/api/batch_status', methods=['GET'])
def get_batch_status():
    if redis_conn:
        status_json = redis_conn.get("batch_job_status")
        if status_json:
            return jsonify(json.loads(status_json))
    
    return jsonify({
        'is_running': False, 
        'message': 'Belum ada proses yang berjalan.', 
        'progress': 0
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = get_all_tasks()
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>/terminate', methods=['POST'])
def terminate_task(task_id):
    try:
        # Use signal='KILL' for immediate termination
        celery.control.revoke(task_id, terminate=True, signal='KILL')
        
        # Update task status in Redis immediately
        if redis_conn:
            redis_conn.hset(f"task:{task_id}", "status", "REVOKED")
            redis_conn.hset(f"task:{task_id}", "last_message", "Task terminated by user")
            
            # Also update batch status if this task was running
            status_json = redis_conn.get("batch_job_status")
            if status_json:
                status_data = json.loads(status_json)
                if status_data.get('is_running'):
                    status_data.update({
                        'is_running': False,
                        'message': 'Task dihentikan oleh user',
                        'progress': status_data.get('progress', 0)
                    })
                    redis_conn.set("batch_job_status", json.dumps(status_data))
        
        # Update global status
        update_app_status_via_api("⏹️ Task dihentikan")
        
        return jsonify({"message": f"Task {task_id} telah dihentikan"}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menghentikan task: {e}"}), 500

@app.route('/api/tasks/<task_id>/remove', methods=['DELETE'])
def remove_task(task_id):
    try:
        # Remove from active tasks list
        remove_task_from_list(task_id)
        
        # Delete task info from Redis
        if redis_conn:
            redis_conn.delete(f"task:{task_id}")
        
        return jsonify({"message": f"Task {task_id} telah dihapus dari daftar"}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menghapus task: {e}"}), 500

@app.route('/api/tasks/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    try:
        celery_task = celery.AsyncResult(task_id)
        
        task_info = {
            'task_id': task_id,
            'status': celery_task.status,
            'result': str(celery_task.result) if celery_task.result else None
        }
        
        # Get additional info from Redis
        if redis_conn:
            redis_info = redis_conn.hgetall(f"task:{task_id}")
            task_info.update(redis_info)
        
        return jsonify(task_info)
    except Exception as e:
        return jsonify({"error": f"Gagal mendapatkan status task: {e}"}), 500

@app.route('/api/status', methods=['GET', 'POST'])
def status_endpoint():
    global current_app_status
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Data tidak valid"}), 400
        current_app_status['status'] = data.get('status')
        current_app_status['last_updated'] = datetime.datetime.now().isoformat()
        return jsonify({"message": "Status berhasil diperbarui"}), 200
    else:
        return jsonify(current_app_status)

# --- Error Handler ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- Menjalankan Aplikasi ---
if __name__ == '__main__':
    app.run(debug=True)