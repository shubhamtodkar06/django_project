import os
import tempfile  # Import tempfile
from googleapiclient.http import MediaFileUpload
# ... other importsfrom googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload # Correct import
# --- Google Drive API Setup ---
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.path.join(settings.BASE_DIR, 'service_account_credentials.json')

creds = None
service = None  # Initialize service to None

try:
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        print("Connected to Google Drive!")
    else:
        print(f"Credentials file not found: {SERVICE_ACCOUNT_FILE}")  # Just print, handle in view
except Exception as e:
    print(f"Error connecting to Google Drive: {e}")


def get_drive_service():
    global service  # Access the global service
    return service  # Return it

def upload_to_drive(service, uploaded_file, drive_folder_id):
    if service is None:
        print("Google Drive service not initialized. Cannot upload file.")
        return None

    try:
        file_metadata = {'name': uploaded_file.name, 'parents': [drive_folder_id]}

        # More robust temporary file handling:
        temp_file_path = None  # Initialize to None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file: # Add suffix
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name # Get the temporary file path
            
            media = MediaFileUpload(temp_file_path, mimetype=uploaded_file.content_type)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"File ID: {file.get('id')}")

            return file.get('id')

        finally: # This block will always execute
            if temp_file_path: # Check if temp_file_path is set
                try:
                    os.remove(temp_file_path) # Remove the temp file
                except Exception as e:
                    print(f"Error removing temp file: {e}") # Handle remove errors

    except Exception as e:
        print(f"Error uploading to Drive: {e}")
        return None
 
def delete_file_from_drive(service, file_id):
    if service is None:
        print("Google Drive service not initialized. Cannot delete file.")
        return False

    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting file from Drive: {e}")
        return False


def fetch_file_content_from_drive(service, file_id):
    if service is None:
        print("Google Drive service not initialized. Cannot fetch file.")
        return None

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
        fh.seek(0)
        return fh.getvalue()
    except Exception as e:
        print(f"Error fetching file from Google Drive: {e}")
        return None

# ... (other utility functions if needed - remember to add 'service' as the first argument)