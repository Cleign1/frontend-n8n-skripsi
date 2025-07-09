# blueprints/upload/routes.py
import os
import json
import csv
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename
from .utils import get_drive_service
import tempfile

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

@upload_bp.route('/upload/upload_to_gdrive', methods=['POST'])
def upload_to_gdrive():
    selected_date = request.form.get('selected_date')
    server_filename = request.form.get('server_filename')
    client_file = request.files.get('file')

    if not selected_date:
        return jsonify({'error': 'No date selected'}), 400

    if not client_file and not server_filename:
        return jsonify({'error': 'No file provided'}), 400

    # *** IMPORTANT: Replace with your actual Google Drive Folder ID ***
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'YOUR_FOLDER_ID_HERE')

    if GOOGLE_DRIVE_FOLDER_ID == 'YOUR_FOLDER_ID_HERE':
        return jsonify({'error': 'Google Drive folder ID is not configured in the backend.'}), 500

    try:
        drive = get_drive_service()
        
        if client_file:
            filename = secure_filename(client_file.filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            client_file.save(temp_path)
        else:
            filename = secure_filename(server_filename)
            temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(temp_path):
                return jsonify({'error': f'Server file {filename} not found.'}), 404

        new_filename = f"daily_sales_{selected_date}.csv"

        drive_file = drive.CreateFile({
            'title': new_filename,
            'parents': [{'id': GOOGLE_DRIVE_FOLDER_ID}]
        })
        
        drive_file.SetContentFile(temp_path)
        drive_file.Upload()

        if client_file:
            os.remove(temp_path)

        return jsonify({'message': f'File {new_filename} uploaded successfully to Google Drive.'})

    except Exception as e:
        print(f"Google Drive Upload Error: {e}")
        return jsonify({'error': f'An error occurred during Google Drive upload: {e}'}), 500
