from datetime import datetime
from src.models import Meeting, MeetingIndexEntry, ActionItem, ParsedDocument, MeetingIndex


class TestMeeting:
    def test_create_meeting(self):
        m = Meeting(
            id="abc123",
            title="Standup Backend",
            date=datetime(2026, 3, 17, 10, 0),
            duration_minutes=25,
            participants=["pedro@test.com", "laura@test.com"],
            source_doc_id="doc123",
            synced_at=datetime(2026, 3, 17, 12, 0),
            tags=[],
            summary="Discussed migration progress.",
            transcript="Full transcript here...",
            action_items=[
                ActionItem(assignee="Pedro", task="Review PR"),
            ],
        )
        assert m.title == "Standup Backend"
        assert len(m.participants) == 2
        assert len(m.action_items) == 1

    def test_meeting_has_action_items(self):
        m = Meeting(
            id="abc", title="Test", date=datetime(2026, 1, 1),
            duration_minutes=None, participants=[], source_doc_id="doc1",
            synced_at=datetime(2026, 1, 1), tags=[], summary="", transcript="",
            action_items=[ActionItem(assignee="X", task="Do thing")],
        )
        assert m.has_action_items is True

    def test_meeting_no_action_items(self):
        m = Meeting(
            id="abc", title="Test", date=datetime(2026, 1, 1),
            duration_minutes=None, participants=[], source_doc_id="doc1",
            synced_at=datetime(2026, 1, 1), tags=[], summary="", transcript="",
            action_items=[],
        )
        assert m.has_action_items is False


class TestMeetingIndexEntry:
    def test_from_meeting(self):
        m = Meeting(
            id="abc", title="Standup", date=datetime(2026, 3, 17, 10, 0),
            duration_minutes=25, participants=["pedro@test.com"],
            source_doc_id="doc1", synced_at=datetime(2026, 3, 17, 12, 0),
            tags=[], summary="Discussed K8s.", transcript="...",
            action_items=[ActionItem(assignee="Pedro", task="Review")],
        )
        entry = MeetingIndexEntry.from_meeting(m, "2026-03-17-standup.md")
        assert entry.file == "2026-03-17-standup.md"
        assert entry.has_action_items is True
        assert entry.summary == "Discussed K8s."


class TestMeetingIndex:
    def test_create_empty(self):
        idx = MeetingIndex(last_sync=None, meetings=[])
        assert len(idx.meetings) == 0

    def test_add_entry(self):
        idx = MeetingIndex(last_sync=None, meetings=[])
        entry = MeetingIndexEntry(
            id="abc", title="Test", date=datetime(2026, 1, 1),
            duration_minutes=None, participants=[], file="test.md",
            source_doc_id="doc1", has_action_items=False, summary="Short summary.",
        )
        idx.meetings.append(entry)
        assert len(idx.meetings) == 1


class TestParsedDocument:
    def test_create(self):
        doc = ParsedDocument(
            title="Meeting Title", date=datetime(2026, 3, 17),
            duration_minutes=30, participants=["Pedro Mantese"],
            summary="We discussed things.", transcript="Speaker: Hello...",
            action_items=[ActionItem(assignee="Pedro", task="Do X")],
            parse_warnings=[],
        )
        assert doc.title == "Meeting Title"
        assert len(doc.parse_warnings) == 0
