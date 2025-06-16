from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Celery instance
celery_app = Celery('tasks')

# Configure Celery for Windows
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_pool='solo',
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=50,
    worker_disable_rate_limits=True,
    broker_connection_retry_on_startup=True,
)