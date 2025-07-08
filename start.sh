#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Start the Flask app in the background
echo "Starting Flask app..."
uv run flask --app run.py run --debug --host=0.0.0.0 &
FLASK_PID=$!

# Start the Celery worker in the background
echo "Starting Celery worker..."
uv run celery -A make_celery.celery worker --loglevel=info --pool=solo -n worker1@%h &
CELERY_PID=$!

echo "Flask app running with PID: $FLASK_PID"
echo "Celery worker running with PID: $CELERY_PID"

# Function to clean up processes
cleanup() {
    echo "Caught SIGINT. Shutting down..."
    kill $FLASK_PID
    kill $CELERY_PID
    # Wait for processes to terminate
    wait $FLASK_PID
    wait $CELERY_PID
    echo "Shutdown complete."
}

# Trap SIGINT and call the cleanup function
trap cleanup SIGINT

# Wait for both processes to exit
wait $FLASK_PID $CELERY_PID
