import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from src.syncer import Syncer

SAMPLE_DRIVE_DOC_CONTENT = """Date: March 17, 2026
Duration: 25 minutes
Attendees: Pedro Mantese, Laura Garcia

Summary
Discussed migration progress and blockers.

Transcript
Pedro: How is the migration going?
Laura: Blocked on permissions.

Action items
- Pedro: Review PR
- Laura: Fix permissions"""


class TestSyncer:
    def test_sync_new_document(self, tmp_path):
        meetings_dir = tmp_path / "meetings"
        meetings_dir.mkdir()
        mock_drive = MagicMock()
        mock_drive.list_meeting_notes.return_value = [
            {"id": "doc1", "name": "Standup Backend", "modifiedTime": "2026-03-17T10:00:00.000Z"},
        ]
        mock_drive.download_document.return_value = SAMPLE_DRIVE_DOC_CONTENT
        syncer = Syncer(meetings_dir=meetings_dir, drive_client=mock_drive)
        syncer.sync()
        md_files = list(meetings_dir.glob("*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "Standup Backend" in content
        index_path = meetings_dir / "index.json"
        assert index_path.exists()
        index_data = json.loads(index_path.read_text())
        assert len(index_data["meetings"]) == 1
        assert index_data["meetings"][0]["source_doc_id"] == "doc1"

    def test_sync_idempotent(self, tmp_path):
        meetings_dir = tmp_path / "meetings"
        meetings_dir.mkdir()
        mock_drive = MagicMock()
        mock_drive.list_meeting_notes.return_value = [
            {"id": "doc1", "name": "Standup", "modifiedTime": "2026-03-17T10:00:00.000Z"},
        ]
        mock_drive.download_document.return_value = SAMPLE_DRIVE_DOC_CONTENT
        syncer = Syncer(meetings_dir=meetings_dir, drive_client=mock_drive)
        syncer.sync()
        syncer.sync()
        md_files = list(meetings_dir.glob("*.md"))
        assert len(md_files) == 1
        index_data = json.loads((meetings_dir / "index.json").read_text())
        assert len(index_data["meetings"]) == 1

    def test_sync_no_new_documents(self, tmp_path):
        meetings_dir = tmp_path / "meetings"
        meetings_dir.mkdir()
        mock_drive = MagicMock()
        mock_drive.list_meeting_notes.return_value = []
        syncer = Syncer(meetings_dir=meetings_dir, drive_client=mock_drive)
        syncer.sync()
        index_path = meetings_dir / "index.json"
        assert index_path.exists()
        index_data = json.loads(index_path.read_text())
        assert len(index_data["meetings"]) == 0
