"""Write Meeting objects to Markdown files with YAML frontmatter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

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
    participants_yaml = "\n".join(f'  - "{p}"' for p in meeting.participants)
    tags_yaml = "[]" if not meeting.tags else "\n".join(f'  - "{t}"' for t in meeting.tags)
    warnings_yaml = ""
    if meeting.parse_warnings:
        warnings_list = "\n".join(f'  - "{w}"' for w in meeting.parse_warnings)
        warnings_yaml = f"parse_warnings:\n{warnings_list}\n"

    frontmatter = f'''---
id: "{meeting.id}"
title: "{meeting.title}"
date: "{meeting.date.isoformat()}"
duration_minutes: {meeting.duration_minutes if meeting.duration_minutes is not None else "null"}
participants:
{participants_yaml}
source_doc_id: "{meeting.source_doc_id}"
synced_at: "{meeting.synced_at.isoformat()}"
tags: {tags_yaml}
{warnings_yaml}---'''

    action_items_section = ""
    if meeting.action_items:
        items = "\n".join(f"- [ ] {ai.assignee}: {ai.task}" for ai in meeting.action_items)
        action_items_section = f"\n## Action Items\n\n{items}\n"

    return f"""{frontmatter}

## Resumen

{meeting.summary}

## Transcripcion

{meeting.transcript}
{action_items_section}"""
