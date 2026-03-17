"""Parse Gemini meeting notes from plain text into structured data."""
from __future__ import annotations

import re
from datetime import datetime

from src.models import ActionItem, ParsedDocument


def parse_gemini_document(text: str, doc_title: str) -> ParsedDocument:
    warnings: list[str] = []
    lines = text.strip().split("\n")

    date = _extract_date(lines)
    duration = _extract_duration(lines)
    participants = _extract_participants(lines)
    sections = extract_sections(text)

    summary = sections.get("summary", "")
    transcript = sections.get("transcript", "")
    action_items = extract_action_items(sections.get("action items", ""))

    if not summary and not transcript and not action_items:
        warnings.append("Could not parse document structure. Using full text as transcript.")
        transcript = text.strip()

    if date is None and _has_metadata_lines(lines):
        warnings.append("Date line found but could not be parsed.")

    return ParsedDocument(
        title=doc_title, date=date, duration_minutes=duration,
        participants=participants, summary=summary.strip(),
        transcript=transcript.strip(), action_items=action_items,
        parse_warnings=warnings,
    )


def _extract_date(lines: list[str]) -> datetime | None:
    for line in lines:
        match = re.match(r"^Date:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return _parse_date_string(match.group(1).strip())
    return None


def _parse_date_string(date_str: str) -> datetime | None:
    formats = ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _extract_duration(lines: list[str]) -> int | None:
    for line in lines:
        match = re.match(r"^Duration:\s*(\d+)\s*minutes?$", line, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_participants(lines: list[str]) -> list[str]:
    for line in lines:
        match = re.match(r"^Attendees:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return [p.strip() for p in match.group(1).split(",") if p.strip()]
    return []


def extract_sections(text: str) -> dict[str, str]:
    """Split text into sections by heading keywords. Public — used by search module.
    Recognizes both English (Gemini output) and Spanish (local files) headings."""
    heading_map = {
        "summary": "summary", "resumen": "summary",
        "transcript": "transcript", "transcripcion": "transcript", "transcripción": "transcript",
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
    """Extract action items. Public — used by search module."""
    items: list[ActionItem] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        match = re.match(r"^[-*]\s*(?:\[.\]\s*)?(\w[\w\s]*?):\s*(.+)$", line)
        if match:
            items.append(ActionItem(assignee=match.group(1).strip(), task=match.group(2).strip()))
    return items


def _has_metadata_lines(lines: list[str]) -> bool:
    return any(re.match(r"^Date:", line, re.IGNORECASE) for line in lines)
