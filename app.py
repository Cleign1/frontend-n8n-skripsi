from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, jsonify
import os
from dotenv import load_dotenv
from pathlib import Path
import csv
import json
import requests

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

@app.route('/api/send_full_csv', methods=['POST'])
def send_full_csv():
    data = request.get_json()
    filename = data.get('filename') if data else None
    if not filename:
        return jsonify({"error": "Filename tidak disertakan"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "File tidak ditemukan"}), 404

    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except Exception as e:
        return jsonify({"error": f"Gagal membaca file CSV: {str(e)}"}), 500

    # external_api_url = "https://n8n.ibnukhaidar.live/webhook/update_stock"
    external_api_url = "http://localhost:5678/webhook/update_stock"
    # external_api_url = "http://localhost:5678/webhook-test/update_stock"
    # external_api_url = "https://n8n.ibnukhaidar.live/webhook-test/update_stock"

    batch_size = 500
    total = len(rows)
    responses = []

    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        try:
            response = requests.post(
                external_api_url,
                json=batch,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            try:
                resp_json = response.json()
            except ValueError:
                resp_json = response.text
            responses.append({
                "batch_index": i//batch_size,
                "status_code": response.status_code,
                "response": resp_json
            })
        except requests.exceptions.RequestException as e:
            return jsonify({
                "error": f"Gagal kirim batch ke {external_api_url}: {str(e)}",
                "sent_batches": responses
            }), 500

    return jsonify({
        "message": f"File {filename} berhasil dikirim ke API eksternal dalam {len(responses)} batch",
        "batch_responses": responses
    })


@app.route('/predictions')
def predictions():
    return render_template('predictions.html')

@app.route('/manage_csv')
def manage_csv():
    files = list_uploaded_files()
    return render_template('manage_csv.html', files=files)


if __name__ == '__main__':
    app.run(debug=True)
