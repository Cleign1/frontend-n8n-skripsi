"""
WSGI entrypoint for Gunicorn using Eventlet.

This file ensures eventlet monkey-patching happens as early as possible,
before importing any other modules that rely on threading/ssl.
"""

import eventlet

# IMPORTANT: Monkey-patch before any other imports
eventlet.monkey_patch()

from app import create_app  # noqa: E402

# Create the Flask application instance
app = create_app()

# Gunicorn will look for a WSGI callable named "app" in this module.
