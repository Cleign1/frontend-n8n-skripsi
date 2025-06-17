# blueprints/tasks/routes.py
from flask import Blueprint, render_template
from .utils import get_all_tasks

tasks_bp = Blueprint('tasks_ui', __name__) # Renamed to avoid conflict with 'tasks' module

@tasks_bp.route('/tasks')
def tasks():
    tasks_list = get_all_tasks()
    return render_template('tasks.html', tasks=tasks_list)