from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.drive_client import DriveClient


class TestDriveClient:
    @patch("src.drive_client.build")
    @patch("src.drive_client.Credentials")
    def test_list_meeting_notes(self, mock_creds_cls, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.files().list().execute.return_value = {
            "files": [
                {"id": "doc1", "name": "Meeting Notes - Standup", "modifiedTime": "2026-03-17T10:00:00.000Z"},
                {"id": "doc2", "name": "Meeting Notes - Planning", "modifiedTime": "2026-03-16T09:00:00.000Z"},
            ]
        }
        client = DriveClient.__new__(DriveClient)
        client._service = mock_service
        client._folder_name = "Meeting notes"
        client._folder_id = "folder123"
        files = client.list_meeting_notes(since=datetime(2026, 3, 15))
        assert len(files) == 2
        assert files[0]["id"] == "doc1"

    @patch("src.drive_client.build")
    @patch("src.drive_client.Credentials")
    def test_download_document(self, mock_creds_cls, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.files().export().execute.return_value = b"Document content here"
        client = DriveClient.__new__(DriveClient)
        client._service = mock_service
        content = client.download_document("doc1")
        assert content == "Document content here"
