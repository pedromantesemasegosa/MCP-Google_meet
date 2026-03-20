# MCP Meet Notes

Search your Google Meet transcriptions and summaries from Claude Code or Cursor.

Syncs Gemini-generated meeting notes from Google Drive to local Markdown files,
and exposes 6 search tools via MCP (Model Context Protocol).

## What can you ask?

**Activity & summaries**
- "What happened in meetings this week?"
- "Give me an executive summary of March"
- "What decisions were made in the last two weeks?"

**Topics & projects**
- "Has the onboarding redesign been discussed recently? Is it moving forward?"
- "How has the database performance topic evolved over the last month?"
- "What was said about the Q2 roadmap across all meetings?"

**People**
- "Who has contributed the most in the last few meetings?"
- "What has Laura been working on this month?"
- "Who has the most open action items right now?"

**Action items**
- "What action items are pending from this week?"
- "Do I have any tasks assigned to me?"
- "Are there any action items from the client review that haven't been followed up?"

**Patterns & signals**
- "Is there any topic that keeps coming up without resolution?"
- "Which meetings had the most participants?"
- "Any blockers mentioned in recent syncs?"

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
| `get_sync_status` | Check when the last sync ran and whether it succeeded |

## Project Structure

See [design spec](docs/superpowers/specs/2026-03-17-mcp-meet-notes-design.md) for full details.
