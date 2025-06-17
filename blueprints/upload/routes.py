# blueprints/upload/routes.py
import os
import json
import csv
from flask import Blueprint, render_template, request, current_app
from .utils import list_uploaded_files

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/update-stok', methods=['GET', 'POST'])
def update_stok():
    json_data = None
    files = list_uploaded_files()
    selected_file = None

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        uploaded_file = request.files.get('file')

        if selected_file:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(filepath):
                with open(filepath, newline='', encoding='utf-8') as csvfile:
                    rows = list(csv.DictReader(csvfile))[:20]
                    json_data = json.dumps(rows, indent=2)
        elif uploaded_file and uploaded_file.filename:
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uploaded_file.filename)
            uploaded_file.save(save_path)
            files = list_uploaded_files()
            selected_file = uploaded_file.filename
            with open(save_path, newline='', encoding='utf-8') as csvfile:
                rows = list(csv.DictReader(csvfile))[:20]
                json_data = json.dumps(rows, indent=2)

    return render_template('upload_stok.html', json_data=json_data, files=files, selected_file=selected_file)