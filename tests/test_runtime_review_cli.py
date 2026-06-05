"""
Tests for Runtime Review CLI commands.

Sprint 27: Runtime Evidence Review Report.
"""
import json
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
    with_session_record: bool = False,
    with_evaluation: bool = False,
) -> dict:
    """Create test runtime session data."""
    data = {
        "runtime_session_id": runtime_session_id,
        "queue_id": "queue_test123",
        "scheduled_id": "sq_test123",
        "assignment_id": assignment_id,
        "student_id": "student_123",
        "status": "active",
        "started_at": "2026-01-01T00:00:00Z",
        "assignment": make_test_assignment_data(assignment_id),
    }

    if with_session_record:
        data["session_record"] = make_test_session_record_data()

    if with_evaluation:
        data["evaluation"] = make_test_evaluation_data()

    return data


def make_test_session_record_data() -> dict:
    """Create test session record data."""
    return {
        "session_id": "00000000-0000-4000-8000-000000000001",
        "instrument_id": "guitar_001",
        "engine_version": "test@0.1.0",
        "program_ref": {
            "type": "ztex",
            "name": "test_exercise",
        },
        "timing": {
            "bpm": 120,
            "grid": 16,
        },
        "duration_s": 60,
        "performance": {
            "bars_played": 4,
            "notes_expected": 16,
            "notes_played": 16,
            "notes_dropped": 0,
        },
    }


def make_test_evaluation_data() -> dict:
    """Create test evaluation data."""
    return {
        "session_id": "00000000-0000-4000-8000-000000000001",
        "coach_version": "test@0.1.0",
        "findings": [],
        "focus_recommendation": {
            "concept": "timing",
            "reason": "Focus on timing accuracy",
        },
        "confidence": 0.8,
        "strengths": ["timing"],
        "weaknesses": [],
    }


def make_test_runtime_result_data() -> dict:
    """Create test runtime result data."""
    return {
        "runtime_session_id": "rts_test123",
        "processed": True,
        "queue_updated": True,
        "curriculum_advanced": True,
        "outcome_event": {
            "id": "aoe_test123",
            "assignment_id": "pa_test123",
            "outcome": "completed",
            "timestamp": "2026-01-01T00:01:00Z",
        },
        "integration_result": {
            "processed": True,
            "updated_queue": {
                "student_id": "student_123",
                "assignments": [],
            },
            "updated_progress_state": {
                "student_id": "student_123",
                "completed_content_ids": [],
            },
            "advanced_curriculum": True,
            "curriculum_recommendation": {
                "content_id": "timing_advanced_v1",
                "diagnosis_code": "timing_grid_deviation",
                "progression_level": "beginner",
                "reason": "Completed current level",
            },
            "reasons": ["completed_successfully"],
        },
        "reasons": ["completed_successfully"],
    }


class TestRuntimeReview:
    """Tests for runtime review command."""

    def test_generates_review_report(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session_id"] == "rts_test123"
        assert output["status"] == "missing_evidence"
        assert output["student_id"] == "student_123"

    def test_with_full_evidence(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(
            make_test_runtime_session_data(
                with_session_record=True,
                with_evaluation=True,
            )
        ))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "complete"
        assert output["evidence_summary"]["has_session_record"] is True
        assert output["evidence_summary"]["has_evaluation"] is True

    def test_with_runtime_result(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_result_file = tmp_path / "runtime_result.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        runtime_result_file.write_text(json.dumps(make_test_runtime_result_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
            "--runtime-result", str(runtime_result_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["outcome_summary"]["outcome"] == "completed"
        assert output["outcome_summary"]["curriculum_advanced"] is True
        assert output["outcome_summary"]["next_curriculum_content_id"] == "timing_advanced_v1"

    def test_without_runtime_result(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["outcome_summary"]["outcome"] is None
        assert output["outcome_summary"]["queue_updated"] is False

    def test_pretty_output(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_runtime_session_file(self, tmp_path, capsys):
        result = main([
            "runtime", "review",
            "--runtime-session", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_runtime_result_file(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
            "--runtime-result", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_diagnosis_code_extracted(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["diagnosis_code"] == "timing_grid_deviation"

    def test_assignment_id_extracted(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))

        result = main([
            "runtime", "review",
            "--runtime-session", str(runtime_session_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["assignment_id"] == "pa_test123"
        assert output["queue_id"] == "queue_test123"
