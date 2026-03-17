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
        assert len(results) >= 2

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

    def test_get_topic_progression(self, server_with_data):
        _, meetings_dir = server_with_data
        from src.index_manager import IndexManager
        from src.search import get_topic_progression
        index = IndexManager(meetings_dir).load()
        results = get_topic_progression(index, meetings_dir, "K8s")
        assert len(results) >= 1
        dates = [r["date"] for r in results]
        assert dates == sorted(dates)

    def test_server_creates_successfully(self, server_with_data):
        """Verify FastMCP server initializes without errors."""
        server, _ = server_with_data
        assert server is not None
