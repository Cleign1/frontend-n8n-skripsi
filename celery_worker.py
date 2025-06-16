from app import celery, app
import os

if __name__ == '__main__':
    # Force solo pool for Windows
    os.environ.setdefault('CELERY_POOL', 'solo')
    
    with app.app_context():
        celery.start(['worker', '--loglevel=info', '--pool=solo'])