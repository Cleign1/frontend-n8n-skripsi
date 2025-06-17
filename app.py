# app.py
import os
import redis
from flask import Flask
from config import Config
from celery_app import celery
from blueprints import register_blueprints
from celery.contrib.abortable import AbortableTask

# Get the absolute path of the project's root directory (where app.py is located)
_basedir = os.path.abspath(os.path.dirname(__file__))


def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    This is the application factory.
    """
    # Explicitly define the template and static folder paths
    app = Flask(
        __name__,
        template_folder=os.path.join(_basedir, 'templates'),
        static_folder=os.path.join(_basedir, 'static')
    )

    app.config.from_object(config_class)

    # Ensure the upload folder exists
    upload_folder = os.path.join(_basedir, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    # Store the absolute path in the config for consistency
    app.config['UPLOAD_FOLDER'] = upload_folder

    # Initialize extensions
    init_celery(app)

    # Register blueprints
    register_blueprints(app)

    # --- START OF FIX ---
    # Initialize Redis connection directly in the app factory.
    # This replaces the deprecated `@app.before_first_request`.
    try:
        app.redis_conn = redis.StrictRedis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB'],
            decode_responses=True
        )
        app.redis_conn.ping()
        print("Redis connection successful!")
    except redis.ConnectionError as e:
        print(f"Warning: Redis connection failed. {e}")
        app.redis_conn = None
    # --- END OF FIX ---

    return app


def init_celery(app):
    """Initializes Celery and makes it work with the Flask app context."""
    celery.conf.update(app.config)

    # Create a new base task class that has both the Flask app context
    # and the abortable functionality from Celery.
    class ContextAbortableTask(AbortableTask):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                # Call the parent class's __call__ method
                return super().__call__(*args, **kwargs)

    # Set this new combined class as the default for all Celery tasks.
    celery.Task = ContextAbortableTask