# celery_app.py
from celery import Celery
from config import Config

celery = Celery(
    'frontend-n8n-skripsi',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.result_backend,
    include=['blueprints.main.tasks'] # Points to where your tasks are defined
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Jakarta',
    enable_utc=False,
    broker_connection_retry_on_startup=True,
)

# Apply the detailed Celery configuration
def create_celery_app(app):
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery