"""MCP Server exposing 6 meeting search tools via FastMCP."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent

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


def _read_last_sync_log(project_root: Path, n_lines: int = 20) -> list[str]:
    log_path = project_root / "logs" / "sync.log"
    if not log_path.exists():
        return []
    with open(log_path, encoding="utf-8") as f:
        return f.readlines()[-n_lines:]


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
    async def get_sync_status() -> str:
        """Get the status of the last sync: when it ran, how many meetings are indexed,
        and whether the last run succeeded or failed."""
        index = index_manager.load()
        log_lines = _read_last_sync_log(_PROJECT_ROOT)

        last_sync = index.last_sync.isoformat() if index.last_sync else None
        total_meetings = len(index.meetings)

        # Parse last run result from log lines
        last_run: dict = {}
        for line in reversed(log_lines):
            line = line.strip()
            if "Sync completed" in line:
                last_run = {"status": "success", "detail": line}
                break
            if "All" in line and "attempts failed" in line:
                last_run = {"status": "failed", "detail": line}
                break
            if "Attempt" in line and "failed" in line:
                last_run = {"status": "failed", "detail": line}
                break

        result = {
            "last_sync": last_sync,
            "total_meetings_indexed": total_meetings,
            "last_run": last_run if last_run else {"status": "unknown", "detail": "No log entries found"},
            "recent_log": [l.strip() for l in log_lines[-5:]],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

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
    settings_path = _PROJECT_ROOT / "config" / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    meetings_dir = _PROJECT_ROOT / settings.get("meetings_dir", "meetings")
    server = create_server(meetings_dir=meetings_dir)
    server.run()


if __name__ == "__main__":
    main()
