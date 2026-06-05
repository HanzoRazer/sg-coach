"""
Tests for Runtime CLI commands.

Sprint 25: Queue-to-runtime practice session flow CLI.
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


def make_test_queue_data(
    assignment_id: str = "pa_test123",
    scheduled_id: str = "sq_test123",
    status: str = "queued",
) -> dict:
    """Create test queue data."""
    return {
        "id": "queue_test123",
        "student_id": "student_123",
        "assignments": [
            {
                "scheduled_id": scheduled_id,
                "queue_id": "queue_test123",
                "assignment_id": assignment_id,
                "student_id": "student_123",
                "title": "Test Assignment",
                "status": status,
                "scheduled_order": 0,
            }
        ],
    }


def make_test_progress_data() -> dict:
    """Create test progress state data."""
    return {
        "student_id": "student_123",
        "completed_content_ids": [],
    }


class TestRuntimeStartNext:
    """Tests for runtime start-next command."""

    def test_starts_next_assignment(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "pa_test123": make_test_assignment_data(),
        }))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session"] is not None
        assert output["runtime_session"]["assignment_id"] == "pa_test123"
        assert output["runtime_session"]["status"] == "active"

    def test_returns_none_for_empty_queue(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps({
            "id": "queue_empty",
            "assignments": [],
        }))
        assignments_file.write_text(json.dumps({}))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session"] is None
        assert "No eligible" in output["message"]

    def test_pretty_output(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "pa_test123": make_test_assignment_data(),
        }))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_error_missing_queue_file(self, tmp_path, capsys):
        assignments_file = tmp_path / "assignments.json"
        assignments_file.write_text(json.dumps({}))

        result = main([
            "runtime", "start-next",
            "--queue", str(tmp_path / "nonexistent.json"),
            "--assignments", str(assignments_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_assignments_file(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(make_test_queue_data()))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_supports_array_assignments_format(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps([
            make_test_assignment_data(),
        ]))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session"] is not None

    def test_supports_assignment_set_format(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "assignments": [make_test_assignment_data()],
        }))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session"] is not None


class TestRuntimeComplete:
    """Tests for runtime complete command."""

    def test_completes_session(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"
        progress_file = tmp_path / "progress.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "pa_test123": make_test_assignment_data(),
        }))
        progress_file.write_text(json.dumps(make_test_progress_data()))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])
        assert result == 0

        captured = capsys.readouterr()
        start_output = json.loads(captured.out)

        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(start_output["runtime_session"]))

        updated_queue_file = tmp_path / "updated_queue.json"
        updated_queue_file.write_text(json.dumps(start_output["updated_queue"]))

        result = main([
            "runtime", "complete",
            "--runtime-session", str(runtime_session_file),
            "--outcome", "completed",
            "--queue", str(updated_queue_file),
            "--progress", str(progress_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"]["processed"] is True
        assert output["result"]["queue_updated"] is True
        assert output["result"]["curriculum_advanced"] is True

    def test_complete_with_worsened_outcome(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"
        progress_file = tmp_path / "progress.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "pa_test123": make_test_assignment_data(),
        }))
        progress_file.write_text(json.dumps(make_test_progress_data()))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])
        assert result == 0

        captured = capsys.readouterr()
        start_output = json.loads(captured.out)

        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(start_output["runtime_session"]))

        updated_queue_file = tmp_path / "updated_queue.json"
        updated_queue_file.write_text(json.dumps(start_output["updated_queue"]))

        result = main([
            "runtime", "complete",
            "--runtime-session", str(runtime_session_file),
            "--outcome", "worsened",
            "--queue", str(updated_queue_file),
            "--progress", str(progress_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"]["processed"] is True
        assert output["result"]["queue_updated"] is False
        assert output["result"]["curriculum_advanced"] is False

    def test_error_missing_runtime_session_file(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        progress_file = tmp_path / "progress.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        progress_file.write_text(json.dumps(make_test_progress_data()))

        result = main([
            "runtime", "complete",
            "--runtime-session", str(tmp_path / "nonexistent.json"),
            "--outcome", "completed",
            "--queue", str(queue_file),
            "--progress", str(progress_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestRuntimeAbandon:
    """Tests for runtime abandon command."""

    def test_abandons_session(self, tmp_path, capsys):
        queue_file = tmp_path / "queue.json"
        assignments_file = tmp_path / "assignments.json"

        queue_file.write_text(json.dumps(make_test_queue_data()))
        assignments_file.write_text(json.dumps({
            "pa_test123": make_test_assignment_data(),
        }))

        result = main([
            "runtime", "start-next",
            "--queue", str(queue_file),
            "--assignments", str(assignments_file),
        ])
        assert result == 0

        captured = capsys.readouterr()
        start_output = json.loads(captured.out)

        runtime_session_file = tmp_path / "runtime_session.json"
        runtime_session_file.write_text(json.dumps(start_output["runtime_session"]))

        updated_queue_file = tmp_path / "updated_queue.json"
        updated_queue_file.write_text(json.dumps(start_output["updated_queue"]))

        result = main([
            "runtime", "abandon",
            "--runtime-session", str(runtime_session_file),
            "--queue", str(updated_queue_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["abandoned_session"]["status"] == "abandoned"
        assert output["updated_queue"]["assignments"][0]["status"] == "abandoned"

    def test_error_missing_files(self, tmp_path, capsys):
        result = main([
            "runtime", "abandon",
            "--runtime-session", str(tmp_path / "nonexistent.json"),
            "--queue", str(tmp_path / "queue.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


def make_test_runtime_session_data(
    runtime_session_id: str = "rts_test123",
    assignment_id: str = "pa_test123",
) -> dict:
    """Create test runtime session data."""
    return {
        "runtime_session_id": runtime_session_id,
        "queue_id": "queue_test123",
        "scheduled_id": "sq_test123",
        "assignment_id": assignment_id,
        "student_id": "student_123",
        "status": "active",
        "started_at": "2026-01-01T00:00:00Z",
        "assignment": make_test_assignment_data(assignment_id),
    }


DEFAULT_SESSION_UUID = "00000000-0000-4000-8000-000000000001"
ALT_SESSION_UUID = "00000000-0000-4000-8000-000000000002"
MISMATCH_SESSION_UUID = "00000000-0000-4000-8000-000000000003"


def make_test_session_record_data(session_id: str = DEFAULT_SESSION_UUID) -> dict:
    """Create test session record data matching actual SessionRecord schema."""
    return {
        "session_id": session_id,
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


def make_test_evaluation_data(session_id: str = DEFAULT_SESSION_UUID) -> dict:
    """Create test evaluation data matching actual CoachEvaluation schema."""
    return {
        "session_id": session_id,
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


class TestRuntimeAttachEvidence:
    """Tests for runtime attach-evidence command."""

    def test_attaches_evidence_to_session(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        session_file = tmp_path / "session.json"
        evaluation_file = tmp_path / "evaluation.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        session_file.write_text(json.dumps(make_test_session_record_data()))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data()))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(session_file),
            "--evaluation", str(evaluation_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"]["attached"] is True
        assert output["result"]["session_id"] == DEFAULT_SESSION_UUID
        assert output["result"]["evaluation_id"] == DEFAULT_SESSION_UUID
        assert output["result"]["runtime_session"]["session_record"] is not None
        assert output["result"]["runtime_session"]["evaluation"] is not None

    def test_attaches_evidence_with_matching_session_ids(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        session_file = tmp_path / "session.json"
        evaluation_file = tmp_path / "evaluation.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        session_file.write_text(json.dumps(make_test_session_record_data(ALT_SESSION_UUID)))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data(ALT_SESSION_UUID)))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(session_file),
            "--evaluation", str(evaluation_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"]["attached"] is True
        assert "session_evaluation_link_unverified" not in output["result"].get("reasons", [])

    def test_adds_warning_for_mismatched_session_ids(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        session_file = tmp_path / "session.json"
        evaluation_file = tmp_path / "evaluation.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        session_file.write_text(json.dumps(make_test_session_record_data(ALT_SESSION_UUID)))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data(MISMATCH_SESSION_UUID)))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(session_file),
            "--evaluation", str(evaluation_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"]["attached"] is True
        assert "session_evaluation_link_unverified" in output["result"]["reasons"]

    def test_pretty_output(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        session_file = tmp_path / "session.json"
        evaluation_file = tmp_path / "evaluation.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        session_file.write_text(json.dumps(make_test_session_record_data()))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data()))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(session_file),
            "--evaluation", str(evaluation_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_error_missing_runtime_session_file(self, tmp_path, capsys):
        session_file = tmp_path / "session.json"
        evaluation_file = tmp_path / "evaluation.json"

        session_file.write_text(json.dumps(make_test_session_record_data()))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data()))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(tmp_path / "nonexistent.json"),
            "--session", str(session_file),
            "--evaluation", str(evaluation_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_session_file(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        evaluation_file = tmp_path / "evaluation.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        evaluation_file.write_text(json.dumps(make_test_evaluation_data()))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(tmp_path / "nonexistent.json"),
            "--evaluation", str(evaluation_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_evaluation_file(self, tmp_path, capsys):
        runtime_session_file = tmp_path / "runtime_session.json"
        session_file = tmp_path / "session.json"

        runtime_session_file.write_text(json.dumps(make_test_runtime_session_data()))
        session_file.write_text(json.dumps(make_test_session_record_data()))

        result = main([
            "runtime", "attach-evidence",
            "--runtime-session", str(runtime_session_file),
            "--session", str(session_file),
            "--evaluation", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err
