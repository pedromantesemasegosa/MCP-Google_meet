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
