import os
import sys
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Add parent directory / backend directory to sys.path for core imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from core.env_utils import update_env_file
except ImportError:
    try:
        from backend.core.env_utils import update_env_file
    except ImportError:
        def update_env_file(key: str, value: str, env_path: str | None = None) -> bool:
            os.environ[key] = value
            return True

SCOPES = ['https://www.googleapis.com/auth/drive']

def save_and_sync_credentials(creds, token_json_path: str):
    """Save credentials to token.json file and sync to GOOGLE_DRIVE_TOKEN in .env."""
    token_data = creds.to_json()
    
    # 1. Write to token.json file
    with open(token_json_path, 'w', encoding='utf-8') as f:
        f.write(token_data)
    print(f"Token saved to: {token_json_path}")
    
    # 2. Update .env file and os.environ
    env_updated = update_env_file("GOOGLE_DRIVE_TOKEN", token_data)
    if env_updated:
        print("GOOGLE_DRIVE_TOKEN updated in .env file and environment variables!")

def attempt_headless_refresh(token_json_path: str) -> bool:
    """Attempt to refresh existing credentials headlessly."""
    creds = None
    if os.path.exists(token_json_path):
        try:
            creds = Credentials.from_authorized_user_file(token_json_path, scopes=SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {token_json_path}: {e}")
    elif os.environ.get("GOOGLE_DRIVE_TOKEN"):
        try:
            token_info = json.loads(os.environ["GOOGLE_DRIVE_TOKEN"])
            creds = Credentials.from_authorized_user_info(token_info, scopes=SCOPES)
        except Exception as e:
            print(f"Could not load credentials from GOOGLE_DRIVE_TOKEN env var: {e}")
            
    if not creds:
        return False

    print("Existing credentials found. Attempting headless token refresh...")
    try:
        creds.refresh(Request())
        if creds.valid:
            print("Token refreshed successfully headlessly!")
            save_and_sync_credentials(creds, token_json_path)
            return True
    except Exception as e:
        print(f"Headless token refresh failed: {e}")
        
    return False

def main():
    gdrive_json = 'backend/oauth_client_secret.json'
    token_json = 'backend/token.json'
    
    # Adjust paths if run from inside the backend directory
    if not os.path.exists(gdrive_json) and os.path.exists('oauth_client_secret.json'):
        gdrive_json = 'oauth_client_secret.json'
        token_json = 'token.json'

    # Try headless refresh first
    if attempt_headless_refresh(token_json):
        print("\nAuthentication automation complete! No interactive login required.")
        return

    if not os.path.exists(gdrive_json):
        print(f"Error: OAuth Client Secret file not found. Place your Client Secret JSON at '{gdrive_json}'.")
        sys.exit(1)
        
    print("\nStarting interactive authentication flow...")
    print("This will open a browser window to log in to Google.")
    
    # Force offline access to get a refresh token so the app can refresh the token headlessly
    flow = InstalledAppFlow.from_client_secrets_file(gdrive_json, SCOPES)
    creds = flow.run_local_server(
        port=8085,
        authorization_prompt_message="Please visit this URL to authorize the app: {url}",
        success_message="The authorization flow has completed. You may close this window.",
        access_type="offline",
        prompt="consent"
    )
    
    save_and_sync_credentials(creds, token_json)
    print(f"\nSuccess! Authentication completed and synced.")

if __name__ == '__main__':
    main()

