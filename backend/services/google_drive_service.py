import os
import io
import re
import urllib.parse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from core.config import settings

def get_drive_service():
    """Authenticate and return Google Drive service client using OAuth 2.0 Credentials."""
    token_path = settings.GOOGLE_DRIVE_TOKEN_FILE
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(
            token_path, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        
    # If credentials are expired, attempt to refresh them
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the refreshed credentials back to file
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Error refreshing Google Drive OAuth token: {e}")
            creds = None
            
    if not creds:
        return None
        
    return build("drive", "v3", credentials=creds)

def extract_drive_file_id(url: str) -> str | None:
    """Extract Google Drive file ID from drive webContentLink or webViewLink."""
    # Match /file/d/FILE_ID/view
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
        
    # Match uc?id=FILE_ID
    parsed = urllib.parse.urlparse(url)
    queries = urllib.parse.parse_qs(parsed.query)
    if "id" in queries:
        return queries["id"][0]
        
    return None

async def upload_file_to_drive(filename: str, file_bytes: bytes, mime_type: str) -> dict:
    """Upload file bytes to Google Drive folder and make it publicly accessible."""
    service = get_drive_service()
    if not service:
        raise Exception(
            f"Google Drive OAuth token file '{settings.GOOGLE_DRIVE_TOKEN_FILE}' not found. "
            "Please run 'python backend/generate_token.py' on your host system to authenticate."
        )
    
    file_metadata = {
        "name": filename,
    }
    
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if folder_id:
        file_metadata["parents"] = [folder_id]
        
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
    )
    
    # Upload file
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webContentLink, webViewLink")
        .execute()
    )
    
    file_id = file.get("id")
    
    # Set public read permissions so students can download the file
    permission = {
        "type": "anyone",
        "role": "reader",
    }
    service.permissions().create(fileId=file_id, body=permission).execute()
    
    # Fetch updated details containing sharing links
    file = service.files().get(fileId=file_id, fields="id, webContentLink, webViewLink").execute()
    return file

async def delete_file_from_drive(file_url: str):
    """Delete file from Google Drive using its sharing URL."""
    service = get_drive_service()
    if not service:
        return
        
    file_id = extract_drive_file_id(file_url)
    if not file_id:
        print(f"Could not extract Google Drive file ID from URL: {file_url}")
        return
        
    try:
        service.files().delete(fileId=file_id).execute()
    except Exception as e:
        print(f"Failed to delete file {file_id} from Google Drive: {e}")
