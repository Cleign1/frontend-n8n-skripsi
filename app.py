# app.py
import os
import redis
import logging
from flask import Flask
from config import Config
from celery_app import celery
from blueprints import register_blueprints
from celery.contrib.abortable import AbortableTask
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from dateutil import parser
from babel.dates import format_datetime as babel_format_datetime

# Get the absolute path of the project's root directory (where app.py is located)
_basedir = os.path.abspath(os.path.dirname(__file__))

# Socket initialization
socketio = SocketIO(message_queue=Config.CELERY_BROKER_URL, transports=['polling'])

class SocketIOHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        # The 'socketio' object is globally available in this module
        socketio.emit('log_message', {'data': log_entry, 'logger_name': record.name})

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

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config.from_object(config_class)

    # Ensure the upload folder exists
    upload_folder = os.path.join(_basedir, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    # Store the absolute path in the config for consistency
    app.config['UPLOAD_FOLDER'] = upload_folder

    # custom jinja filter untuk format datetime
    @app.template_filter('format_datetime')
    def _format_datetime(value, format='medium'):
        if value is None:
            return ""
        dt = parser.parse(value)
        if format == 'full':
            format="EEEE, d MMMM y 'at' h:mm:ss a"
        elif format == 'medium':
            format="dd MMM y, HH:mm"
        return babel_format_datetime(dt, format, locale='en')

    # Initialize extensions
    socketio.init_app(app)
    init_celery(app)

    # Register blueprints
    register_blueprints(app)


    # --- Setup Logging for the Flask App ---
    socket_handler = SocketIOHandler()
    socket_handler.setLevel(logging.INFO)
    socket_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(socket_handler)
    logging.getLogger('werkzeug').addHandler(socket_handler) # Capture Werkzeug logs too


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
