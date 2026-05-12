"""
One-time YouTube OAuth setup.

Steps:
1. Go to https://console.cloud.google.com/
2. Create a project → Enable "YouTube Data API v3"
3. Credentials → Create OAuth 2.0 Client ID → Desktop App
4. Download JSON → rename to client_secrets.json → put in this folder
5. Run: python setup_youtube.py
6. Browser opens → log in → approve → done!
"""

import os
import pickle
import sys

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def main():
    print("\n[AUTH] YouTube OAuth Setup")
    print("-" * 40)

    if not os.path.exists("client_secrets.json"):
        print("[ERROR] client_secrets.json not found!")
        print("\nSteps to get it:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create project -> Enable 'YouTube Data API v3'")
        print("  3. Credentials -> Create OAuth 2.0 Client ID -> Desktop App")
        print("  4. Download JSON -> rename to client_secrets.json")
        print("  5. Put it in this folder, then re-run this script")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print("[ERROR] Missing packages. Run: pip install -r requirements.txt")
        sys.exit(1)

    creds = None

    if os.path.exists("youtube_token.json"):
        with open("youtube_token.json", "rb") as f:
            creds = pickle.load(f)

    if creds and creds.valid:
        print("[OK] Already authenticated! Token is valid.")
        return

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("[OK] Token refreshed successfully!")
        except Exception:
            creds = None

    if not creds or not creds.valid:
        print("\n[BROWSER] Opening browser for Google login...")
        flow  = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
        creds = flow.run_local_server(port=0)

    with open("youtube_token.json", "wb") as f:
        pickle.dump(creds, f)

    print("[OK] Authentication successful! youtube_token.json created.")
    print("   You can now run: python main.py")


if __name__ == "__main__":
    main()
