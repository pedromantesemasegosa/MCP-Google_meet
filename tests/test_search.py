from datetime import datetime
from pathlib import Path
import pytest
from src.models import MeetingIndex, MeetingIndexEntry
from src.search import (
    search_by_topic, search_by_participant, search_by_date,
    get_topic_progression, get_action_items, get_executive_summary,
)


def _make_entry(id, title, date, participants, summary, file, has_action_items=False):
    return MeetingIndexEntry(
        id=id, title=title, date=date, duration_minutes=30,
        participants=participants, file=file, source_doc_id=f"doc_{id}",
        has_action_items=has_action_items, summary=summary,
    )


@pytest.fixture
def test_index():
    return MeetingIndex(
        last_sync=datetime(2026, 3, 17),
        meetings=[
            _make_entry("1", "Standup Backend", datetime(2026, 3, 15),
                        ["pedro@test.com", "laura@test.com"],
                        "Discussed K8s migration progress.", "2026-03-15-standup-backend.md",
                        has_action_items=True),
            _make_entry("2", "Planning Sprint 42", datetime(2026, 3, 16),
                        ["pedro@test.com", "carlos@test.com"],
                        "Sprint planning for Q2 features.", "2026-03-16-planning-sprint-42.md"),
            _make_entry("3", "1:1 Pedro Laura", datetime(2026, 3, 17),
                        ["pedro@test.com", "laura@test.com"],
                        "Career growth and K8s migration blockers.", "2026-03-17-1on1-pedro-laura.md",
                        has_action_items=True),
            _make_entry("4", "Design Review", datetime(2026, 3, 10),
                        ["carlos@test.com", "maria@test.com"],
                        "Reviewed new onboarding flow.", "2026-03-10-design-review.md"),
        ],
    )


@pytest.fixture
def test_meetings_dir(tmp_path, test_index):
    meetings = tmp_path / "meetings"
    meetings.mkdir()
    contents = {
        "2026-03-15-standup-backend.md": "---\nid: \"1\"\ntitle: \"Standup Backend\"\n---\n\n## Resumen\n\nDiscussed K8s migration progress. CI/CD pipeline needs fixing.\n\n## Action Items\n\n- [ ] Pedro: Review migration PR\n",
        "2026-03-16-planning-sprint-42.md": "---\nid: \"2\"\ntitle: \"Planning Sprint 42\"\n---\n\n## Resumen\n\nSprint planning for Q2 features. Focus on user onboarding redesign.\n",
        "2026-03-17-1on1-pedro-laura.md": "---\nid: \"3\"\ntitle: \"1:1 Pedro Laura\"\n---\n\n## Resumen\n\nCareer growth and K8s migration blockers. Laura wants to lead the next project.\n\n## Action Items\n\n- [ ] Laura: Prepare tech talk proposal\n- [ ] Pedro: Schedule follow-up with manager\n",
        "2026-03-10-design-review.md": "---\nid: \"4\"\ntitle: \"Design Review\"\n---\n\n## Resumen\n\nReviewed new onboarding flow. Need more user testing data.\n",
    }
    for name, content in contents.items():
        (meetings / name).write_text(content)
    return meetings


class TestSearchByTopic:
    def test_match_in_title(self, test_index, test_meetings_dir):
        results = search_by_topic(test_index, test_meetings_dir, "standup")
        assert any(r["title"] == "Standup Backend" for r in results)

    def test_match_in_summary(self, test_index, test_meetings_dir):
        results = search_by_topic(test_index, test_meetings_dir, "K8s")
        assert len(results) >= 2

    def test_no_results(self, test_index, test_meetings_dir):
        results = search_by_topic(test_index, test_meetings_dir, "nonexistent_xyz")
        assert len(results) == 0

    def test_fulltext_fallback(self, test_index, test_meetings_dir):
        results = search_by_topic(test_index, test_meetings_dir, "CI/CD", limit=5)
        assert any(r["id"] == "1" for r in results)


class TestSearchByParticipant:
    def test_exact_match(self, test_index, test_meetings_dir):
        results = search_by_participant(test_index, "pedro@test.com")
        assert len(results) == 3

    def test_partial_match(self, test_index, test_meetings_dir):
        results = search_by_participant(test_index, "laura")
        assert len(results) == 2

    def test_with_date_range(self, test_index, test_meetings_dir):
        results = search_by_participant(test_index, "pedro", date_from=datetime(2026, 3, 16))
        assert len(results) == 2


class TestSearchByDate:
    def test_single_day(self, test_index, test_meetings_dir):
        results = search_by_date(test_index, date_from=datetime(2026, 3, 17))
        assert len(results) == 1
        assert results[0]["title"] == "1:1 Pedro Laura"

    def test_date_range(self, test_index, test_meetings_dir):
        results = search_by_date(test_index, date_from=datetime(2026, 3, 15), date_to=datetime(2026, 3, 17))
        assert len(results) == 3


class TestGetTopicProgression:
    def test_progression_order(self, test_index, test_meetings_dir):
        results = get_topic_progression(test_index, test_meetings_dir, "K8s")
        assert len(results) >= 2
        dates = [r["date"] for r in results]
        assert dates == sorted(dates)

    def test_includes_excerpts(self, test_index, test_meetings_dir):
        results = get_topic_progression(test_index, test_meetings_dir, "K8s")
        for r in results:
            assert "excerpt" in r


class TestGetActionItems:
    def test_all_action_items(self, test_index, test_meetings_dir):
        results = get_action_items(test_index, test_meetings_dir)
        assert len(results) >= 3

    def test_filter_by_participant(self, test_index, test_meetings_dir):
        results = get_action_items(test_index, test_meetings_dir, participant="Pedro")
        assert all(r["assignee"] == "Pedro" for r in results)

    def test_filter_by_date(self, test_index, test_meetings_dir):
        results = get_action_items(test_index, test_meetings_dir, date_from=datetime(2026, 3, 17))
        assert all(r["meeting_date"] >= "2026-03-17" for r in results)


class TestGetExecutiveSummary:
    def test_summary_range(self, test_index, test_meetings_dir):
        results = get_executive_summary(test_index, test_meetings_dir, date_from=datetime(2026, 3, 15), date_to=datetime(2026, 3, 17))
        assert len(results) == 3
        for r in results:
            assert "title" in r
            assert "summary" in r
            assert "action_items" in r
