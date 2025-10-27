# blueprints/api/utils.py
import requests
from datetime import datetime
from dateutil import tz
import os
import json # Import json
from flask import current_app
from app import socketio # Import socketio instance

# Remove the global variable 'current_app_status'

GLOBAL_STATUS_KEY = "global_app_status" # Define a Redis key
jakarta_tz = tz.gettz('Asia/Jakarta')


def update_app_status_via_api(status_text):
    """Update global status in Redis and emit Socket.IO event."""
    try:
        redis_conn = current_app.redis_conn
        if not redis_conn:
            print("Warning: Redis connection not available. Cannot update global status.")
            return

        now_iso = datetime.now(jakarta_tz).isoformat()
        status_data = {
            "status": status_text,
            "last_updated": now_iso
        }
        
        # Store the latest status in Redis
        redis_conn.set(GLOBAL_STATUS_KEY, json.dumps(status_data))
        
        # Emit the update to all connected clients
        socketio.emit('global_status_update', status_data)
        
        print(f"Global status updated via Redis & emitted: {status_text}")

    except Exception as e:
        print(f"An unexpected error occurred in update_app_status_via_api: {e}")

# Function to get current status (used by API endpoint and potentially other places)
def get_current_app_status():
    """Get the current global status from Redis."""
    redis_conn = current_app.redis_conn
    default_status = {"status": "Idle", "last_updated": datetime.now(jakarta_tz).isoformat()}
    if not redis_conn:
        return default_status
        
    status_json = redis_conn.get(GLOBAL_STATUS_KEY)
    if status_json:
        try:
            return json.loads(status_json)
        except json.JSONDecodeError:
            print("Warning: Could not decode global status JSON from Redis.")
            return default_status
    else:
        # Initialize if it doesn't exist
        redis_conn.set(GLOBAL_STATUS_KEY, json.dumps(default_status))
        return default_status