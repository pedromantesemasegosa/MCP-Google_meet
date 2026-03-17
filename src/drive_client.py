"""Google Drive API client for fetching Gemini meeting notes."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveClient:
    def __init__(self, config_dir: Path, folder_name: str) -> None:
        self._config_dir = config_dir
        self._folder_name = folder_name
        self._credentials_path = config_dir / "credentials.json"
        self._token_path = config_dir / "token.json"
        self._service = self._authenticate()
        self._folder_id = self._find_folder_id()

    def _authenticate(self):
        creds = None
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                logger.warning("Token refresh failed. Manual re-auth required.")
                raise
        if not creds or not creds.valid:
            if not self._credentials_path.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found at {self._credentials_path}. "
                    "Run scripts/first_auth.py first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(self._credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        self._token_path.write_text(creds.to_json())
        return build("drive", "v3", credentials=creds)

    def _find_folder_id(self) -> str | None:
        query = (
            f"name = '{self._folder_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        response = self._service.files().list(
            q=query, spaces="drive", fields="files(id, name)"
        ).execute()
        files = response.get("files", [])
        if not files:
            logger.warning(f"Folder '{self._folder_name}' not found in Drive.")
            return None
        return files[0]["id"]

    def list_meeting_notes(self, since: datetime | None = None) -> list[dict]:
        if self._folder_id is None:
            return []
        query = (
            f"'{self._folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.document' and trashed = false"
        )
        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
            query += f" and modifiedTime > '{since_str}'"
        response = self._service.files().list(
            q=query, spaces="drive",
            fields="files(id, name, modifiedTime, createdTime)",
            orderBy="modifiedTime desc",
        ).execute()
        return response.get("files", [])

    def download_document(self, doc_id: str) -> str:
        content = self._service.files().export(
            fileId=doc_id, mimeType="text/plain"
        ).execute()
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return str(content)
