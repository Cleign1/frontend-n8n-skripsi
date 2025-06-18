# make_celery.py
import logging
from app import create_app, SocketIOHandler  # <-- Import the handler class directly
from celery_app import celery
from celery.signals import after_setup_logger

# Create the Flask app to establish an application context for tasks
app = create_app()


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """
    This function is called when the Celery worker sets up its logger.
    We add our custom SocketIOHandler to it.
    """
    # Create a new handler instance for the Celery logger
    socket_handler = SocketIOHandler()
    socket_handler.setLevel(logging.INFO)
    socket_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))

    # Add the custom handler to the Celery logger
    logger.addHandler(socket_handler)
