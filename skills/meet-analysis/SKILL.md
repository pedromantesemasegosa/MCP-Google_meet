---
name: meet-analysis
description: >
  Analyzes meeting notes using the mcp__meet-notes MCP server, cross-referencing multiple tools
  to deliver synthesized insights rather than raw data. Use when the user asks about meetings,
  for example: "what happened with X this week?", "what are the pending action items?",
  "has topic Y progressed?", "what did Laura work on last month?", "give me a weekly summary",
  "any blockers?", "what decisions were made about Z?". Covers topic tracking, participant
  analysis, action item extraction, executive summaries, and trend detection across meetings.
---

# Meet Analysis

## Overview

Use the `mcp__meet-notes__*` tools to retrieve raw meeting data, then analyze and synthesize
the results into clear, actionable insights. Never just return the raw JSON — always interpret it.

## Available Tools

| Tool | Parameters | Best for |
|---|---|---|
| `mcp__meet-notes__search_by_topic` | `query`, `limit` | Finding meetings where a topic was discussed |
| `mcp__meet-notes__search_by_participant` | `participant`, `date_from?`, `date_to?` | Participant activity and involvement |
| `mcp__meet-notes__search_by_date` | `date_from`, `date_to?` | What happened in a time window |
| `mcp__meet-notes__get_topic_progression` | `topic` | How a topic has evolved over time |
| `mcp__meet-notes__get_action_items` | `date_from?`, `date_to?`, `participant?` | Pending tasks and commitments |
| `mcp__meet-notes__get_executive_summary` | `date_from`, `date_to?` | High-level summary of a period |

Dates use ISO format: `"2026-03-01"` or `"2026-03-01T09:00:00"`.

## Workflow

### Step 1 — Identify intent and select tools

Map the user's request to one of these patterns, and call the relevant tools **in parallel**:

**"What happened with [topic/project]?"**
→ `get_topic_progression(topic)` + `get_action_items()` filtered by period + `search_by_topic(topic)`

**"What did [person] do / work on?"**
→ `search_by_participant(participant, date_from, date_to)` + `get_action_items(participant=person)`

**"Summary of this week / month"**
→ `get_executive_summary(date_from, date_to)` + `get_action_items(date_from, date_to)`

**"Any blockers / pending items / decisions?"**
→ `get_action_items(date_from, date_to)` + `search_by_topic("blocker")` or `search_by_topic("decision")`

**"How has [topic] evolved?"**
→ `get_topic_progression(topic)` — this is the primary tool for trend analysis

When uncertain, default to calling 2-3 tools in parallel to get broader coverage.

### Step 2 — Analyze the results

After getting the raw JSON, synthesize across all results:

- **Progression**: Is the topic gaining momentum or stalling? Are decisions being made or deferred?
- **Ownership**: Who drives this topic? Who is assigned action items?
- **Gaps**: Are there action items without assignees? Topics discussed but never resolved?
- **Recurrence**: Is the same issue appearing in multiple meetings (likely a blocker)?
- **Volume**: More meetings on a topic = higher priority or higher friction

### Step 3 — Deliver structured insights

Present results in natural language with a clear structure:

```
## [Topic / Period / Person]

**Summary:** 1-2 sentences on the overall picture.

**Key moments:**
- [Date] — [what happened, decision made, or milestone reached]
- ...

**Open action items:**
- [Item] → [assignee if known]
- ...

**Trend / Assessment:** Is this progressing, blocked, or stalled?
```

Adapt the structure to the question. For quick questions, a short paragraph is fine.
For executive summaries or weekly reviews, use the full structure.

## Tips

- When the user gives a vague date like "this week" or "last month", resolve it to ISO dates
  using today's date before calling the tools.
- Partial name matching works: `"laura"` will match `"laura.garcia@company.com"`.
- If a topic returns no results, try synonyms or broader terms.
- If action items reference a topic, cross-reference with `get_topic_progression` to add context.
