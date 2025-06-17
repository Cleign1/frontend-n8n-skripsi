# celery_app.py
from celery import Celery
from config import Config

celery = Celery(
    'frontend-n8n-skripsi',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.result_backend,
    include=['blueprints.main.tasks'] # Points to where your tasks are defined
)

# Apply the detailed Celery configuration
celery.conf.update(Config.CELERY_CONFIG)

# Optional: subclass Task to have app context
# This is handled in app.py in this new structure