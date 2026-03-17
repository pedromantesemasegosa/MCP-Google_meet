"""Write Meeting objects to Markdown files with YAML frontmatter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml
from slugify import slugify

from src.models import Meeting


def generate_filename(meeting: Meeting) -> str:
    date_str = meeting.date.strftime("%Y-%m-%d")
    slug = slugify(meeting.title, max_length=60)
    return f"{date_str}-{slug}.md"


def write_meeting_markdown(meeting: Meeting, meetings_dir: Path) -> Path:
    filename = generate_filename(meeting)
    target_path = meetings_dir / filename
    content = _render_markdown(meeting)

    fd, tmp_path = tempfile.mkstemp(dir=meetings_dir, suffix=".tmp", prefix="meeting_")
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
    meta = {
        "id": meeting.id,
        "title": meeting.title,
        "date": meeting.date.isoformat(),
        "duration_minutes": meeting.duration_minutes,
        "participants": meeting.participants,
        "source_doc_id": meeting.source_doc_id,
        "synced_at": meeting.synced_at.isoformat() if meeting.synced_at else None,
        "tags": meeting.tags,
    }
    if meeting.parse_warnings:
        meta["parse_warnings"] = meeting.parse_warnings

    frontmatter = "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---"

    action_items_section = ""
    if meeting.action_items:
        items = "\n".join(f"- [ ] {ai.assignee}: {ai.task}" for ai in meeting.action_items)
        action_items_section = f"\n## Action Items\n\n{items}\n"

    body = f"""
## Resumen

{meeting.summary}

## Transcripcion

{meeting.transcript}
{action_items_section}"""

    return frontmatter + "\n" + body
