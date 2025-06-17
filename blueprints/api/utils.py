# blueprints/api/utils.py
import requests
import datetime

# This can be a simple dictionary for in-memory status
current_app_status = {
    "status": "Idle",
    "last_updated": datetime.datetime.now().isoformat()
}

def update_app_status_via_api(status_text):
    """Send status update via POST to the local /api/status endpoint."""
    try:
        # Assuming the app runs on localhost:5000
        payload = {"status": status_text}
        response = requests.post(
            'http://localhost:5000/api/status',
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            print(f"Status updated via API: {status_text}")
        else:
            print(f"Failed to update status via API: {response.status_code}")
    except Exception as e:
        print(f"Error updating status via API: {e}")