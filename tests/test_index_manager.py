import json
from datetime import datetime
from pathlib import Path

import pytest

from src.index_manager import IndexManager
from src.models import MeetingIndex, MeetingIndexEntry


class TestIndexManager:
    def test_load_empty_index(self, tmp_meetings_dir: Path):
        manager = IndexManager(tmp_meetings_dir)
        index = manager.load()
        assert index.last_sync is None
        assert index.meetings == []

    def test_save_and_load(self, tmp_meetings_dir: Path, sample_index_entry: MeetingIndexEntry):
        manager = IndexManager(tmp_meetings_dir)
        index = MeetingIndex(last_sync=datetime(2026, 3, 17, 12, 0), meetings=[sample_index_entry])
        manager.save(index)
        loaded = manager.load()
        assert loaded.last_sync == datetime(2026, 3, 17, 12, 0)
        assert len(loaded.meetings) == 1
        assert loaded.meetings[0].title == "Standup Backend"

    def test_save_atomic_write(self, tmp_meetings_dir: Path, sample_index_entry: MeetingIndexEntry):
        manager = IndexManager(tmp_meetings_dir)
        index = MeetingIndex(last_sync=None, meetings=[sample_index_entry])
        manager.save(index)
        tmp_files = list(tmp_meetings_dir.glob("*.tmp"))
        assert len(tmp_files) == 0
        assert (tmp_meetings_dir / "index.json").exists()

    def test_add_or_update_entry_adds_new(self, tmp_meetings_dir: Path, sample_index_entry: MeetingIndexEntry):
        manager = IndexManager(tmp_meetings_dir)
        index = MeetingIndex(last_sync=None, meetings=[])
        manager.add_or_update_entry(index, sample_index_entry)
        assert len(index.meetings) == 1

    def test_add_or_update_entry_updates_existing(self, tmp_meetings_dir: Path, sample_index_entry: MeetingIndexEntry):
        manager = IndexManager(tmp_meetings_dir)
        index = MeetingIndex(last_sync=None, meetings=[sample_index_entry])
        updated = MeetingIndexEntry(
            id=sample_index_entry.id, title="Updated Standup",
            date=sample_index_entry.date, duration_minutes=30,
            participants=sample_index_entry.participants,
            file=sample_index_entry.file, source_doc_id=sample_index_entry.source_doc_id,
            has_action_items=False, summary="Updated summary.",
        )
        manager.add_or_update_entry(index, updated)
        assert len(index.meetings) == 1
        assert index.meetings[0].title == "Updated Standup"

    def test_regenerate_from_files(self, tmp_meetings_dir: Path, sample_markdown_content: str):
        md_file = tmp_meetings_dir / "2026-03-17-standup-backend.md"
        md_file.write_text(sample_markdown_content)
        manager = IndexManager(tmp_meetings_dir)
        index = manager.regenerate()
        assert len(index.meetings) == 1
        assert index.meetings[0].id == "abc123"
        assert index.meetings[0].has_action_items is True
        assert "K8s migration" in index.meetings[0].summary

    def test_load_corrupted_index_auto_regenerates(self, tmp_meetings_dir: Path, sample_markdown_content: str):
        md_file = tmp_meetings_dir / "2026-03-17-standup-backend.md"
        md_file.write_text(sample_markdown_content)
        (tmp_meetings_dir / "index.json").write_text("{invalid json!!!}")
        manager = IndexManager(tmp_meetings_dir)
        index = manager.load()
        assert len(index.meetings) == 1
        assert index.meetings[0].id == "abc123"
