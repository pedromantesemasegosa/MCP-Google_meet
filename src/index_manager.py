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

from src.models import MeetingIndex, MeetingIndexEntry

logger = logging.getLogger(__name__)


class IndexManager:
    def __init__(self, meetings_dir: Path) -> None:
        self._meetings_dir = meetings_dir
        self._index_path = meetings_dir / "index.json"

    def load(self) -> MeetingIndex:
        """Load index. Returns empty if missing. Auto-regenerates if corrupted."""
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
                id=m["id"], title=m["title"],
                date=datetime.fromisoformat(m["date"]),
                duration_minutes=m.get("duration_minutes"),
                participants=m.get("participants", []),
                file=m["file"], source_doc_id=m["source_doc_id"],
                has_action_items=m.get("has_action_items", False),
                summary=m.get("summary", ""),
            )
            for m in data.get("meetings", [])
        ]
        last_sync_str = data.get("last_sync")
        last_sync = datetime.fromisoformat(last_sync_str) if last_sync_str else None
        return MeetingIndex(last_sync=last_sync, meetings=meetings)

    def save(self, index: MeetingIndex) -> None:
        """Save index atomically (write tmp, then rename)."""
        data = {
            "last_sync": index.last_sync.isoformat() if index.last_sync else None,
            "meetings": [
                {
                    "id": m.id, "title": m.title, "date": m.date.isoformat(),
                    "duration_minutes": m.duration_minutes,
                    "participants": m.participants, "file": m.file,
                    "source_doc_id": m.source_doc_id,
                    "has_action_items": m.has_action_items, "summary": m.summary,
                }
                for m in index.meetings
            ],
        }
        fd, tmp_path = tempfile.mkstemp(dir=self._meetings_dir, suffix=".tmp", prefix="index_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._index_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def add_or_update_entry(self, index: MeetingIndex, entry: MeetingIndexEntry) -> None:
        for i, m in enumerate(index.meetings):
            if m.source_doc_id == entry.source_doc_id:
                index.meetings[i] = entry
                return
        index.meetings.append(entry)

    def regenerate(self) -> MeetingIndex:
        """Regenerate index from .md files. Reads frontmatter + body."""
        entries: list[MeetingIndexEntry] = []
        for md_file in sorted(self._meetings_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            frontmatter, body = split_frontmatter(content)
            if frontmatter is None:
                continue
            meta = yaml.safe_load(frontmatter)
            if not isinstance(meta, dict):
                continue
            has_actions = _body_has_action_items(body)
            summary = _extract_summary_from_body(body)
            date_val = meta.get("date")
            if isinstance(date_val, str):
                date_val = datetime.fromisoformat(date_val)
            entries.append(MeetingIndexEntry(
                id=meta.get("id", md_file.stem), title=meta.get("title", md_file.stem),
                date=date_val, duration_minutes=meta.get("duration_minutes"),
                participants=meta.get("participants", []), file=md_file.name,
                source_doc_id=meta.get("source_doc_id", ""),
                has_action_items=has_actions, summary=summary,
            ))
        index = MeetingIndex(last_sync=None, meetings=entries)
        self.save(index)
        return index


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split YAML frontmatter from Markdown body. Public — used by search module."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, content


def _body_has_action_items(body: str) -> bool:
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
    sentences = re.split(r"(?<=[.!?])\s+", full)
    return " ".join(sentences[:2]).strip()
