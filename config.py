# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()


class Config:
    """Base configuration settings."""
    SECRET_KEY = os.getenv("SECRET_KEY")
    UPLOAD_FOLDER = 'uploads'

    # Redis configuration
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = int(os.getenv('REDIS_PORT'))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    # Celery configuration
    CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

    # Windows-specific Celery settings
    CELERY_CONFIG = {
        'worker_pool': 'solo',
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'timezone': 'UTC',
        'enable_utc': True,
        'task_acks_late': True,
        'worker_prefetch_multiplier': 1,
        'task_reject_on_worker_lost': True,
        'worker_max_tasks_per_child': 50,
        'worker_disable_rate_limits': True,
        'broker_connection_retry_on_startup': True,
        'task_always_eager': False
    }