import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    gdrive_json = 'backend/oauth_client_secret.json'
    token_json = 'backend/token.json'
    
    # Adjust paths if run from inside the backend directory
    if not os.path.exists(gdrive_json) and os.path.exists('oauth_client_secret.json'):
        gdrive_json = 'oauth_client_secret.json'
        token_json = 'token.json'
        
    if not os.path.exists(gdrive_json):
        print(f"Error: OAuth Client Secret file not found. Place your Client Secret JSON at '{gdrive_json}'.")
        sys.exit(1)
        
    print("Starting authentication flow...")
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
    
    with open(token_json, 'w') as token_file:
        token_file.write(creds.to_json())
        
    print(f"\nSuccess! Token saved to: {token_json}")

if __name__ == '__main__':
    main()
