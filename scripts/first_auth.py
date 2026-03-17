#!/usr/bin/env python3
# scripts/first_auth.py
"""Interactive OAuth2 first-time authentication for Google Drive."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.drive_client import DriveClient


def main():
    config_dir = project_root / "config"

    if not (config_dir / "credentials.json").exists():
        print("ERROR: config/credentials.json not found.")
        print("Download it from Google Cloud Console → APIs & Services → Credentials.")
        print("See docs/setup-guide.md for step-by-step instructions.")
        sys.exit(1)

    print("Opening browser for Google OAuth login...")
    print("Grant read-only access to Google Drive when prompted.")
    print()

    try:
        client = DriveClient(config_dir=config_dir, folder_name="Meeting notes")
        print()
        print("Authentication successful!")
        print(f"Token saved to {config_dir / 'token.json'}")

        # Test by listing folder
        docs = client.list_meeting_notes()
        print(f"Found {len(docs)} meeting note(s) in Drive.")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
