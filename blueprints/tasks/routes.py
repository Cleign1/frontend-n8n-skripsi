# blueprints/tasks/routes.py
from flask import Blueprint, render_template, request, jsonify, current_app
from .utils import get_all_tasks

tasks_bp = Blueprint('tasks_ui', __name__)


@tasks_bp.route('/tasks')
def tasks():
    tasks_list = get_all_tasks()
    return render_template('tasks.html', tasks=tasks_list)


@tasks_bp.route('/prediksi-stok', methods=['GET', 'POST'])
def prediksi_stok_task():
    workflow_2_url = current_app.config.get('WORKFLOW_2')
    return render_template('prediksi_stok.html', n8n_webhook_url=workflow_2_url)