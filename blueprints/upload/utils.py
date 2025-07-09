# blueprints/upload/utils.py
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

def get_drive_service():
    """
    Authenticates with Google Drive using a service account
    and returns a drive service instance.
    """
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    # IMPORTANT: This requires a 'client_secrets.json' file in the root directory
    # This file should be obtained from the Google Cloud Console for a service account.
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secrets.json', scope)
    drive = GoogleDrive(gauth)
    return drive
