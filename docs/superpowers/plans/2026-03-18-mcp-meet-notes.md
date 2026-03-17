# MCP Meet Notes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MCP Server that syncs Google Meet/Gemini notes from Drive to local Markdown and exposes 6 conversational search tools.

**Architecture:** Three independent components — Syncer (daily Google Drive → local Markdown), Storage (flat `meetings/` directory with `index.json` registry), and MCP Server (6 tools reading local files). Connected only through the filesystem.

**Tech Stack:** Python 3.11+, fastmcp, google-api-python-client, google-auth-oauthlib, macOS launchd

**Spec:** `docs/superpowers/specs/2026-03-17-mcp-meet-notes-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project metadata, dependencies, entry points |
| `.gitignore` | Exclude meetings/, config/credentials.json, config/token.json, logs/ |
| `config/settings.json` | User configuration (meetings dir, Drive folder name) |
| `src/__init__.py` | Package marker |
| `src/models.py` | Dataclasses: Meeting, MeetingIndex, ActionItem, ParsedDocument |
| `src/document_parser.py` | Parse Gemini plain text → ParsedDocument with heading extraction |
| `src/index_manager.py` | CRUD on index.json with atomic writes and regeneration |
| `src/search.py` | Search logic: by topic, participant, date, progression, action items, summary |
| `src/drive_client.py` | Google Drive API wrapper: auth, list files, download content |
| `src/syncer.py` | Orchestrate sync: Drive client → parser → index manager → filesystem |
| `src/server.py` | FastMCP server exposing 6 tools |
| `scripts/first_auth.py` | Interactive OAuth first-time login |
| `scripts/install_launchd.sh` | Install macOS launchd plist for daily sync |
| `tests/conftest.py` | Shared fixtures: sample meetings, temp directories, test index |
| `tests/test_models.py` | Model validation tests |
| `tests/test_document_parser.py` | Parser tests: standard format, missing sections, fallback |
| `tests/test_index_manager.py` | Index CRUD, regeneration, atomic writes |
| `tests/test_search.py` | All 6 search functions |
| `tests/test_syncer.py` | Syncer integration with mocked Drive API |
| `tests/test_server.py` | MCP tool integration tests |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `config/settings.json`
- Create: `src/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "mcp-meet-notes"
version = "0.1.0"
description = "MCP Server for searching Google Meet/Gemini meeting notes"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0.0",
    "google-api-python-client>=2.100.0",
    "google-auth-oauthlib>=1.2.0",
    "google-auth-httplib2>=0.2.0",
    "pyyaml>=6.0",
    "python-slugify>=8.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
mcp-meet-sync = "src.syncer:main"
mcp-meet-server = "src.server:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
venv/

# Project data (sensitive / generated)
meetings/
logs/
config/credentials.json
config/token.json

# IDE
.vscode/
.idea/
.cursor/

# OS
.DS_Store
```

- [ ] **Step 3: Create `config/settings.json`**

```json
{
  "meetings_dir": "meetings",
  "drive_folder_name": "Meeting notes",
  "sync_interval_description": "daily via launchd"
}
```

- [ ] **Step 4: Create `src/__init__.py`**

```python
"""MCP Meet Notes — Search Google Meet transcriptions via MCP."""
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -e ".[dev]"`
Expected: all dependencies installed successfully

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore config/settings.json src/__init__.py
git commit -m "chore: scaffold project with dependencies and config"
```

---

## Task 2: Data Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests for data models**

```python
# tests/test_models.py
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
            id="abc",
            title="Test",
            date=datetime(2026, 1, 1),
            duration_minutes=None,
            participants=[],
            source_doc_id="doc1",
            synced_at=datetime(2026, 1, 1),
            tags=[],
            summary="",
            transcript="",
            action_items=[ActionItem(assignee="X", task="Do thing")],
        )
        assert m.has_action_items is True

    def test_meeting_no_action_items(self):
        m = Meeting(
            id="abc",
            title="Test",
            date=datetime(2026, 1, 1),
            duration_minutes=None,
            participants=[],
            source_doc_id="doc1",
            synced_at=datetime(2026, 1, 1),
            tags=[],
            summary="",
            transcript="",
            action_items=[],
        )
        assert m.has_action_items is False


class TestMeetingIndexEntry:
    def test_from_meeting(self):
        m = Meeting(
            id="abc",
            title="Standup",
            date=datetime(2026, 3, 17, 10, 0),
            duration_minutes=25,
            participants=["pedro@test.com"],
            source_doc_id="doc1",
            synced_at=datetime(2026, 3, 17, 12, 0),
            tags=[],
            summary="Discussed K8s.",
            transcript="...",
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
            id="abc",
            title="Test",
            date=datetime(2026, 1, 1),
            duration_minutes=None,
            participants=[],
            file="test.md",
            source_doc_id="doc1",
            has_action_items=False,
            summary="Short summary.",
        )
        idx.meetings.append(entry)
        assert len(idx.meetings) == 1


class TestParsedDocument:
    def test_create(self):
        doc = ParsedDocument(
            title="Meeting Title",
            date=datetime(2026, 3, 17),
            duration_minutes=30,
            participants=["Pedro Mantese"],
            summary="We discussed things.",
            transcript="Speaker: Hello...",
            action_items=[ActionItem(assignee="Pedro", task="Do X")],
            parse_warnings=[],
        )
        assert doc.title == "Meeting Title"
        assert len(doc.parse_warnings) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.models'`

- [ ] **Step 3: Implement models**

```python
# src/models.py
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
            id=meeting.id,
            title=meeting.title,
            date=meeting.date,
            duration_minutes=meeting.duration_minutes,
            participants=meeting.participants,
            file=filename,
            source_doc_id=meeting.source_doc_id,
            has_action_items=meeting.has_action_items,
            summary=meeting.summary,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add data models for meetings, index entries, and parsed documents"
```

---

## Task 3: Document Parser

**Files:**
- Create: `src/document_parser.py`
- Create: `tests/test_document_parser.py`

- [ ] **Step 1: Write tests for parser**

```python
# tests/test_document_parser.py
from datetime import datetime
from src.document_parser import parse_gemini_document


SAMPLE_GEMINI_DOC = """Date: March 17, 2026
Duration: 25 minutes
Attendees: Pedro Mantese, Laura Garcia, Carlos Ruiz

Summary
We discussed the migration to Kubernetes. There is a blocker in CI/CD due to permissions. Laura will prepare the demo for Friday stakeholders.

Transcript
Pedro: Let's start with the migration update.
Laura: I've been blocked on CI/CD permissions since Monday.
Carlos: I can help with that after lunch.

Action items
- Pedro: Review migration PR
- Laura: Prepare Friday demo
- Carlos: Fix CI/CD permissions"""


class TestParseGeminiDocument:
    def test_parse_standard_format(self):
        result = parse_gemini_document(SAMPLE_GEMINI_DOC, doc_title="Standup Backend")
        assert result.title == "Standup Backend"
        assert result.date == datetime(2026, 3, 17)
        assert result.duration_minutes == 25
        assert result.participants == ["Pedro Mantese", "Laura Garcia", "Carlos Ruiz"]
        assert "migration to Kubernetes" in result.summary
        assert "Let's start" in result.transcript
        assert len(result.action_items) == 3
        assert result.action_items[0].assignee == "Pedro"
        assert result.action_items[0].task == "Review migration PR"
        assert len(result.parse_warnings) == 0

    def test_parse_missing_duration(self):
        doc = """Date: January 5, 2026
Attendees: Pedro Mantese

Summary
Short meeting about planning.

Transcript
Pedro: Quick sync."""
        result = parse_gemini_document(doc, doc_title="Quick Sync")
        assert result.duration_minutes is None
        assert result.title == "Quick Sync"
        assert len(result.parse_warnings) == 0

    def test_parse_missing_all_metadata(self):
        doc = """Just some unstructured text that doesn't match
any expected format at all."""
        result = parse_gemini_document(doc, doc_title="Unknown Meeting")
        assert result.title == "Unknown Meeting"
        assert result.date is None
        assert result.participants == []
        assert result.transcript == doc.strip()
        assert len(result.parse_warnings) > 0

    def test_parse_missing_action_items(self):
        doc = """Date: February 10, 2026
Attendees: Pedro Mantese

Summary
We discussed the roadmap.

Transcript
Pedro: Let's review the roadmap."""
        result = parse_gemini_document(doc, doc_title="Roadmap Review")
        assert len(result.action_items) == 0

    def test_parse_date_various_formats(self):
        doc1 = "Date: March 17, 2026\n\nSummary\nTest."
        r1 = parse_gemini_document(doc1, doc_title="T")
        assert r1.date == datetime(2026, 3, 17)

        doc2 = "Date: 2026-03-17\n\nSummary\nTest."
        r2 = parse_gemini_document(doc2, doc_title="T")
        assert r2.date == datetime(2026, 3, 17)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_document_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement parser**

```python
# src/document_parser.py
"""Parse Gemini meeting notes from plain text into structured data."""
from __future__ import annotations

import re
from datetime import datetime

from src.models import ActionItem, ParsedDocument


def parse_gemini_document(text: str, doc_title: str) -> ParsedDocument:
    """Parse a Gemini-generated meeting notes document.

    Extracts metadata using heading-based parsing. Falls back gracefully
    when the format doesn't match expectations.
    """
    warnings: list[str] = []
    lines = text.strip().split("\n")

    date = _extract_date(lines)
    duration = _extract_duration(lines)
    participants = _extract_participants(lines)
    sections = extract_sections(text)

    summary = sections.get("summary", "")
    transcript = sections.get("transcript", "")
    action_items = extract_action_items(sections.get("action items", ""))

    # Fallback: if no sections found, treat entire text as transcript
    if not summary and not transcript and not action_items:
        warnings.append("Could not parse document structure. Using full text as transcript.")
        transcript = text.strip()

    if date is None and _has_metadata_lines(lines):
        warnings.append("Date line found but could not be parsed.")

    return ParsedDocument(
        title=doc_title,
        date=date,
        duration_minutes=duration,
        participants=participants,
        summary=summary.strip(),
        transcript=transcript.strip(),
        action_items=action_items,
        parse_warnings=warnings,
    )


def _extract_date(lines: list[str]) -> datetime | None:
    """Extract date from 'Date: ...' line."""
    for line in lines:
        match = re.match(r"^Date:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return _parse_date_string(match.group(1).strip())
    return None


def _parse_date_string(date_str: str) -> datetime | None:
    """Try multiple date formats."""
    formats = [
        "%B %d, %Y",      # March 17, 2026
        "%b %d, %Y",      # Mar 17, 2026
        "%Y-%m-%d",        # 2026-03-17
        "%d/%m/%Y",        # 17/03/2026
        "%m/%d/%Y",        # 03/17/2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _extract_duration(lines: list[str]) -> int | None:
    """Extract duration from 'Duration: X minutes' line."""
    for line in lines:
        match = re.match(r"^Duration:\s*(\d+)\s*minutes?$", line, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_participants(lines: list[str]) -> list[str]:
    """Extract participants from 'Attendees: ...' line."""
    for line in lines:
        match = re.match(r"^Attendees:\s*(.+)$", line, re.IGNORECASE)
        if match:
            raw = match.group(1)
            return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def extract_sections(text: str) -> dict[str, str]:
    """Split text into sections by heading keywords.

    Recognizes both English (Gemini output) and Spanish (local files) headings.
    """
    heading_map = {
        "summary": "summary",
        "resumen": "summary",
        "transcript": "transcript",
        "transcripcion": "transcript",
        "transcripción": "transcript",
        "action items": "action items",
    }

    pattern = r"^(?:##?\s*)?(" + "|".join(re.escape(h) for h in heading_map) + r")\s*$"
    parts: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            if current_key is not None:
                parts[current_key] = "\n".join(current_lines)
            heading = match.group(1).strip().lower()
            current_key = heading_map.get(heading, heading)
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        parts[current_key] = "\n".join(current_lines)

    return parts


def extract_action_items(text: str) -> list[ActionItem]:
    """Extract action items from the Action Items section."""
    items: list[ActionItem] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        # Match patterns like "- Pedro: Review PR" or "- [ ] Pedro: Review PR"
        match = re.match(r"^[-*]\s*(?:\[.\]\s*)?(\w[\w\s]*?):\s*(.+)$", line)
        if match:
            items.append(ActionItem(
                assignee=match.group(1).strip(),
                task=match.group(2).strip(),
            ))
    return items


def _has_metadata_lines(lines: list[str]) -> bool:
    """Check if any Date: line exists."""
    return any(re.match(r"^Date:", line, re.IGNORECASE) for line in lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_document_parser.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/document_parser.py tests/test_document_parser.py
git commit -m "feat: add Gemini document parser with heading extraction and fallback"
```

---

## Task 4: Index Manager

**Files:**
- Create: `src/index_manager.py`
- Create: `tests/test_index_manager.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write shared test fixtures**

```python
# tests/conftest.py
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from src.models import ActionItem, Meeting, MeetingIndex, MeetingIndexEntry


@pytest.fixture
def tmp_meetings_dir(tmp_path: Path) -> Path:
    """Create a temporary meetings directory."""
    meetings = tmp_path / "meetings"
    meetings.mkdir()
    return meetings


@pytest.fixture
def sample_meeting() -> Meeting:
    return Meeting(
        id="abc123",
        title="Standup Backend",
        date=datetime(2026, 3, 17, 10, 0),
        duration_minutes=25,
        participants=["pedro@test.com", "laura@test.com"],
        source_doc_id="doc123",
        synced_at=datetime(2026, 3, 17, 12, 0),
        tags=[],
        summary="Discussed K8s migration and CI/CD blocker.",
        transcript="Pedro: Let's talk about K8s.\nLaura: Blocked on CI.",
        action_items=[
            ActionItem(assignee="Pedro", task="Review PR"),
            ActionItem(assignee="Laura", task="Prepare demo"),
        ],
    )


@pytest.fixture
def sample_index_entry() -> MeetingIndexEntry:
    return MeetingIndexEntry(
        id="abc123",
        title="Standup Backend",
        date=datetime(2026, 3, 17, 10, 0),
        duration_minutes=25,
        participants=["pedro@test.com", "laura@test.com"],
        file="2026-03-17-standup-backend.md",
        source_doc_id="doc123",
        has_action_items=True,
        summary="Discussed K8s migration and CI/CD blocker.",
    )


@pytest.fixture
def sample_markdown_content() -> str:
    return """---
id: "abc123"
title: "Standup Backend"
date: "2026-03-17T10:00:00"
duration_minutes: 25
participants:
  - "pedro@test.com"
  - "laura@test.com"
source_doc_id: "doc123"
synced_at: "2026-03-17T12:00:00"
tags: []
---

## Resumen

Discussed K8s migration and CI/CD blocker.

## Transcripcion

Pedro: Let's talk about K8s.
Laura: Blocked on CI.

## Action Items

- [ ] Pedro: Review PR
- [ ] Laura: Prepare demo
"""
```

- [ ] **Step 2: Write tests for index manager**

```python
# tests/test_index_manager.py
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
        index = MeetingIndex(
            last_sync=datetime(2026, 3, 17, 12, 0),
            meetings=[sample_index_entry],
        )
        manager.save(index)
        loaded = manager.load()
        assert loaded.last_sync == datetime(2026, 3, 17, 12, 0)
        assert len(loaded.meetings) == 1
        assert loaded.meetings[0].title == "Standup Backend"

    def test_save_atomic_write(self, tmp_meetings_dir: Path, sample_index_entry: MeetingIndexEntry):
        """Verify no .tmp files are left after save."""
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
            id=sample_index_entry.id,
            title="Updated Standup",
            date=sample_index_entry.date,
            duration_minutes=30,
            participants=sample_index_entry.participants,
            file=sample_index_entry.file,
            source_doc_id=sample_index_entry.source_doc_id,
            has_action_items=False,
            summary="Updated summary.",
        )
        manager.add_or_update_entry(index, updated)
        assert len(index.meetings) == 1
        assert index.meetings[0].title == "Updated Standup"

    def test_regenerate_from_files(self, tmp_meetings_dir: Path, sample_markdown_content: str):
        # Write a sample .md file
        md_file = tmp_meetings_dir / "2026-03-17-standup-backend.md"
        md_file.write_text(sample_markdown_content)

        manager = IndexManager(tmp_meetings_dir)
        index = manager.regenerate()
        assert len(index.meetings) == 1
        assert index.meetings[0].id == "abc123"
        assert index.meetings[0].has_action_items is True
        assert "K8s migration" in index.meetings[0].summary

    def test_load_corrupted_index_auto_regenerates(self, tmp_meetings_dir: Path, sample_markdown_content: str):
        """AC #3: corrupted index.json triggers auto-regeneration."""
        md_file = tmp_meetings_dir / "2026-03-17-standup-backend.md"
        md_file.write_text(sample_markdown_content)

        # Write corrupted index.json
        (tmp_meetings_dir / "index.json").write_text("{invalid json!!!}")

        manager = IndexManager(tmp_meetings_dir)
        index = manager.load()  # should auto-regenerate, not crash
        assert len(index.meetings) == 1
        assert index.meetings[0].id == "abc123"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_index_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement index manager**

```python
# src/index_manager.py
"""Manage the meetings index.json with atomic writes."""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

from src.models import ActionItem, MeetingIndex, MeetingIndexEntry


class IndexManager:
    """CRUD operations on the meetings index.json."""

    def __init__(self, meetings_dir: Path) -> None:
        self._meetings_dir = meetings_dir
        self._index_path = meetings_dir / "index.json"

    def load(self) -> MeetingIndex:
        """Load index from disk. Returns empty index if file doesn't exist.
        Auto-regenerates if index.json is corrupted."""
        if not self._index_path.exists():
            return MeetingIndex(last_sync=None, meetings=[])

        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            logger.warning("index.json is corrupted. Regenerating from .md files.")
            return self.regenerate()

        meetings = [
            MeetingIndexEntry(
                id=m["id"],
                title=m["title"],
                date=datetime.fromisoformat(m["date"]),
                duration_minutes=m.get("duration_minutes"),
                participants=m.get("participants", []),
                file=m["file"],
                source_doc_id=m["source_doc_id"],
                has_action_items=m.get("has_action_items", False),
                summary=m.get("summary", ""),
            )
            for m in data.get("meetings", [])
        ]

        last_sync_str = data.get("last_sync")
        last_sync = datetime.fromisoformat(last_sync_str) if last_sync_str else None

        return MeetingIndex(last_sync=last_sync, meetings=meetings)

    def save(self, index: MeetingIndex) -> None:
        """Save index to disk atomically (write tmp, then rename)."""
        data = {
            "last_sync": index.last_sync.isoformat() if index.last_sync else None,
            "meetings": [
                {
                    "id": m.id,
                    "title": m.title,
                    "date": m.date.isoformat(),
                    "duration_minutes": m.duration_minutes,
                    "participants": m.participants,
                    "file": m.file,
                    "source_doc_id": m.source_doc_id,
                    "has_action_items": m.has_action_items,
                    "summary": m.summary,
                }
                for m in index.meetings
            ],
        }

        fd, tmp_path = tempfile.mkstemp(
            dir=self._meetings_dir, suffix=".tmp", prefix="index_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._index_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def add_or_update_entry(
        self, index: MeetingIndex, entry: MeetingIndexEntry
    ) -> None:
        """Add a new entry or update existing one (matched by source_doc_id)."""
        for i, m in enumerate(index.meetings):
            if m.source_doc_id == entry.source_doc_id:
                index.meetings[i] = entry
                return
        index.meetings.append(entry)

    def regenerate(self) -> MeetingIndex:
        """Regenerate index by scanning all .md files in meetings dir.

        Reads YAML frontmatter for metadata and parses Markdown body
        to reconstruct has_action_items and summary.
        """
        entries: list[MeetingIndexEntry] = []

        for md_file in sorted(self._meetings_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            frontmatter, body = split_frontmatter(content)
            if frontmatter is None:
                continue

            meta = yaml.safe_load(frontmatter)
            if not isinstance(meta, dict):
                continue

            # Reconstruct from body
            has_actions = _body_has_action_items(body)
            summary = _extract_summary_from_body(body)

            date_val = meta.get("date")
            if isinstance(date_val, str):
                date_val = datetime.fromisoformat(date_val)

            entries.append(
                MeetingIndexEntry(
                    id=meta.get("id", md_file.stem),
                    title=meta.get("title", md_file.stem),
                    date=date_val,
                    duration_minutes=meta.get("duration_minutes"),
                    participants=meta.get("participants", []),
                    file=md_file.name,
                    source_doc_id=meta.get("source_doc_id", ""),
                    has_action_items=has_actions,
                    summary=summary,
                )
            )

        index = MeetingIndex(last_sync=None, meetings=entries)
        self.save(index)
        return index


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split YAML frontmatter from Markdown body."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, content


def _body_has_action_items(body: str) -> bool:
    """Check if body contains an Action Items section with checklist items."""
    in_section = False
    for line in body.split("\n"):
        stripped = line.strip().lower()
        if stripped in ("## action items", "action items"):
            in_section = True
            continue
        if in_section and re.match(r"^[-*]\s", line.strip()):
            return True
        if in_section and stripped.startswith("## "):
            break
    return False


def _extract_summary_from_body(body: str) -> str:
    """Extract first 1-2 sentences from the Resumen/Summary section."""
    in_section = False
    summary_lines: list[str] = []
    for line in body.split("\n"):
        stripped = line.strip().lower()
        if stripped in ("## resumen", "## summary", "resumen", "summary"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## ") or stripped.startswith("# "):
                break
            if line.strip():
                summary_lines.append(line.strip())

    full = " ".join(summary_lines)
    # Take first ~2 sentences
    sentences = re.split(r"(?<=[.!?])\s+", full)
    return " ".join(sentences[:2]).strip()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_index_manager.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/index_manager.py tests/test_index_manager.py tests/conftest.py
git commit -m "feat: add index manager with atomic writes and regeneration"
```

---

## Task 5: Markdown Writer

This is a utility function in the syncer that converts a `Meeting` to a Markdown file. We test it early because the search module will read these files.

**Files:**
- Create: `src/markdown_writer.py`
- Create: `tests/test_markdown_writer.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_markdown_writer.py
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
        # Extract frontmatter
        parts = content.split("---")
        fm = yaml.safe_load(parts[1])
        assert fm["id"] == "abc"
        assert fm["title"] == "Test"
        assert len(fm["participants"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_markdown_writer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement markdown writer**

```python
# src/markdown_writer.py
"""Write Meeting objects to Markdown files with YAML frontmatter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from slugify import slugify

from src.models import Meeting


def generate_filename(meeting: Meeting) -> str:
    """Generate a filename like '2026-03-17-standup-equipo-backend.md'."""
    date_str = meeting.date.strftime("%Y-%m-%d")
    slug = slugify(meeting.title, max_length=60)
    return f"{date_str}-{slug}.md"


def write_meeting_markdown(meeting: Meeting, meetings_dir: Path) -> Path:
    """Write a meeting to a Markdown file atomically.

    Writes to a temp file first, then renames to prevent partial reads.
    Returns the path to the written file.
    """
    filename = generate_filename(meeting)
    target_path = meetings_dir / filename
    content = _render_markdown(meeting)

    fd, tmp_path = tempfile.mkstemp(
        dir=meetings_dir, suffix=".tmp", prefix="meeting_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return target_path


def _render_markdown(meeting: Meeting) -> str:
    """Render a Meeting as Markdown with YAML frontmatter."""
    participants_yaml = "\n".join(f'  - "{p}"' for p in meeting.participants)
    tags_yaml = "[]" if not meeting.tags else "\n".join(f"  - \"{t}\"" for t in meeting.tags)
    warnings_yaml = ""
    if meeting.parse_warnings:
        warnings_list = "\n".join(f"  - \"{w}\"" for w in meeting.parse_warnings)
        warnings_yaml = f"parse_warnings:\n{warnings_list}\n"

    frontmatter = f"""---
id: "{meeting.id}"
title: "{meeting.title}"
date: "{meeting.date.isoformat()}"
duration_minutes: {meeting.duration_minutes if meeting.duration_minutes is not None else "null"}
participants:
{participants_yaml}
source_doc_id: "{meeting.source_doc_id}"
synced_at: "{meeting.synced_at.isoformat()}"
tags: {tags_yaml}
{warnings_yaml}---"""

    action_items_section = ""
    if meeting.action_items:
        items = "\n".join(
            f"- [ ] {ai.assignee}: {ai.task}" for ai in meeting.action_items
        )
        action_items_section = f"\n## Action Items\n\n{items}\n"

    return f"""{frontmatter}

## Resumen

{meeting.summary}

## Transcripcion

{meeting.transcript}
{action_items_section}"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_markdown_writer.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/markdown_writer.py tests/test_markdown_writer.py
git commit -m "feat: add markdown writer with atomic file writes and slug filenames"
```

---

## Task 6: Search Module

**Files:**
- Create: `src/search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_search.py
from datetime import datetime
from pathlib import Path

import pytest

from src.models import MeetingIndex, MeetingIndexEntry
from src.search import (
    search_by_topic,
    search_by_participant,
    search_by_date,
    get_topic_progression,
    get_action_items,
    get_executive_summary,
)


def _make_entry(
    id: str, title: str, date: datetime, participants: list[str],
    summary: str, file: str, has_action_items: bool = False,
) -> MeetingIndexEntry:
    return MeetingIndexEntry(
        id=id, title=title, date=date, duration_minutes=30,
        participants=participants, file=file, source_doc_id=f"doc_{id}",
        has_action_items=has_action_items, summary=summary,
    )


@pytest.fixture
def test_index() -> MeetingIndex:
    return MeetingIndex(
        last_sync=datetime(2026, 3, 17),
        meetings=[
            _make_entry("1", "Standup Backend", datetime(2026, 3, 15),
                        ["pedro@test.com", "laura@test.com"],
                        "Discussed K8s migration progress.", "2026-03-15-standup-backend.md",
                        has_action_items=True),
            _make_entry("2", "Planning Sprint 42", datetime(2026, 3, 16),
                        ["pedro@test.com", "carlos@test.com"],
                        "Sprint planning for Q2 features.", "2026-03-16-planning-sprint-42.md"),
            _make_entry("3", "1:1 Pedro Laura", datetime(2026, 3, 17),
                        ["pedro@test.com", "laura@test.com"],
                        "Career growth and K8s migration blockers.", "2026-03-17-1on1-pedro-laura.md",
                        has_action_items=True),
            _make_entry("4", "Design Review", datetime(2026, 3, 10),
                        ["carlos@test.com", "maria@test.com"],
                        "Reviewed new onboarding flow.", "2026-03-10-design-review.md"),
        ],
    )


@pytest.fixture
def test_meetings_dir(tmp_path: Path, test_index: MeetingIndex) -> Path:
    """Create a meetings dir with .md files matching the index."""
    meetings = tmp_path / "meetings"
    meetings.mkdir()

    contents = {
        "2026-03-15-standup-backend.md": """---
id: "1"
title: "Standup Backend"
---

## Resumen

Discussed K8s migration progress. CI/CD pipeline needs fixing.

## Action Items

- [ ] Pedro: Review migration PR
""",
        "2026-03-16-planning-sprint-42.md": """---
id: "2"
title: "Planning Sprint 42"
---

## Resumen

Sprint planning for Q2 features. Focus on user onboarding redesign.
""",
        "2026-03-17-1on1-pedro-laura.md": """---
id: "3"
title: "1:1 Pedro Laura"
---

## Resumen

Career growth and K8s migration blockers. Laura wants to lead the next project.

## Action Items

- [ ] Laura: Prepare tech talk proposal
- [ ] Pedro: Schedule follow-up with manager
""",
        "2026-03-10-design-review.md": """---
id: "4"
title: "Design Review"
---

## Resumen

Reviewed new onboarding flow. Need more user testing data.
""",
    }

    for name, content in contents.items():
        (meetings / name).write_text(content)

    return meetings


class TestSearchByTopic:
    def test_match_in_title(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_topic(test_index, test_meetings_dir, "standup")
        assert any(r["title"] == "Standup Backend" for r in results)

    def test_match_in_summary(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_topic(test_index, test_meetings_dir, "K8s")
        assert len(results) >= 2  # standup + 1:1

    def test_no_results(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_topic(test_index, test_meetings_dir, "nonexistent_xyz")
        assert len(results) == 0

    def test_fulltext_fallback(self, test_index: MeetingIndex, test_meetings_dir: Path):
        # "CI/CD" only appears in file body, not in index summary
        results = search_by_topic(test_index, test_meetings_dir, "CI/CD", limit=5)
        assert any(r["id"] == "1" for r in results)


class TestSearchByParticipant:
    def test_exact_match(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_participant(test_index, "pedro@test.com")
        assert len(results) == 3

    def test_partial_match(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_participant(test_index, "laura")
        assert len(results) == 2

    def test_with_date_range(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_participant(
            test_index, "pedro", date_from=datetime(2026, 3, 16)
        )
        assert len(results) == 2  # planning + 1:1


class TestSearchByDate:
    def test_single_day(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_date(test_index, date_from=datetime(2026, 3, 17))
        assert len(results) == 1
        assert results[0]["title"] == "1:1 Pedro Laura"

    def test_date_range(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = search_by_date(
            test_index,
            date_from=datetime(2026, 3, 15),
            date_to=datetime(2026, 3, 17),
        )
        assert len(results) == 3


class TestGetTopicProgression:
    def test_progression_order(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_topic_progression(test_index, test_meetings_dir, "K8s")
        assert len(results) >= 2
        dates = [r["date"] for r in results]
        assert dates == sorted(dates)

    def test_includes_excerpts(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_topic_progression(test_index, test_meetings_dir, "K8s")
        for r in results:
            assert "excerpt" in r


class TestGetActionItems:
    def test_all_action_items(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_action_items(test_index, test_meetings_dir)
        assert len(results) >= 3

    def test_filter_by_participant(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_action_items(test_index, test_meetings_dir, participant="Pedro")
        assert all(r["assignee"] == "Pedro" for r in results)

    def test_filter_by_date(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_action_items(
            test_index, test_meetings_dir, date_from=datetime(2026, 3, 17)
        )
        assert all(r["meeting_date"] >= "2026-03-17" for r in results)


class TestGetExecutiveSummary:
    def test_summary_range(self, test_index: MeetingIndex, test_meetings_dir: Path):
        results = get_executive_summary(
            test_index, test_meetings_dir,
            date_from=datetime(2026, 3, 15), date_to=datetime(2026, 3, 17),
        )
        assert len(results) == 3
        for r in results:
            assert "title" in r
            assert "summary" in r
            assert "action_items" in r
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_search.py -v`
Expected: FAIL

- [ ] **Step 3: Implement search module**

```python
# src/search.py
"""Search logic for meetings — used by MCP server tools."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.document_parser import extract_action_items, extract_sections
from src.index_manager import split_frontmatter
from src.models import MeetingIndex, MeetingIndexEntry


def search_by_topic(
    index: MeetingIndex,
    meetings_dir: Path,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Two-phase search: index first, full-text fallback if under limit."""
    query_lower = query.lower()
    results: list[dict] = []
    seen_ids: set[str] = set()

    # Phase 1: search titles and summaries in index
    for entry in index.meetings:
        score = _score_index_match(entry, query_lower)
        if score > 0:
            results.append(_entry_to_result(entry, score))
            seen_ids.add(entry.id)

    # Phase 2: full-text fallback if under limit
    if len(results) < limit:
        for entry in index.meetings:
            if entry.id in seen_ids:
                continue
            file_path = meetings_dir / entry.file
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8").lower()
            if query_lower in content:
                results.append(_entry_to_result(entry, score=1))
                seen_ids.add(entry.id)

    results.sort(key=lambda r: r["_score"], reverse=True)
    for r in results:
        del r["_score"]
    return results[:limit]


def search_by_participant(
    index: MeetingIndex,
    participant: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Filter meetings by participant with partial matching."""
    participant_lower = participant.lower()
    results: list[dict] = []

    for entry in index.meetings:
        if not any(participant_lower in p.lower() for p in entry.participants):
            continue
        if date_from and entry.date < date_from:
            continue
        if date_to and entry.date > date_to:
            continue
        results.append(_entry_to_result(entry))

    results.sort(key=lambda r: r["date"])
    return results


def search_by_date(
    index: MeetingIndex,
    date_from: datetime,
    date_to: datetime | None = None,
) -> list[dict]:
    """Return meetings in a date range. Single day if no date_to."""
    if date_to is None:
        date_to = date_from.replace(hour=23, minute=59, second=59)

    results: list[dict] = []
    for entry in index.meetings:
        if date_from <= entry.date <= date_to:
            results.append(_entry_to_result(entry))

    results.sort(key=lambda r: r["date"])
    return results


def get_topic_progression(
    index: MeetingIndex,
    meetings_dir: Path,
    topic: str,
) -> list[dict]:
    """Find meetings mentioning a topic, ordered chronologically with excerpts."""
    topic_lower = topic.lower()
    results: list[dict] = []

    for entry in index.meetings:
        # Check index fields
        in_index = topic_lower in entry.title.lower() or topic_lower in entry.summary.lower()

        # Check file content
        file_path = meetings_dir / entry.file
        content = ""
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")

        in_content = topic_lower in content.lower()

        if in_index or in_content:
            excerpt = _extract_excerpt(content, topic_lower)
            results.append({
                "id": entry.id,
                "title": entry.title,
                "date": entry.date.isoformat(),
                "summary": entry.summary,
                "excerpt": excerpt,
                "participants": entry.participants,
            })

    results.sort(key=lambda r: r["date"])
    return results


def get_action_items(
    index: MeetingIndex,
    meetings_dir: Path,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    participant: str | None = None,
) -> list[dict]:
    """Extract action items from meetings, with optional filters."""
    results: list[dict] = []

    for entry in index.meetings:
        if not entry.has_action_items:
            continue
        if date_from and entry.date < date_from:
            continue
        if date_to and entry.date > date_to:
            continue

        file_path = meetings_dir / entry.file
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8")
        _, body = split_frontmatter(content)
        sections = extract_sections(body)
        items = extract_action_items(sections.get("action items", ""))

        for item in items:
            if participant and participant.lower() not in item.assignee.lower():
                continue
            results.append({
                "assignee": item.assignee,
                "task": item.task,
                "meeting_title": entry.title,
                "meeting_date": entry.date.isoformat(),
                "meeting_id": entry.id,
            })

    return results


def get_executive_summary(
    index: MeetingIndex,
    meetings_dir: Path,
    date_from: datetime,
    date_to: datetime | None = None,
) -> list[dict]:
    """Return titles, summaries, and action items for a date range."""
    if date_to is None:
        date_to = date_from.replace(hour=23, minute=59, second=59)

    results: list[dict] = []

    for entry in index.meetings:
        if not (date_from <= entry.date <= date_to):
            continue

        action_items: list[dict] = []
        if entry.has_action_items:
            file_path = meetings_dir / entry.file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                _, body = split_frontmatter(content)
                sections = extract_sections(body)
                items = extract_action_items(sections.get("action items", ""))
                action_items = [{"assignee": i.assignee, "task": i.task} for i in items]

        results.append({
            "id": entry.id,
            "title": entry.title,
            "date": entry.date.isoformat(),
            "summary": entry.summary,
            "participants": entry.participants,
            "action_items": action_items,
        })

    results.sort(key=lambda r: r["date"])
    return results


def _score_index_match(entry: MeetingIndexEntry, query_lower: str) -> int:
    """Score an index entry match. Higher = more relevant."""
    score = 0
    if query_lower in entry.title.lower():
        score += 3
    if query_lower in entry.summary.lower():
        score += 2
    return score


def _entry_to_result(entry: MeetingIndexEntry, score: int = 0) -> dict:
    return {
        "id": entry.id,
        "title": entry.title,
        "date": entry.date.isoformat(),
        "summary": entry.summary,
        "participants": entry.participants,
        "has_action_items": entry.has_action_items,
        "_score": score,
    }


def _extract_excerpt(content: str, query_lower: str, context_chars: int = 200) -> str:
    """Extract a text excerpt around the first occurrence of the query."""
    idx = content.lower().find(query_lower)
    if idx == -1:
        return ""

    start = max(0, idx - context_chars)
    end = min(len(content), idx + len(query_lower) + context_chars)
    excerpt = content[start:end].strip()

    if start > 0:
        excerpt = "..." + excerpt
    if end < len(content):
        excerpt = excerpt + "..."

    return excerpt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_search.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/search.py tests/test_search.py
git commit -m "feat: add search module with 6 query functions"
```

---

## Task 7: Google Drive Client

**Files:**
- Create: `src/drive_client.py`
- Create: `tests/test_drive_client.py`

- [ ] **Step 1: Write tests (mocked Google API)**

```python
# tests/test_drive_client.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_drive_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Drive client**

```python
# src/drive_client.py
"""Google Drive API client for fetching Gemini meeting notes."""
from __future__ import annotations

import json
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
    """Wrapper around Google Drive API for fetching meeting notes."""

    def __init__(self, config_dir: Path, folder_name: str) -> None:
        self._config_dir = config_dir
        self._folder_name = folder_name
        self._credentials_path = config_dir / "credentials.json"
        self._token_path = config_dir / "token.json"
        self._service = self._authenticate()
        self._folder_id = self._find_folder_id()

    def _authenticate(self):
        """Authenticate with Google Drive API using OAuth2."""
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
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        self._token_path.write_text(creds.to_json())

        return build("drive", "v3", credentials=creds)

    def _find_folder_id(self) -> str | None:
        """Find the Google Drive folder ID for meeting notes."""
        query = (
            f"name = '{self._folder_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
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
        """List Gemini meeting note documents modified since a given date."""
        if self._folder_id is None:
            return []

        query = (
            f"'{self._folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.document' and "
            "trashed = false"
        )

        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
            query += f" and modifiedTime > '{since_str}'"

        response = self._service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, modifiedTime, createdTime)",
            orderBy="modifiedTime desc",
        ).execute()

        return response.get("files", [])

    def download_document(self, doc_id: str) -> str:
        """Download a Google Doc as plain text."""
        content = self._service.files().export(
            fileId=doc_id, mimeType="text/plain"
        ).execute()

        if isinstance(content, bytes):
            return content.decode("utf-8")
        return str(content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_drive_client.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/drive_client.py tests/test_drive_client.py
git commit -m "feat: add Google Drive API client with OAuth2 and document download"
```

---

## Task 8: Syncer

**Files:**
- Create: `src/syncer.py`
- Create: `tests/test_syncer.py`

- [ ] **Step 1: Write tests (mocked Drive client)**

```python
# tests/test_syncer.py
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.syncer import Syncer, main


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
    def test_sync_new_document(self, tmp_path: Path):
        meetings_dir = tmp_path / "meetings"
        meetings_dir.mkdir()
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mock_drive = MagicMock()
        mock_drive.list_meeting_notes.return_value = [
            {"id": "doc1", "name": "Standup Backend", "modifiedTime": "2026-03-17T10:00:00.000Z"},
        ]
        mock_drive.download_document.return_value = SAMPLE_DRIVE_DOC_CONTENT

        syncer = Syncer(meetings_dir=meetings_dir, drive_client=mock_drive)
        syncer.sync()

        # Verify .md file was created
        md_files = list(meetings_dir.glob("*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "Standup Backend" in content

        # Verify index.json was updated
        index_path = meetings_dir / "index.json"
        assert index_path.exists()
        index_data = json.loads(index_path.read_text())
        assert len(index_data["meetings"]) == 1
        assert index_data["meetings"][0]["source_doc_id"] == "doc1"

    def test_sync_idempotent(self, tmp_path: Path):
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

    def test_sync_no_new_documents(self, tmp_path: Path):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_syncer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement syncer**

```python
# src/syncer.py
"""Sync Google Drive Gemini meeting notes to local Markdown files."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from src.document_parser import parse_gemini_document
from src.drive_client import DriveClient
from src.index_manager import IndexManager
from src.markdown_writer import generate_filename, write_meeting_markdown
from src.models import Meeting, MeetingIndexEntry

logger = logging.getLogger(__name__)


class Syncer:
    """Orchestrate sync from Google Drive to local meetings directory."""

    def __init__(self, meetings_dir: Path, drive_client: DriveClient) -> None:
        self._meetings_dir = meetings_dir
        self._drive = drive_client
        self._index_manager = IndexManager(meetings_dir)

    def sync(self) -> None:
        """Run one sync cycle."""
        index = self._index_manager.load()
        logger.info("Sync started. Last sync: %s", index.last_sync)

        try:
            docs = self._drive.list_meeting_notes(since=index.last_sync)
        except Exception as e:
            logger.error("Failed to list meeting notes: %s", e)
            return

        logger.info("Found %d documents to process.", len(docs))

        for doc in docs:
            try:
                self._process_document(doc, index)
            except Exception as e:
                logger.error("Failed to process document %s: %s", doc.get("id"), e)
                continue

        index.last_sync = datetime.now(tz=timezone.utc)
        self._index_manager.save(index)
        logger.info("Sync completed. Processed %d documents.", len(docs))

    def _process_document(self, doc: dict, index) -> None:
        """Download, parse, and store a single document."""
        doc_id = doc["id"]
        doc_title = doc["name"]

        logger.info("Processing: %s (%s)", doc_title, doc_id)

        content = self._drive.download_document(doc_id)
        parsed = parse_gemini_document(content, doc_title=doc_title)

        meeting = Meeting(
            id=str(uuid.uuid4())[:8],
            title=parsed.title,
            date=parsed.date or datetime.now(tz=timezone.utc),
            duration_minutes=parsed.duration_minutes,
            participants=parsed.participants,
            source_doc_id=doc_id,
            synced_at=datetime.now(tz=timezone.utc),
            tags=[],
            summary=parsed.summary,
            transcript=parsed.transcript,
            action_items=parsed.action_items,
            parse_warnings=parsed.parse_warnings,
        )

        # Check if already synced (idempotency)
        existing = index.find_by_source_doc_id(doc_id)
        if existing:
            meeting.id = existing.id  # preserve ID

        path = write_meeting_markdown(meeting, self._meetings_dir)
        filename = path.name

        entry = MeetingIndexEntry.from_meeting(meeting, filename)
        self._index_manager.add_or_update_entry(index, entry)


def _setup_logging(logs_dir: Path) -> None:
    """Configure logging with daily rotation."""
    logs_dir.mkdir(exist_ok=True)
    handler = TimedRotatingFileHandler(
        logs_dir / "sync.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    """Entry point for the sync command."""
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    meetings_dir = project_root / "meetings"
    logs_dir = project_root / "logs"

    _setup_logging(logs_dir)
    meetings_dir.mkdir(exist_ok=True)

    settings_path = config_dir / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    folder_name = settings.get("drive_folder_name", "Meeting notes")

    try:
        drive = DriveClient(config_dir=config_dir, folder_name=folder_name)
    except Exception as e:
        logger.error("Failed to initialize Drive client: %s", e)
        return

    syncer = Syncer(meetings_dir=meetings_dir, drive_client=drive)
    syncer.sync()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_syncer.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/syncer.py tests/test_syncer.py
git commit -m "feat: add syncer orchestrating Drive → parser → index → filesystem"
```

---

## Task 9: MCP Server

**Files:**
- Create: `src/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_server.py
import json
from datetime import datetime
from pathlib import Path

import pytest

from src.server import create_server


@pytest.fixture
def server_with_data(tmp_path: Path):
    """Create a server with test meeting data."""
    meetings_dir = tmp_path / "meetings"
    meetings_dir.mkdir()

    index_data = {
        "last_sync": "2026-03-17T12:00:00",
        "meetings": [
            {
                "id": "1",
                "title": "Standup Backend",
                "date": "2026-03-17T10:00:00",
                "duration_minutes": 25,
                "participants": ["pedro@test.com", "laura@test.com"],
                "file": "2026-03-17-standup-backend.md",
                "source_doc_id": "doc1",
                "has_action_items": True,
                "summary": "Discussed K8s migration and CI/CD blockers.",
            },
            {
                "id": "2",
                "title": "Planning Sprint",
                "date": "2026-03-16T09:00:00",
                "duration_minutes": 60,
                "participants": ["pedro@test.com", "carlos@test.com"],
                "file": "2026-03-16-planning-sprint.md",
                "source_doc_id": "doc2",
                "has_action_items": False,
                "summary": "Sprint planning for Q2.",
            },
        ],
    }
    (meetings_dir / "index.json").write_text(json.dumps(index_data))

    (meetings_dir / "2026-03-17-standup-backend.md").write_text("""---
id: "1"
title: "Standup Backend"
---

## Resumen

Discussed K8s migration and CI/CD blockers. Pipeline needs fixing.

## Action Items

- [ ] Pedro: Review migration PR
- [ ] Laura: Fix CI/CD permissions
""")

    (meetings_dir / "2026-03-16-planning-sprint.md").write_text("""---
id: "2"
title: "Planning Sprint"
---

## Resumen

Sprint planning for Q2. Focus on onboarding redesign and API refactor.
""")

    server = create_server(meetings_dir)
    return server, meetings_dir


class TestMCPServer:
    """Test MCP tools by calling the underlying search functions directly.
    This avoids depending on FastMCP internal APIs."""

    def test_search_by_topic(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import search_by_topic
        index = IndexManager(meetings_dir).load()
        results = search_by_topic(index, meetings_dir, "K8s")
        assert len(results) >= 1
        assert any("Standup" in r["title"] for r in results)

    def test_search_by_participant(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import search_by_participant
        index = IndexManager(meetings_dir).load()
        results = search_by_participant(index, "laura")
        assert len(results) == 1

    def test_search_by_date(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import search_by_date
        index = IndexManager(meetings_dir).load()
        results = search_by_date(index, datetime.fromisoformat("2026-03-17"))
        assert len(results) == 1

    def test_get_action_items(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import get_action_items
        index = IndexManager(meetings_dir).load()
        results = get_action_items(index, meetings_dir)
        data = json.loads(result)
        assert len(data) >= 2

    def test_get_executive_summary(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import get_executive_summary
        index = IndexManager(meetings_dir).load()
        results = get_executive_summary(
            index, meetings_dir,
            date_from=datetime.fromisoformat("2026-03-16"),
            date_to=datetime.fromisoformat("2026-03-17"),
        )
        assert len(results) == 2

    def test_server_creates_successfully(self, server_with_data):
        """Verify FastMCP server initializes without errors."""
        server, _ = server_with_data
        assert server is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL

- [ ] **Step 3: Implement MCP server**

```python
# src/server.py
"""MCP Server exposing 6 meeting search tools via FastMCP."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

from src.index_manager import IndexManager
from src.search import (
    get_action_items as _get_action_items,
    get_executive_summary as _get_executive_summary,
    get_topic_progression as _get_topic_progression,
    search_by_date as _search_by_date,
    search_by_participant as _search_by_participant,
    search_by_topic as _search_by_topic,
)


def create_server(meetings_dir: Path | None = None) -> FastMCP:
    """Create and configure the MCP server."""
    if meetings_dir is None:
        meetings_dir = Path(__file__).parent.parent / "meetings"

    index_manager = IndexManager(meetings_dir)
    mcp = FastMCP("MCP Meet Notes")

    @mcp.tool()
    async def search_by_topic(query: str, limit: int = 5) -> str:
        """Search meetings by topic. Finds meetings where a topic was discussed,
        checking titles, summaries, and full transcripts."""
        index = index_manager.load()
        results = _search_by_topic(index, meetings_dir, query, limit)
        return json.dumps(results, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def search_by_participant(
        participant: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> str:
        """Search meetings by participant. Supports partial name matching
        (e.g., 'laura' matches 'laura.garcia@company.com')."""
        index = index_manager.load()
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        results = _search_by_participant(index, participant, df, dt)
        return json.dumps(results, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def search_by_date(
        date_from: str,
        date_to: str | None = None,
    ) -> str:
        """Search meetings by date range. If only date_from is provided,
        returns meetings from that single day."""
        index = index_manager.load()
        df = datetime.fromisoformat(date_from)
        dt = datetime.fromisoformat(date_to) if date_to else None
        results = _search_by_date(index, df, dt)
        return json.dumps(results, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_topic_progression(topic: str) -> str:
        """Track how a topic has evolved across meetings over time.
        Returns chronologically ordered summaries and excerpts."""
        index = index_manager.load()
        results = _get_topic_progression(index, meetings_dir, topic)
        return json.dumps(results, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_action_items(
        date_from: str | None = None,
        date_to: str | None = None,
        participant: str | None = None,
    ) -> str:
        """Get action items from meetings. Can filter by date range
        and/or assignee."""
        index = index_manager.load()
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        results = _get_action_items(index, meetings_dir, df, dt, participant)
        return json.dumps(results, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def get_executive_summary(
        date_from: str,
        date_to: str | None = None,
    ) -> str:
        """Get an executive summary of all meetings in a date range.
        Returns titles, summaries, and action items."""
        index = index_manager.load()
        df = datetime.fromisoformat(date_from)
        dt = datetime.fromisoformat(date_to) if date_to else None
        results = _get_executive_summary(index, meetings_dir, df, dt)
        return json.dumps(results, indent=2, ensure_ascii=False)

    return mcp


def main() -> None:
    """Entry point for the MCP server."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: all tests PASS

Note: Tests call the underlying search functions directly rather than through FastMCP internals, ensuring tests are stable across fastmcp versions. The `test_server_creates_successfully` test verifies the FastMCP server initializes correctly.

- [ ] **Step 5: Commit**

```bash
git add src/server.py tests/test_server.py
git commit -m "feat: add MCP server with 6 meeting search tools via FastMCP"
```

---

## Task 10: Scripts and Automation

**Files:**
- Create: `scripts/first_auth.py`
- Create: `scripts/install_launchd.sh`
- Create: `scripts/com.mcp-meet.sync.plist`

- [ ] **Step 1: Create OAuth first-auth script**

```python
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
```

- [ ] **Step 2: Create launchd plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!-- scripts/com.mcp-meet.sync.plist -->
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mcp-meet.sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>__PYTHON_PATH__</string>
        <string>-m</string>
        <string>src.syncer</string>
    </array>
    <key>WorkingDirectory</key>
    <string>__PROJECT_DIR__</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>__PROJECT_DIR__/logs/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>__PROJECT_DIR__/logs/launchd-stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

- [ ] **Step 3: Create install script**

```bash
#!/bin/bash
# scripts/install_launchd.sh
# Installs the daily sync job via macOS launchd.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SRC="$SCRIPT_DIR/com.mcp-meet.sync.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.mcp-meet.sync.plist"
PYTHON_PATH="$(which python3)"

echo "MCP Meet Notes — launchd installer"
echo "===================================="
echo "Project dir: $PROJECT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Unload existing job if present
if launchctl list | grep -q "com.mcp-meet.sync"; then
    echo "Unloading existing job..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Generate plist with actual paths
sed -e "s|__PYTHON_PATH__|$PYTHON_PATH|g" \
    -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
    "$PLIST_SRC" > "$PLIST_DST"

# Load the job
launchctl load "$PLIST_DST"

echo ""
echo "Installed! Sync will run daily at 9:00 AM."
echo "To run manually: launchctl start com.mcp-meet.sync"
echo "To uninstall:    launchctl unload $PLIST_DST && rm $PLIST_DST"
```

- [ ] **Step 4: Make scripts executable**

Run: `chmod +x scripts/first_auth.py scripts/install_launchd.sh`

- [ ] **Step 5: Commit**

```bash
git add scripts/
git commit -m "feat: add OAuth first-auth script and launchd daily sync installer"
```

---

## Task 11: Setup Guide and README

**Files:**
- Create: `docs/setup-guide.md`
- Create: `README.md`

- [ ] **Step 1: Write setup guide**

```markdown
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
```

- [ ] **Step 2: Write README**

```markdown
# MCP Meet Notes

Search your Google Meet transcriptions and summaries from Claude Code or Cursor.

Syncs Gemini-generated meeting notes from Google Drive to local Markdown files,
and exposes 6 search tools via MCP (Model Context Protocol).

## What can you ask?

- "What did we discuss about the K8s migration?"
- "What meetings did Laura attend this week?"
- "How has the onboarding redesign evolved over the last month?"
- "What action items came out of yesterday's meetings?"
- "Give me a summary of all meetings from this week"

## Quick Start

1. Set up Google Cloud OAuth ([setup guide](docs/setup-guide.md))
2. Install dependencies: `pip install -e ".[dev]"`
3. Authenticate: `python scripts/first_auth.py`
4. Install daily sync: `bash scripts/install_launchd.sh`
5. Add MCP server to Claude Code / Cursor config
6. Start asking questions!

## Architecture

```
Google Drive (Gemini notes) → Syncer (daily) → Local Markdown → MCP Server → Claude/Cursor
```

## Tools

| Tool | Description |
|------|-------------|
| `search_by_topic` | Find meetings where a topic was discussed |
| `search_by_participant` | Find meetings by attendee (partial match) |
| `search_by_date` | Find meetings in a date range |
| `get_topic_progression` | Track how a topic evolved over time |
| `get_action_items` | Extract action items with filters |
| `get_executive_summary` | Get a summary of meetings in a range |

## Project Structure

See [design spec](docs/superpowers/specs/2026-03-17-mcp-meet-notes-design.md) for full details.
```

- [ ] **Step 3: Commit**

```bash
git add docs/setup-guide.md README.md
git commit -m "docs: add setup guide and README"
```

---

## Task 12: Run Full Test Suite and Final Verification

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 2: Verify .gitignore works**

Run: `mkdir -p meetings logs && touch meetings/test.md logs/test.log config/token.json && git status`
Expected: none of these files appear as untracked

- [ ] **Step 3: Clean up test files**

Run: `rm -rf meetings logs/test.log config/token.json`

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```
