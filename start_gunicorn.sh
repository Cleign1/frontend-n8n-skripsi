#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# The host and port Gunicorn will bind to.
# '0.0.0.0' makes it accessible from other machines on the network.
HOST="0.0.0.0"
PORT="5000"
# The number of Gunicorn worker processes.
# A common recommendation is (2 * number of CPU cores) + 1.
WORKERS=4
# The location of your Flask app instance.
# Format: <module_name>:<flask_app_variable_name>
# Use the dedicated WSGI entrypoint that monkey-patches with eventlet early
APP_MODULE="wsgi:app"

# --- Environment Activation ---
echo "Activating virtual environment..."
source .venv/bin/activate

# --- Process Management ---
# Function to clean up background processes on exit
cleanup() {
    echo "Caught signal. Shutting down gracefully..."
    # Kill the entire process group to ensure all Gunicorn workers and Celery shut down
    if [ -n "$GUNICORN_PID" ]; then
        kill -s TERM -- -$GUNICORN_PID
    fi
    if [ -n "$CELERY_PID" ]; then
        kill -s TERM $CELERY_PID
    fi
    echo "Shutdown complete."
}

# Trap signals to call the cleanup function
trap cleanup SIGINT SIGTERM SIGHUP

# --- Service Startup ---
# Start Gunicorn in the background
echo "Starting Gunicorn server (eventlet worker)..."
# Using 'set -m' enables job control, allowing us to kill the process group
set -m
uv run gunicorn --worker-class eventlet --bind $HOST:$PORT --workers $WORKERS $APP_MODULE &
GUNICORN_PID=$!
set +m

# Start the Celery worker in the background
echo "Starting Celery worker..."
uv run celery -A make_celery.celery worker --loglevel=info --pool=solo -n worker1@%h &
CELERY_PID=$!

echo "----------------------------------------"
echo "Gunicorn running with PID: $GUNICORN_PID"
echo "Celery worker running with PID: $CELERY_PID"
echo "Access your application at http://$HOST:$PORT"
echo "Press Ctrl+C to shut down."
echo "----------------------------------------"

# Wait for any process to exit
wait -n
# Call cleanup in case one process dies, to ensure the other is also stopped
cleanup
