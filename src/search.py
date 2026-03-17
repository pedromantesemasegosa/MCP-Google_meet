"""Search logic for meetings — used by MCP server tools."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.document_parser import extract_action_items, extract_sections
from src.index_manager import split_frontmatter
from src.models import MeetingIndex, MeetingIndexEntry


def search_by_topic(index, meetings_dir, query, limit=5):
    query_lower = query.lower()
    results, seen_ids = [], set()
    for entry in index.meetings:
        score = _score_index_match(entry, query_lower)
        if score > 0:
            results.append(_entry_to_result(entry, score))
            seen_ids.add(entry.id)
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


def search_by_participant(index, participant, date_from=None, date_to=None):
    participant_lower = participant.lower()
    results = []
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


def search_by_date(index, date_from, date_to=None):
    if date_to is None:
        date_to = date_from.replace(hour=23, minute=59, second=59)
    results = []
    for entry in index.meetings:
        if date_from <= entry.date <= date_to:
            results.append(_entry_to_result(entry))
    results.sort(key=lambda r: r["date"])
    return results


def get_topic_progression(index, meetings_dir, topic):
    topic_lower = topic.lower()
    results = []
    for entry in index.meetings:
        in_index = topic_lower in entry.title.lower() or topic_lower in entry.summary.lower()
        file_path = meetings_dir / entry.file
        content = ""
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
        in_content = topic_lower in content.lower()
        if in_index or in_content:
            excerpt = _extract_excerpt(content, topic_lower)
            results.append({
                "id": entry.id, "title": entry.title,
                "date": entry.date.isoformat(), "summary": entry.summary,
                "excerpt": excerpt, "participants": entry.participants,
            })
    results.sort(key=lambda r: r["date"])
    return results


def get_action_items(index, meetings_dir, date_from=None, date_to=None, participant=None):
    results = []
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
                "assignee": item.assignee, "task": item.task,
                "meeting_title": entry.title, "meeting_date": entry.date.isoformat(),
                "meeting_id": entry.id,
            })
    return results


def get_executive_summary(index, meetings_dir, date_from, date_to=None):
    if date_to is None:
        date_to = date_from.replace(hour=23, minute=59, second=59)
    results = []
    for entry in index.meetings:
        if not (date_from <= entry.date <= date_to):
            continue
        action_items = []
        if entry.has_action_items:
            file_path = meetings_dir / entry.file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                _, body = split_frontmatter(content)
                sections = extract_sections(body)
                items = extract_action_items(sections.get("action items", ""))
                action_items = [{"assignee": i.assignee, "task": i.task} for i in items]
        results.append({
            "id": entry.id, "title": entry.title, "date": entry.date.isoformat(),
            "summary": entry.summary, "participants": entry.participants,
            "action_items": action_items,
        })
    results.sort(key=lambda r: r["date"])
    return results


def _score_index_match(entry, query_lower):
    score = 0
    if query_lower in entry.title.lower():
        score += 3
    if query_lower in entry.summary.lower():
        score += 2
    return score


def _entry_to_result(entry, score=0):
    return {
        "id": entry.id, "title": entry.title, "date": entry.date.isoformat(),
        "summary": entry.summary, "participants": entry.participants,
        "has_action_items": entry.has_action_items, "_score": score,
    }


def _extract_excerpt(content, query_lower, context_chars=200):
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
