from datetime import datetime
from src.document_parser import parse_gemini_document


SAMPLE_GEMINI_DOC = """Date: March 17, 2026
Duration: 25 minutes
Attendees: Pedro Mantese, Laura Garcia, Carlos Ruiz

Summary
We discussed the migration to Kubernetes. There is a blocker in CI/CD due to permissions. Laura will prepare the demo for Friday stakeholders.

Transcript
Pedro: Let's start with the migration update.
Laura: I've been blocked on CI/CD permissions since Monday.
Carlos: I can help with that after lunch.

Action items
- Pedro: Review migration PR
- Laura: Prepare Friday demo
- Carlos: Fix CI/CD permissions"""


class TestParseGeminiDocument:
    def test_parse_standard_format(self):
        result = parse_gemini_document(SAMPLE_GEMINI_DOC, doc_title="Standup Backend")
        assert result.title == "Standup Backend"
        assert result.date == datetime(2026, 3, 17)
        assert result.duration_minutes == 25
        assert result.participants == ["Pedro Mantese", "Laura Garcia", "Carlos Ruiz"]
        assert "migration to Kubernetes" in result.summary
        assert "Let's start" in result.transcript
        assert len(result.action_items) == 3
        assert result.action_items[0].assignee == "Pedro"
        assert result.action_items[0].task == "Review migration PR"
        assert len(result.parse_warnings) == 0

    def test_parse_missing_duration(self):
        doc = """Date: January 5, 2026
Attendees: Pedro Mantese

Summary
Short meeting about planning.

Transcript
Pedro: Quick sync."""
        result = parse_gemini_document(doc, doc_title="Quick Sync")
        assert result.duration_minutes is None
        assert result.title == "Quick Sync"
        assert len(result.parse_warnings) == 0

    def test_parse_missing_all_metadata(self):
        doc = """Just some unstructured text that doesn't match
any expected format at all."""
        result = parse_gemini_document(doc, doc_title="Unknown Meeting")
        assert result.title == "Unknown Meeting"
        assert result.date is None
        assert result.participants == []
        assert result.transcript == doc.strip()
        assert len(result.parse_warnings) > 0

    def test_parse_missing_action_items(self):
        doc = """Date: February 10, 2026
Attendees: Pedro Mantese

Summary
We discussed the roadmap.

Transcript
Pedro: Let's review the roadmap."""
        result = parse_gemini_document(doc, doc_title="Roadmap Review")
        assert len(result.action_items) == 0

    def test_parse_date_various_formats(self):
        doc1 = "Date: March 17, 2026\n\nSummary\nTest."
        r1 = parse_gemini_document(doc1, doc_title="T")
        assert r1.date == datetime(2026, 3, 17)

        doc2 = "Date: 2026-03-17\n\nSummary\nTest."
        r2 = parse_gemini_document(doc2, doc_title="T")
        assert r2.date == datetime(2026, 3, 17)
