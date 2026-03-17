"""Data models for MCP Meet Notes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ActionItem:
    """A single action item from a meeting."""
    assignee: str
    task: str


@dataclass
class Meeting:
    """Full meeting data, used internally and for Markdown generation."""
    id: str
    title: str
    date: datetime
    duration_minutes: int | None
    participants: list[str]
    source_doc_id: str
    synced_at: datetime
    tags: list[str]
    summary: str
    transcript: str
    action_items: list[ActionItem]
    parse_warnings: list[str] = field(default_factory=list)

    @property
    def has_action_items(self) -> bool:
        return len(self.action_items) > 0


@dataclass
class MeetingIndexEntry:
    """Lightweight meeting record for index.json."""
    id: str
    title: str
    date: datetime
    duration_minutes: int | None
    participants: list[str]
    file: str
    source_doc_id: str
    has_action_items: bool
    summary: str

    @classmethod
    def from_meeting(cls, meeting: Meeting, filename: str) -> MeetingIndexEntry:
        return cls(
            id=meeting.id, title=meeting.title, date=meeting.date,
            duration_minutes=meeting.duration_minutes,
            participants=meeting.participants, file=filename,
            source_doc_id=meeting.source_doc_id,
            has_action_items=meeting.has_action_items, summary=meeting.summary,
        )


@dataclass
class MeetingIndex:
    """The full index.json structure."""
    last_sync: datetime | None
    meetings: list[MeetingIndexEntry]

    def find_by_source_doc_id(self, doc_id: str) -> MeetingIndexEntry | None:
        for m in self.meetings:
            if m.source_doc_id == doc_id:
                return m
        return None


@dataclass
class ParsedDocument:
    """Result of parsing a Gemini meeting notes document."""
    title: str
    date: datetime | None
    duration_minutes: int | None
    participants: list[str]
    summary: str
    transcript: str
    action_items: list[ActionItem]
    parse_warnings: list[str] = field(default_factory=list)
