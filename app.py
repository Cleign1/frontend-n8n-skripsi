from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
from dotenv import load_dotenv
from pathlib import Path
import csv
import json

env_path = Path("./.env")
loaded = load_dotenv(dotenv_path=env_path)


app = Flask(__name__)
app.secret_key = loaded
app.secret_key = os.getenv("SECRET_KEY")

app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

def list_uploaded_files():
    # List semua file csv di folder uploads
    files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        if f.lower().endswith('.csv'):
            files.append(f)
    return sorted(files)

@app.route('/daily_sales', methods=['GET', 'POST'])
def upload_daily_sales():
    json_data = None
    files = list_uploaded_files()
    selected_file = None
    message = ''

    if request.method == 'POST':
        # Cek apakah user pilih file dari dropdown
        selected_file = request.form.get('selected_file')
        uploaded_file = request.files.get('file')
        
        if 'delete_all' in request.form:
            folder = app.config['UPLOAD_FOLDER']
            count = 0
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    count += 1
            message = f'{count} file berhasil dihapus dari folder uploads.'
            files = list_uploaded_files()

        if selected_file and selected_file != "":  # Kalau pilih file dari list
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(filepath):
                with open(filepath, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)[:20]
                json_data = json.dumps(rows, indent=2)
            else:
                flash("File tidak ditemukan di server.")
        
        elif uploaded_file and uploaded_file.filename != '':
            # Simpan file baru
            if uploaded_file.filename.lower().endswith('.csv'):
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                uploaded_file.save(save_path)
                # Baca file yang baru diupload
                with open(save_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)[:20]
                json_data = json.dumps(rows, indent=2)
                # Refresh list file agar file baru muncul
                files = list_uploaded_files()
                selected_file = uploaded_file.filename
            else:
                flash("Hanya file CSV yang diperbolehkan.")
        else:
            flash("Silakan pilih file dari daftar atau upload file CSV.")

    return render_template('daily_sales.html', json_data=json_data, files=files, selected_file=selected_file)

@app.route('/predictions')
def predictions():
    return render_template('predictions.html')


if __name__ == '__main__':
    app.run(debug=True)
