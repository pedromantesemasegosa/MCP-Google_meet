from datetime import datetime
from pathlib import Path

import yaml

from src.markdown_writer import write_meeting_markdown, generate_filename
from src.models import ActionItem, Meeting


class TestGenerateFilename:
    def test_basic(self):
        m = Meeting(
            id="x", title="Standup Equipo Backend", date=datetime(2026, 3, 17),
            duration_minutes=25, participants=[], source_doc_id="d",
            synced_at=datetime(2026, 3, 17), tags=[], summary="", transcript="",
            action_items=[],
        )
        assert generate_filename(m) == "2026-03-17-standup-equipo-backend.md"

    def test_special_characters(self):
        m = Meeting(
            id="x", title="1:1 Pedro / Laura (Weekly)", date=datetime(2026, 3, 17),
            duration_minutes=None, participants=[], source_doc_id="d",
            synced_at=datetime(2026, 3, 17), tags=[], summary="", transcript="",
            action_items=[],
        )
        filename = generate_filename(m)
        assert filename.startswith("2026-03-17-")
        assert "/" not in filename
        assert ":" not in filename


class TestWriteMeetingMarkdown:
    def test_write_creates_file(self, tmp_meetings_dir: Path):
        m = Meeting(
            id="abc", title="Test Meeting", date=datetime(2026, 3, 17, 10, 0),
            duration_minutes=25, participants=["pedro@test.com"],
            source_doc_id="doc1", synced_at=datetime(2026, 3, 17, 12, 0),
            tags=[], summary="We discussed things.",
            transcript="Pedro: Hello.", action_items=[
                ActionItem(assignee="Pedro", task="Do thing"),
            ],
        )
        path = write_meeting_markdown(m, tmp_meetings_dir)
        assert path.exists()
        content = path.read_text()
        assert "title: \"Test Meeting\"" in content
        assert "## Resumen" in content
        assert "We discussed things." in content
        assert "## Transcripcion" in content
        assert "## Action Items" in content
        assert "- [ ] Pedro: Do thing" in content

    def test_write_atomic_no_tmp_left(self, tmp_meetings_dir: Path):
        m = Meeting(
            id="abc", title="Test", date=datetime(2026, 3, 17),
            duration_minutes=None, participants=[], source_doc_id="doc1",
            synced_at=datetime(2026, 3, 17), tags=[], summary="S",
            transcript="T", action_items=[],
        )
        write_meeting_markdown(m, tmp_meetings_dir)
        tmp_files = list(tmp_meetings_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_frontmatter_is_valid_yaml(self, tmp_meetings_dir: Path):
        m = Meeting(
            id="abc", title="Test", date=datetime(2026, 3, 17, 10, 0),
            duration_minutes=30, participants=["a@b.com", "c@d.com"],
            source_doc_id="doc1", synced_at=datetime(2026, 3, 17, 12, 0),
            tags=[], summary="Summary.", transcript="Text.", action_items=[],
        )
        path = write_meeting_markdown(m, tmp_meetings_dir)
        content = path.read_text()
        parts = content.split("---")
        fm = yaml.safe_load(parts[1])
        assert fm["id"] == "abc"
        assert fm["title"] == "Test"
        assert len(fm["participants"]) == 2
