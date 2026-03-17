# Google Cloud Setup Guide

Step-by-step guide to configure Google Cloud OAuth for MCP Meet Notes.

## Prerequisites

- A Google account (personal or Workspace)
- Access to Google Cloud Console
- Python 3.11+ installed

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "MCP Meet Notes" (or anything you prefer)
4. Click "Create"

## Step 2: Enable Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "Internal" if using Google Workspace, or "External" for personal accounts
3. Fill in:
   - App name: "MCP Meet Notes"
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. On "Scopes", click "Add or Remove Scopes"
6. Add: `https://www.googleapis.com/auth/drive.readonly`
7. Click "Save and Continue" through the remaining steps

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "MCP Meet Notes"
5. Click "Create"
6. Click "Download JSON"
7. Save the file as `config/credentials.json` in this project

## Step 5: First Authentication

```bash
python scripts/first_auth.py
```

This opens your browser. Log in with your Google account and grant read-only
access to Drive. The token is saved to `config/token.json` for future use.

## Step 6: Install Daily Sync

```bash
bash scripts/install_launchd.sh
```

This installs a macOS launchd job that syncs meetings daily at 9:00 AM.

## Step 7: Configure MCP Server

Add to your Claude Code or Cursor MCP settings:

```json
{
  "mcpServers": {
    "meet-notes": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/MCP-Meet"
    }
  }
}
```

## Troubleshooting

### "Token refresh failed"
Your refresh token expired. Run `python scripts/first_auth.py` again.

### "Folder 'Meeting notes' not found"
Check `config/settings.json` — the `drive_folder_name` must match your
Google Drive folder name exactly. Gemini may use a localized name
(e.g., "Notas de la reunion" in Spanish).

### Workspace admin restrictions
If your Workspace admin blocks third-party OAuth apps, you may need to
request approval or ask your admin to allowlist the app.
