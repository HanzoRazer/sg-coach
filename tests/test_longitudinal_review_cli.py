"""
Tests for Longitudinal Review CLI commands.

Sprint 28: Longitudinal Progress Review.
"""
import json
from datetime import datetime, timezone, timedelta
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
        "params": {"curriculum_content_id": "timing_foundation_v1"},
    }


def make_test_runtime_session_data(
    runtime_session_id: str = "rts_test123",
    assignment_id: str = "pa_test123",
    with_evaluation: bool = False,
    evaluation_codes: list[str] | None = None,
) -> dict:
    """Create test runtime session data."""
    data = {
        "runtime_session_id": runtime_session_id,
        "queue_id": "queue_test123",
        "scheduled_id": "sq_test123",
        "assignment_id": assignment_id,
        "student_id": "student_123",
        "status": "completed",
        "started_at": "2026-01-01T00:00:00Z",
        "assignment": make_test_assignment_data(assignment_id),
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
        "strengths": ["timing"],
        "weaknesses": [],
    }


def make_test_runtime_review_report_data(
    runtime_session_id: str = "rts_test123",
    outcome: str = "completed",
    evaluation_codes: list[str] | None = None,
    generated_at: str | None = None,
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
            "outcome": outcome,
        },
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
    }


class TestLongitudinalReview:
    """Tests for longitudinal-review command."""

    def test_generates_review_from_ndjson(self, tmp_path, capsys):
        now = datetime.now(timezone.utc)

        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                outcome="completed",
                generated_at=(now - timedelta(days=3)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                outcome="improved",
                generated_at=(now - timedelta(days=2)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_003",
                outcome="completed",
                generated_at=(now - timedelta(days=1)).isoformat(),
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["review_count"] == 3
        assert len(output["evidence_review_ids"]) == 3

    def test_with_student_id(self, tmp_path, capsys):
        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(runtime_session_id="rts_001"),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
            "--student-id", "student_123",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_123"

    def test_diagnosis_trends_aggregated(self, tmp_path, capsys):
        now = datetime.now(timezone.utc)

        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=3)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=2)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_003",
                evaluation_codes=[],
                generated_at=(now - timedelta(days=1)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_004",
                evaluation_codes=[],
                generated_at=now.isoformat(),
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["diagnosis_trends"]) == 1
        trend = output["diagnosis_trends"][0]
        assert trend["diagnosis_code"] == "timing_grid_deviation"
        assert trend["trend"] == "improving"

    def test_outcome_trajectory_aggregated(self, tmp_path, capsys):
        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                outcome="completed",
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                outcome="improved",
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_003",
                outcome="repeated",
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        trajectory = output["outcome_trajectory"]
        assert trajectory["total_completed"] == 1
        assert trajectory["total_improved"] == 1
        assert trajectory["total_repeated"] == 1

    def test_pretty_output(self, tmp_path, capsys):
        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(runtime_session_id="rts_001"),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_reports_file(self, tmp_path, capsys):
        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(tmp_path / "nonexistent.ndjson"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_empty_reports_file(self, tmp_path, capsys):
        reports_file = tmp_path / "reports.ndjson"
        reports_file.write_text("")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["review_count"] == 0
        assert output["diagnosis_trends"] == []

    def test_notes_included_for_insufficient_data(self, tmp_path, capsys):
        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert any("insufficient" in note.lower() for note in output["notes"])

    def test_strongest_improvements_identified(self, tmp_path, capsys):
        now = datetime.now(timezone.utc)

        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=3)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=2)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_003",
                evaluation_codes=[],
                generated_at=(now - timedelta(days=1)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_004",
                evaluation_codes=[],
                generated_at=now.isoformat(),
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "timing_grid_deviation" in output["strongest_improvements"]

    def test_recurring_challenges_identified(self, tmp_path, capsys):
        now = datetime.now(timezone.utc)

        reports_file = tmp_path / "reports.ndjson"
        reports = [
            make_test_runtime_review_report_data(
                runtime_session_id="rts_001",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=3)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_002",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=2)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_003",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=(now - timedelta(days=1)).isoformat(),
            ),
            make_test_runtime_review_report_data(
                runtime_session_id="rts_004",
                evaluation_codes=["timing_grid_deviation"],
                generated_at=now.isoformat(),
            ),
        ]

        with reports_file.open("w", encoding="utf-8") as f:
            for report in reports:
                f.write(json.dumps(report) + "\n")

        result = main([
            "runtime", "longitudinal-review",
            "--reports", str(reports_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "timing_grid_deviation" in output["recurring_challenges"]
