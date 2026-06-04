"""
Tests for Pedagogical Evidence Ledger CLI commands.

Sprint 29: Pedagogical Evidence Ledger.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_coach.cli import main


def make_test_assignment_data(assignment_id: str = "pa_test123") -> dict:
    """Create test assignment data."""
    return {
        "id": assignment_id,
        "title": "Test Assignment",
        "assignment_type": "drill",
        "instructions": "Practice this drill",
        "diagnosis_code": "timing_grid_deviation",
    }


def make_test_runtime_session_data(
    runtime_session_id: str = "rts_test123",
    with_evaluation: bool = False,
    evaluation_codes: list[str] | None = None,
) -> dict:
    """Create test runtime session data."""
    data = {
        "runtime_session_id": runtime_session_id,
        "queue_id": "queue_test123",
        "scheduled_id": "sq_test123",
        "assignment_id": "pa_test123",
        "student_id": "student_123",
        "status": "completed",
        "started_at": "2026-01-01T00:00:00Z",
        "assignment": make_test_assignment_data(),
    }

    if with_evaluation:
        data["evaluation"] = make_test_evaluation_data(evaluation_codes or [])

    return data


def make_test_evaluation_data(codes: list[str] | None = None) -> dict:
    """Create test evaluation data."""
    findings = [
        {
            "id": f"finding_{i}",
            "type": "timing",
            "code": code,
            "severity": "primary",
            "interpretation": f"Finding {i} interpretation",
            "message": f"Finding {i}",
        }
        for i, code in enumerate(codes or [])
    ]

    return {
        "session_id": "00000000-0000-4000-8000-000000000001",
        "coach_version": "test@0.1.0",
        "findings": findings,
        "focus_recommendation": {
            "concept": "timing",
            "reason": "Focus on timing accuracy",
        },
        "confidence": 0.8,
        "strengths": [],
        "weaknesses": [],
    }


def make_test_runtime_review_report_data(
    runtime_session_id: str = "rts_test123",
    evaluation_codes: list[str] | None = None,
) -> dict:
    """Create test runtime review report data."""
    return {
        "runtime_session_id": runtime_session_id,
        "runtime_session": make_test_runtime_session_data(
            runtime_session_id=runtime_session_id,
            with_evaluation=bool(evaluation_codes),
            evaluation_codes=evaluation_codes,
        ),
        "status": "complete",
        "evidence_summary": {
            "finding_count": len(evaluation_codes) if evaluation_codes else 0,
        },
        "outcome_summary": {
            "outcome": "completed",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_test_queue_event_data(
    event_id: str = "pqe_test123",
    event_type: str = "assignment_completed",
) -> dict:
    """Create test queue event data."""
    return {
        "id": event_id,
        "queue_id": "queue_test123",
        "assignment_id": "pa_test123",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def make_test_teacher_review_data() -> dict:
    """Create test teacher review data."""
    return {
        "id": "trv_test123",
        "teacher_id": "teacher_001",
        "student_id": "student_123",
        "annotations": [
            {
                "annotation_type": "note",
                "text": "Good progress on timing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "recommendations": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class TestLedgerBuild:
    """Tests for ledger build command."""

    def test_builds_empty_ledger(self, tmp_path, capsys):
        result = main(["ledger", "build"])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["entries"] == []

    def test_builds_from_runtime_reviews_json_array(self, tmp_path, capsys):
        reviews_file = tmp_path / "reviews.json"
        reviews = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
            ),
        ]
        reviews_file.write_text(json.dumps(reviews))

        result = main([
            "ledger", "build",
            "--runtime-reviews", str(reviews_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["entries"]) == 1

    def test_builds_from_runtime_reviews_ndjson(self, tmp_path, capsys):
        reviews_file = tmp_path / "reviews.ndjson"
        reviews = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                evaluation_codes=["pitch_deviation"],
            ),
        ]
        with reviews_file.open("w", encoding="utf-8") as f:
            for review in reviews:
                f.write(json.dumps(review) + "\n")

        result = main([
            "ledger", "build",
            "--runtime-reviews", str(reviews_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["entries"]) == 2

    def test_builds_from_queue_events(self, tmp_path, capsys):
        events_file = tmp_path / "events.json"
        events = [
            make_test_queue_event_data("pqe_001"),
            make_test_queue_event_data("pqe_002"),
        ]
        events_file.write_text(json.dumps(events))

        result = main([
            "ledger", "build",
            "--queue-events", str(events_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["entries"]) == 2

    def test_builds_from_teacher_reviews(self, tmp_path, capsys):
        reviews_file = tmp_path / "reviews.json"
        reviews = [make_test_teacher_review_data()]
        reviews_file.write_text(json.dumps(reviews))

        result = main([
            "ledger", "build",
            "--teacher-reviews", str(reviews_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["entries"]) == 1

    def test_builds_with_student_id(self, tmp_path, capsys):
        result = main([
            "ledger", "build",
            "--student-id", "student_xyz",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_xyz"

    def test_builds_with_multiple_sources(self, tmp_path, capsys):
        reviews_file = tmp_path / "reviews.json"
        reviews = [
            make_test_runtime_review_report_data(
                evaluation_codes=["timing_grid_deviation"],
            ),
        ]
        reviews_file.write_text(json.dumps(reviews))

        events_file = tmp_path / "events.json"
        events = [make_test_queue_event_data()]
        events_file.write_text(json.dumps(events))

        result = main([
            "ledger", "build",
            "--runtime-reviews", str(reviews_file),
            "--queue-events", str(events_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["entries"]) == 2

    def test_pretty_output(self, tmp_path, capsys):
        result = main([
            "ledger", "build",
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_runtime_reviews_file(self, tmp_path, capsys):
        result = main([
            "ledger", "build",
            "--runtime-reviews", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestLedgerSummary:
    """Tests for ledger summary command."""

    def test_generates_summary(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = {
            "student_id": "student_123",
            "entries": [
                {
                    "evidence_id": "ped_001",
                    "source": "runtime_review",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "diagnosis_code": "timing_grid_deviation",
                    "title": "Test",
                    "summary": "Test",
                    "severity": "informational",
                }
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "ledger", "summary",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total_entries"] == 1
        assert output["runtime_review_entries"] == 1
        assert output["diagnosis_counts"]["timing_grid_deviation"] == 1

    def test_summary_empty_ledger(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = {
            "entries": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "ledger", "summary",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total_entries"] == 0

    def test_pretty_output(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = {
            "entries": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "ledger", "summary",
            "--ledger", str(ledger_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_ledger_file(self, tmp_path, capsys):
        result = main([
            "ledger", "summary",
            "--ledger", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err
