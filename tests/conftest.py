import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from src.models import ActionItem, Meeting, MeetingIndex, MeetingIndexEntry


@pytest.fixture
def tmp_meetings_dir(tmp_path: Path) -> Path:
    meetings = tmp_path / "meetings"
    meetings.mkdir()
    return meetings


@pytest.fixture
def sample_meeting() -> Meeting:
    return Meeting(
        id="abc123", title="Standup Backend",
        date=datetime(2026, 3, 17, 10, 0), duration_minutes=25,
        participants=["pedro@test.com", "laura@test.com"],
        source_doc_id="doc123", synced_at=datetime(2026, 3, 17, 12, 0),
        tags=[], summary="Discussed K8s migration and CI/CD blocker.",
        transcript="Pedro: Let's talk about K8s.\nLaura: Blocked on CI.",
        action_items=[
            ActionItem(assignee="Pedro", task="Review PR"),
            ActionItem(assignee="Laura", task="Prepare demo"),
        ],
    )


@pytest.fixture
def sample_index_entry() -> MeetingIndexEntry:
    return MeetingIndexEntry(
        id="abc123", title="Standup Backend",
        date=datetime(2026, 3, 17, 10, 0), duration_minutes=25,
        participants=["pedro@test.com", "laura@test.com"],
        file="2026-03-17-standup-backend.md", source_doc_id="doc123",
        has_action_items=True,
        summary="Discussed K8s migration and CI/CD blocker.",
    )


@pytest.fixture
def sample_markdown_content() -> str:
    return '''---
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

Pedro: Let\'s talk about K8s.
Laura: Blocked on CI.

## Action Items

- [ ] Pedro: Review PR
- [ ] Laura: Prepare demo
'''
