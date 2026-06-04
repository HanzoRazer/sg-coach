"""
Tests for Guided Practice Session View CLI commands.

Sprint 34: Guided Practice Session UX Projection.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_coach.cli import main


def make_test_assignment_data(
    assignment_id: str = "pa_test123",
    title: str = "Test Assignment",
) -> dict:
    """Create test assignment data."""
    return {
        "id": assignment_id,
        "title": title,
        "assignment_type": "drill",
        "instructions": "Practice this drill carefully.",
    }


def make_test_queue_data(
    queue_id: str = "queue_test123",
    student_id: str = "student_001",
    assignments: list[dict] | None = None,
) -> dict:
    """Create test queue data."""
    scheduled = []
    for i, assignment in enumerate(assignments or []):
        scheduled.append({
            "scheduled_id": f"sq_{i}",
            "queue_id": queue_id,
            "assignment_id": assignment.get("id", f"pa_test{i}"),
            "title": assignment.get("title", "Test Assignment"),
            "scheduled_order": i,
            "priority": "normal",
            "status": "queued",
        })
    return {
        "id": queue_id,
        "student_id": student_id,
        "assignments": scheduled,
        "version": "0.1",
    }


def make_test_runtime_session_data(
    runtime_session_id: str = "rts_test123",
    assignment_id: str = "pa_test123",
) -> dict:
    """Create test runtime session data."""
    return {
        "runtime_session_id": runtime_session_id,
        "queue_id": "queue_test123",
        "scheduled_id": "sq_0",
        "assignment_id": assignment_id,
        "student_id": "student_001",
        "status": "active",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "assignment": make_test_assignment_data(assignment_id=assignment_id),
    }


def make_test_adaptive_plan_data(
    student_id: str = "student_001",
) -> dict:
    """Create test adaptive scheduling plan data."""
    return {
        "student_id": student_id,
        "recommendations": [
            {
                "recommendation_id": "asr_001",
                "reasons": ["worsening_trend"],
                "diagnosis_code": "timing_grid_deviation",
                "priority_adjustment": "increase",
                "recommended_priority": "high",
                "evidence_ids": ["ped_001"],
                "rationale": "Test rationale",
            }
        ],
        "source_evidence_count": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "0.1",
    }


def make_test_mediation_data(
    mediation_id: str = "tsm_001",
    action: str = "approve",
) -> dict:
    """Create test mediation data."""
    return {
        "id": mediation_id,
        "recommendation_id": "asr_001",
        "teacher_id": "teacher_001",
        "action": action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def make_test_timeline_data(
    student_id: str = "student_001",
    total_events: int = 5,
) -> dict:
    """Create test timeline view data."""
    return {
        "student_id": student_id,
        "total_events": total_events,
        "timeline_events": [],
        "diagnosis_groups": [],
        "notes": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "0.1",
    }


class TestGuidedSessionViewCommand:
    """Tests for the guided-session-view CLI command."""

    def test_minimal_view(self, tmp_path: Path, capsys) -> None:
        result = main(["guided-session-view"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["view_id"].startswith("gpsv_")

    def test_with_queue(self, tmp_path: Path, capsys) -> None:
        queue_path = tmp_path / "queue.json"
        queue_data = make_test_queue_data()
        queue_path.write_text(json.dumps(queue_data))

        result = main(["guided-session-view", "--queue", str(queue_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["queue_id"] == "queue_test123"
        assert output["student_id"] == "student_001"

    def test_with_assignment(self, tmp_path: Path, capsys) -> None:
        assignment_path = tmp_path / "assignment.json"
        assignment_data = make_test_assignment_data()
        assignment_path.write_text(json.dumps(assignment_data))

        result = main(["guided-session-view", "--assignment", str(assignment_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["assignment"] is not None
        assert output["assignment"]["assignment_id"] == "pa_test123"

    def test_with_runtime_session(self, tmp_path: Path, capsys) -> None:
        rts_path = tmp_path / "runtime_session.json"
        rts_data = make_test_runtime_session_data()
        rts_path.write_text(json.dumps(rts_data))

        result = main(["guided-session-view", "--runtime-session", str(rts_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["runtime_session_id"] == "rts_test123"

    def test_with_adaptive_plan(self, tmp_path: Path, capsys) -> None:
        plan_path = tmp_path / "adaptive_plan.json"
        plan_data = make_test_adaptive_plan_data()
        plan_path.write_text(json.dumps(plan_data))

        result = main(["guided-session-view", "--adaptive-plan", str(plan_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["adaptive_guidance"] is not None
        assert output["adaptive_guidance"]["recommendation_count"] == 1

    def test_with_mediations_array(self, tmp_path: Path, capsys) -> None:
        mediations_path = tmp_path / "mediations.json"
        mediations_data = [make_test_mediation_data()]
        mediations_path.write_text(json.dumps(mediations_data))

        result = main(["guided-session-view", "--mediations", str(mediations_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["teacher_mediation"] is not None
        assert output["teacher_mediation"]["mediation_count"] == 1

    def test_with_single_mediation(self, tmp_path: Path, capsys) -> None:
        mediations_path = tmp_path / "mediation.json"
        mediation_data = make_test_mediation_data()
        mediations_path.write_text(json.dumps(mediation_data))

        result = main(["guided-session-view", "--mediations", str(mediations_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["teacher_mediation"]["mediation_count"] == 1

    def test_with_timeline(self, tmp_path: Path, capsys) -> None:
        timeline_path = tmp_path / "timeline.json"
        timeline_data = make_test_timeline_data(total_events=10)
        timeline_path.write_text(json.dumps(timeline_data))

        result = main(["guided-session-view", "--timeline", str(timeline_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["timeline"] is not None
        assert output["timeline"]["total_events"] == 10

    def test_with_student_id_override(self, tmp_path: Path, capsys) -> None:
        queue_path = tmp_path / "queue.json"
        queue_data = make_test_queue_data(student_id="original_id")
        queue_path.write_text(json.dumps(queue_data))

        result = main([
            "guided-session-view",
            "--queue", str(queue_path),
            "--student-id", "override_id",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "override_id"

    def test_pretty_output(self, tmp_path: Path, capsys) -> None:
        result = main(["guided-session-view", "--pretty"])
        assert result == 0

        captured = capsys.readouterr()
        # Pretty output should be indented
        assert "  " in captured.out

    def test_notes_for_no_assignment(self, tmp_path: Path, capsys) -> None:
        result = main(["guided-session-view"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "No active practice assignment is available." in output["notes"]

    def test_error_missing_queue_file(self, tmp_path: Path) -> None:
        queue_path = tmp_path / "nonexistent.json"
        result = main(["guided-session-view", "--queue", str(queue_path)])
        assert result == 1

    def test_error_missing_assignment_file(self, tmp_path: Path) -> None:
        assignment_path = tmp_path / "nonexistent.json"
        result = main(["guided-session-view", "--assignment", str(assignment_path)])
        assert result == 1

    def test_error_invalid_json(self, tmp_path: Path) -> None:
        queue_path = tmp_path / "invalid.json"
        queue_path.write_text("not valid json")
        result = main(["guided-session-view", "--queue", str(queue_path)])
        assert result == 1

    def test_full_integration(self, tmp_path: Path, capsys) -> None:
        assignment_data = make_test_assignment_data()
        queue_data = make_test_queue_data(assignments=[assignment_data])
        rts_data = make_test_runtime_session_data()
        plan_data = make_test_adaptive_plan_data()
        mediations_data = [make_test_mediation_data()]
        timeline_data = make_test_timeline_data()

        (tmp_path / "queue.json").write_text(json.dumps(queue_data))
        (tmp_path / "assignment.json").write_text(json.dumps(assignment_data))
        (tmp_path / "runtime.json").write_text(json.dumps(rts_data))
        (tmp_path / "plan.json").write_text(json.dumps(plan_data))
        (tmp_path / "mediations.json").write_text(json.dumps(mediations_data))
        (tmp_path / "timeline.json").write_text(json.dumps(timeline_data))

        result = main([
            "guided-session-view",
            "--queue", str(tmp_path / "queue.json"),
            "--assignment", str(tmp_path / "assignment.json"),
            "--runtime-session", str(tmp_path / "runtime.json"),
            "--adaptive-plan", str(tmp_path / "plan.json"),
            "--mediations", str(tmp_path / "mediations.json"),
            "--timeline", str(tmp_path / "timeline.json"),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["assignment"] is not None
        assert output["playback"] is not None
        assert output["adaptive_guidance"] is not None
        assert output["teacher_mediation"] is not None
        assert output["timeline"] is not None
