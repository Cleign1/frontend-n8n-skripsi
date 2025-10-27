# blueprints/upload/routes.py
import os
import json
import csv
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename
from .utils import get_drive_service
import tempfile
from .task import upload_file_to_r2
import uuid

upload_bp = Blueprint('upload', __name__)

def list_uploaded_files():
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        return []
    return [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]

@upload_bp.route('/update-stok', methods=['GET', 'POST'])
def update_stok():
    json_data = None
    files = list_uploaded_files()
    selected_file = None

    if request.method == 'POST':
        uploaded_file = request.files.get('file')

        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(save_path)
            
            files = list_uploaded_files()
            selected_file = filename
            
            try:
                with open(save_path, newline='', encoding='utf-8') as csvfile:
                    rows = list(csv.DictReader(csvfile))[:20]
                    json_data = json.dumps(rows, indent=2)
            except Exception as e:
                # Handle potential errors with file reading or parsing
                json_data = json.dumps({"error": f"Could not process file: {e}"})


    return render_template('upload_stok.html', json_data=json_data, files=files, selected_file=selected_file)

@upload_bp.route('/upload/start_r2_upload', methods=['POST'])
def start_r2_upload():
    selected_date = request.form.get('selected_date')
    server_filename = request.form.get('server_filename')
    # Removed client_file logic as the file should already be on the server

    if not selected_date:
        return jsonify({'error': 'No date selected'}), 400

    if not server_filename:
        return jsonify({'error': 'No server filename provided'}), 400

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], server_filename)
    if not os.path.exists(filepath):
        return jsonify({'error': f'Server file {server_filename} not found.'}), 404

    try:
        # Enqueue the Celery task
        task = upload_file_to_r2.delay(server_filename, selected_date)

        # --- Return the Celery task ID and the Display ID used in store_task_info ---
        # The Display ID is useful for linking to the /tasks page immediately
        # We need to peek into the task's request or generate it similarly here.
        # For simplicity, let's assume the task generates and returns it if needed,
        # or we just return the Celery ID for now.
        # Modify the task to return the display ID if needed.

        return jsonify({
            'message': f'R2 upload task started for {server_filename}.',
            'celery_task_id': task.id,
            # 'display_task_id': r2_task_display_id # Add this if the task returns it
            }), 202 # Accepted

    except Exception as e:
        print(f"Error starting R2 upload task: {e}")
        return jsonify({'error': f'An error occurred: {e}'}), 500