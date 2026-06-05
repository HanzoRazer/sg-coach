"""
Tests for Pedagogical Narrative CLI commands.

Sprint 35: Pedagogical Narrative Layer.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_coach.cli import main


def make_test_session_view_data() -> dict:
    """Create test session view data."""
    return {
        "view_id": "gpsv_test123456",
        "student_id": "student_001",
        "runtime_session_id": "rts_test123",
        "queue_id": "queue_test123",
        "assignment": {
            "assignment_id": "pa_test123",
            "title": "Test Assignment",
            "assignment_type": "drill",
            "priority": "normal",
            "status": "queued",
            "runtime_active": False,
            "adaptive": False,
            "teacher_modified": False,
            "has_success_criteria": True,
            "has_coach_prompts": True,
        },
        "playback": {
            "playback_available": True,
            "runtime_session_id": "rts_test123",
            "timeline_event_count": 10,
            "finding_overlay_count": 3,
            "active_finding_ids": ["finding_1"],
            "critical_overlay_count": 0,
        },
        "adaptive_guidance": {
            "recommendation_count": 2,
            "high_priority_count": 1,
            "critical_priority_count": 0,
            "active_recommendation_ids": ["asr_001"],
            "evidence_ids": ["ped_001"],
        },
        "teacher_mediation": {
            "mediation_count": 1,
            "latest_mediation_id": "tsm_001",
            "approved_count": 1,
            "modified_count": 0,
            "rejected_count": 0,
            "deferred_count": 0,
            "teacher_override_count": 0,
        },
        "timeline": {
            "total_events": 5,
            "timeline_events": [],
            "diagnosis_groups": [],
        },
        "notes": ["Test note"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_test_runtime_review_data() -> dict:
    """Create test runtime review data."""
    return {
        "runtime_session_id": "rts_test123",
        "status": "complete",
        "student_id": "student_001",
        "assignment_id": "pa_test123",
        "runtime_session": {
            "runtime_session_id": "rts_test123",
            "queue_id": "queue_test123",
            "scheduled_id": "sq_test123",
            "assignment_id": "pa_test123",
            "student_id": "student_001",
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "assignment": {
                "id": "pa_test123",
                "title": "Test Assignment",
                "assignment_type": "drill",
                "instructions": "Test instructions",
            },
        },
        "evidence_summary": {
            "has_session_record": True,
            "has_evaluation": True,
            "finding_count": 3,
            "recommendation_count": 2,
        },
        "outcome_summary": {
            "outcome": "improved",
            "queue_updated": True,
            "curriculum_advanced": True,
            "reasons": ["Improved timing"],
        },
    }


def make_test_longitudinal_review_data() -> dict:
    """Create test longitudinal review data."""
    return {
        "student_id": "student_001",
        "review_count": 10,
        "diagnosis_trends": [
            {
                "diagnosis_code": "timing_grid_deviation",
                "total_occurrences": 5,
                "trend": "improving",
            }
        ],
        "outcome_trajectory": {
            "total_completed": 8,
            "total_improved": 5,
            "total_repeated": 2,
            "total_worsened": 1,
            "total_abandoned": 0,
            "completion_ratio": 0.8,
            "improvement_ratio": 0.625,
        },
        "strongest_improvements": ["Timing accuracy"],
        "recurring_challenges": ["Pitch consistency"],
        "evidence_review_ids": ["rrr_001"],
        "notes": ["Good progress"],
    }


class TestNarrativeGuidedSessionCommand:
    """Tests for the narrative guided-session CLI command."""

    def test_basic_narrative(self, tmp_path: Path, capsys) -> None:
        view_path = tmp_path / "session_view.json"
        view_data = make_test_session_view_data()
        view_path.write_text(json.dumps(view_data))

        result = main(["narrative", "guided-session", "--session-view", str(view_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["narrative_id"].startswith("pn_")
        assert output["audience"] == "mixed"
        assert len(output["sections"]) == 5

    def test_with_student_audience(self, tmp_path: Path, capsys) -> None:
        view_path = tmp_path / "session_view.json"
        view_data = make_test_session_view_data()
        view_path.write_text(json.dumps(view_data))

        result = main([
            "narrative", "guided-session",
            "--session-view", str(view_path),
            "--audience", "student",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["audience"] == "student"

    def test_with_teacher_audience(self, tmp_path: Path, capsys) -> None:
        view_path = tmp_path / "session_view.json"
        view_data = make_test_session_view_data()
        view_path.write_text(json.dumps(view_data))

        result = main([
            "narrative", "guided-session",
            "--session-view", str(view_path),
            "--audience", "teacher",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["audience"] == "teacher"

    def test_pretty_output(self, tmp_path: Path, capsys) -> None:
        view_path = tmp_path / "session_view.json"
        view_data = make_test_session_view_data()
        view_path.write_text(json.dumps(view_data))

        result = main([
            "narrative", "guided-session",
            "--session-view", str(view_path),
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        # Pretty output should be indented
        assert "  " in captured.out

    def test_title_includes_assignment(self, tmp_path: Path, capsys) -> None:
        view_path = tmp_path / "session_view.json"
        view_data = make_test_session_view_data()
        view_path.write_text(json.dumps(view_data))

        result = main(["narrative", "guided-session", "--session-view", str(view_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "Test Assignment" in output["title"]

    def test_error_missing_file(self, tmp_path: Path) -> None:
        view_path = tmp_path / "nonexistent.json"
        result = main(["narrative", "guided-session", "--session-view", str(view_path)])
        assert result == 1


class TestNarrativeRuntimeReviewCommand:
    """Tests for the narrative runtime-review CLI command."""

    def test_basic_narrative(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_runtime_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main(["narrative", "runtime-review", "--review", str(review_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["narrative_id"].startswith("pn_")
        assert output["title"] == "Runtime Practice Review"
        assert len(output["sections"]) == 2

    def test_with_teacher_audience(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_runtime_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main([
            "narrative", "runtime-review",
            "--review", str(review_path),
            "--audience", "teacher",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["audience"] == "teacher"

    def test_pretty_output(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_runtime_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main([
            "narrative", "runtime-review",
            "--review", str(review_path),
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        assert "  " in captured.out

    def test_metadata_populated(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_runtime_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main(["narrative", "runtime-review", "--review", str(review_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["metadata"]["runtime_session_id"] == "rts_test123"

    def test_error_missing_file(self, tmp_path: Path) -> None:
        review_path = tmp_path / "nonexistent.json"
        result = main(["narrative", "runtime-review", "--review", str(review_path)])
        assert result == 1


class TestNarrativeLongitudinalReviewCommand:
    """Tests for the narrative longitudinal-review CLI command."""

    def test_basic_narrative(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_longitudinal_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main(["narrative", "longitudinal-review", "--review", str(review_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["narrative_id"].startswith("pn_")
        assert output["title"] == "Longitudinal Progress Review"
        assert len(output["sections"]) == 3

    def test_defaults_to_teacher_audience(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_longitudinal_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main(["narrative", "longitudinal-review", "--review", str(review_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["audience"] == "teacher"

    def test_with_student_audience(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_longitudinal_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main([
            "narrative", "longitudinal-review",
            "--review", str(review_path),
            "--audience", "student",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["audience"] == "student"

    def test_pretty_output(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_longitudinal_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main([
            "narrative", "longitudinal-review",
            "--review", str(review_path),
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        assert "  " in captured.out

    def test_overview_includes_review_count(self, tmp_path: Path, capsys) -> None:
        review_path = tmp_path / "review.json"
        review_data = make_test_longitudinal_review_data()
        review_path.write_text(json.dumps(review_data))

        result = main(["narrative", "longitudinal-review", "--review", str(review_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "10" in output["overview"]

    def test_error_missing_file(self, tmp_path: Path) -> None:
        review_path = tmp_path / "nonexistent.json"
        result = main(["narrative", "longitudinal-review", "--review", str(review_path)])
        assert result == 1
