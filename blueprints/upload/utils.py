# blueprints/upload/utils.py
import os
from flask import current_app

def list_uploaded_files():
    """Returns a sorted list of CSV files in the upload folder."""
    files = []
    upload_folder = current_app.config['UPLOAD_FOLDER']
    try:
        for f in os.listdir(upload_folder):
            if f.lower().endswith('.csv'):
                files.append(f)
    except FileNotFoundError:
        pass
    return sorted(files)