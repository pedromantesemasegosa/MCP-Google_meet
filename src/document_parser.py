"""Parse meeting notes from plain text into structured data.

Supports two modes:
- Gemini format: structured with Date/Duration/Attendees headers + sections
- Generic format: any Google Doc — extracts what it can, uses full text as content
"""
from __future__ import annotations

import re
from datetime import datetime

from src.models import ActionItem, ParsedDocument


def parse_gemini_document(text: str, doc_title: str) -> ParsedDocument:
    warnings: list[str] = []
    lines = text.strip().split("\n")

    date = _extract_date(lines) or _extract_date_from_title(doc_title)
    duration = _extract_duration(lines)
    participants = _extract_participants(lines)
    sections = extract_sections(text)

    summary = sections.get("summary", "")
    transcript = sections.get("transcript", "")
    action_items = extract_action_items(sections.get("action items", ""))

    is_generic = not summary and not transcript and not action_items

    if is_generic:
        warnings.append("No Gemini structure detected. Parsed as generic document.")
        transcript = text.strip()
        summary = _extract_auto_summary(text, max_chars=300)

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


def _extract_date_from_title(title: str) -> datetime | None:
    """Try to extract a date from the document title.

    Handles patterns like:
    - "Acta 03-17", "Acta 18/10"
    - "Acta MKT 2022/10/02", "Acta JD 2/04/2021"
    - "Planificación noviembre 2023"
    - "Plan 2017/18" (academic year — returns start year)
    """
    # Full date: YYYY/MM/DD or YYYY-MM-DD
    m = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", title)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", title)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # Month name + year: "noviembre 2023", "March 2026"
    month_map = {
        "enero": 1, "february": 2, "febrero": 2, "march": 3, "marzo": 3,
        "april": 4, "abril": 4, "may": 5, "mayo": 5, "june": 6, "junio": 6,
        "july": 7, "julio": 7, "august": 8, "agosto": 8, "september": 9,
        "septiembre": 9, "october": 10, "octubre": 10, "november": 11,
        "noviembre": 11, "december": 12, "diciembre": 12, "january": 1,
    }
    m = re.search(r"(" + "|".join(month_map.keys()) + r")\s+(\d{4})", title, re.IGNORECASE)
    if m:
        month = month_map[m.group(1).lower()]
        year = int(m.group(2))
        return datetime(year, month, 1)

    # Academic year: "2017/18" or "2017-18"
    m = re.search(r"(\d{4})[/\-](\d{2})(?!\d)", title)
    if m:
        try:
            return datetime(int(m.group(1)), 1, 1)
        except ValueError:
            pass

    return None


def _extract_auto_summary(text: str, max_chars: int = 300) -> str:
    """Build a summary from the first meaningful lines of a generic document.

    Skips blank lines and very short lines (titles, headers) to find
    the first substantive paragraph(s).
    """
    lines = text.strip().split("\n")
    meaningful: list[str] = []
    chars = 0

    for line in lines:
        stripped = line.strip()
        # Skip blanks, very short lines (likely titles), and BOM
        if not stripped or stripped == "\ufeff":
            continue
        # Skip lines that look like headings (all caps, very short)
        if len(stripped) < 15 and stripped == stripped.upper():
            continue

        meaningful.append(stripped)
        chars += len(stripped)
        if chars >= max_chars:
            break

    result = " ".join(meaningful)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit(" ", 1)[0] + "..."
    return result
