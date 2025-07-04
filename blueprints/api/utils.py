# blueprints/api/utils.py
import requests
import datetime
import os

# This can be a simple dictionary for in-memory status
current_app_status = {
    "status": "Idle",
    "last_updated": datetime.datetime.now().isoformat()
}

def update_app_status_via_api(status_text):
    """Send status update via POST to the API endpoint."""
    try:
        # Get the base URL from an env var. Default to None if not set.
        base_url = os.getenv("INTERNAL_API_BASE_URL")
        if not base_url:
            # If the base URL isn't configured, we can't make the API call.
            # Log this and exit gracefully.
            print("Warning: INTERNAL_API_BASE_URL is not set. Cannot update app status via API.")
            return

        api_url = f"{base_url}/api/status"

        payload = {"status": status_text}
        response = requests.post(
            api_url,
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            print(f"Status updated via API: {status_text}")
        else:
            print(f"Failed to update status via API to {api_url}: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error updating status via API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in update_app_status_via_api: {e}")