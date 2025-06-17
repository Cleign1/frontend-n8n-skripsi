# blueprints/summary/routes.py
from flask import Blueprint, render_template

summary_bp = Blueprint('summary', __name__)

@summary_bp.route('/rangkuman')
def rangkuman():
    return render_template('rangkuman.html')