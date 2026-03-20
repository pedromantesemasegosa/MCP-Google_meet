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

Google Cloud Console now uses the **Google Auth platform** section (previously
"OAuth consent screen"). The setup is split into three tabs: **Branding**,
**Audience**, and **Data Access**.

### 3a. Branding (app info)

1. In the side menu, go to **"Google Auth platform"** → **"Branding"**
   (ES: "Plataforma de Google Auth" → "Marca")
2. If it's the first time, click **"Get Started"** / **"Empezar"**
3. Fill in:
   - App name: "MCP Meet Notes"
   - User support email: your email
4. Click **"Next"** / **"Siguiente"**
5. Enter your developer contact email
6. Click **"Next"** / **"Siguiente"** through the remaining steps and then
   **"Create"** / **"Crear"**

### 3b. Audience (user type)

1. Go to **"Google Auth platform"** → **"Audience"**
   (ES: "Audiencia")
2. Select **"Internal"** if using Google Workspace, or **"External"** for
   personal accounts
3. Click **"Save"** / **"Guardar"**

> If you chose "External", you'll need to add your email as a **test user**
> under "Test users" on this same page.

### 3c. Data Access (scopes / permissions)

1. Go to **"Google Auth platform"** → **"Data Access"**
   (ES: "Acceso a datos")
2. Click **"Add or Remove Scopes"** / **"Agregar o quitar permisos"**
3. In the search box, paste: `https://www.googleapis.com/auth/drive.readonly`
4. If it doesn't appear in the filtered list, add it manually — it will show
   up as a **Google Drive** permission (non-sensitive), which is normal
5. Click **"Update"** / **"Actualizar"**, then **"Save"** / **"Guardar"**

> `drive.readonly` is categorized as a non-sensitive Drive permission. This
> means your app won't require Google's OAuth verification process — it works
> immediately for your account and any test users you've added.

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

## What you can ask

Once the MCP server is running and your meetings are synced, you can ask Claude
questions like these directly in the chat — no commands needed.

**Activity & summaries**
- "What happened in meetings this week?"
- "Give me an executive summary of March"
- "What decisions were made in the last two weeks?"

**Topics & projects**
- "Has the onboarding redesign been discussed recently? Is it moving forward?"
- "How has the database performance topic evolved over the last month?"
- "What was said about the Q2 roadmap across all meetings?"

**People**
- "Who has contributed the most in the last few meetings?"
- "What has Laura been working on this month?"
- "Who has the most open action items right now?"

**Action items**
- "What action items are pending from this week?"
- "Do I have any tasks assigned to me?"
- "Are there any action items from the client review that haven't been followed up?"

**Patterns & signals**
- "Is there any topic that keeps coming up without resolution?"
- "Which meetings had the most participants?"
- "Any blockers mentioned in recent syncs?"

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