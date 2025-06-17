# blueprints/prediction/routes.py
from flask import Blueprint, render_template

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/prediksi-stok')
def prediksi_stok():
    return render_template('prediksi_stok.html')