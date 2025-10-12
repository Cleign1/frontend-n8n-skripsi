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

    # N8N Webhook URL
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
    N8N_CHAT_WEBHOOK_URL = os.getenv("N8N_CHAT_WEBHOOK_URL")

    # GCP Bucket Config
    GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
    N8N_SUMMARY_WEBHOOK_URL = os.getenv("N8N_SUMMARY_WEBHOOK_URL")
    WORKFLOW_2 = os.getenv("WORKFLOW_2")

    # WORKFLOW_DEFINITIONS
    WORKFLOWS = {
        'update': {
            'title': 'Proses Update Stok',
            'steps': [
                {'id': os.getenv("UPDATE_STEP_1_ID"), 'name': 'Webhook Trigger', 'description': 'Webhook Trigger'},
                {'id': os.getenv("UPDATE_STEP_2_ID"), 'name': 'Process CSV', 'description': 'Mencari file CSV berdasarkan tanggals'},
                {'id': os.getenv("UPDATE_STEP_3_ID"), 'name': 'Download CSV', 'description': 'Mendownload file CSV'},
                {'id': os.getenv("UPDATE_STEP_4_ID"), 'name': 'Extract CSV File', 'description': 'Ekstrak file CSV'},
                {'id': os.getenv("UPDATE_STEP_5_ID"), 'name': 'Prepare Bulk Query', 'description': 'Siapkan kueri massal untuk pembaruan stok'},
                {'id': os.getenv("UPDATE_STEP_6_ID"), 'name': 'Eksekusi Kueri SQL', 'description': 'Mengeksekusi kueri SQL untuk memperbarui stok di database'},
            ]
        },
        # 'prediction': {
        #     'title': 'Proses Prediksi Stok',
        #     'steps': [
        #         {'id': os.getenv("PREDICTION_STEP_1_ID"), 'name': 'Webhook Trigger', 'description': 'Trigger untuk memulai prediksi stok'},
        #     ]
        # },
        # 'report': {
        #     'title': 'Proses Pembuatan Laporan',
        #     'steps': [
        #         {'id': os.getenv("REPORT_STEP_1_ID"), 'title': 'Menerima Panggilan Webhook', 'description': 'Alur kerja laporan dipicu.'},
        #     ]
        # }
    }

    # Celery configuration
    CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

    # Windows-specific Celery settings
    CELERY_CONFIG = {
        'worker_pool': 'solo',
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'timezone': 'Asia/Jakarta',
        'enable_utc': False,
        'task_acks_late': True,
        'worker_prefetch_multiplier': 1,
        'task_reject_on_worker_lost': True,
        'worker_max_tasks_per_child': 50,
        'worker_disable_rate_limits': True,
        'broker_connection_retry_on_startup': True,
        'task_always_eager': False
    }
