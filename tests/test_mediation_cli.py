"""
Tests for Teacher Scheduling Mediation CLI.

Sprint 31: Teacher-Adaptive Scheduling Mediation.
"""
import json
from datetime import datetime, timezone

import pytest

from sg_coach.cli import main


def make_test_recommendation(
    recommendation_id: str = "asr_test123",
    diagnosis_code: str = "timing_grid_deviation",
    priority_adjustment: str = "increase",
) -> dict:
    """Create a test recommendation dict."""
    return {
        "recommendation_id": recommendation_id,
        "assignment_id": None,
        "diagnosis_code": diagnosis_code,
        "priority_adjustment": priority_adjustment,
        "recommended_priority": "high",
        "recommended_repetition_count": 3,
        "recommended_delay_days": None,
        "reasons": ["worsening_trend"],
        "evidence_ids": ["ped_001"],
        "rationale": "Test rationale",
        "metadata": {},
    }


def make_test_mediation(
    mediation_id: str = "tsm_test123",
    recommendation_id: str = "asr_test123",
    teacher_id: str = "teacher_001",
    action: str = "approve",
    rationale: str | None = None,
) -> dict:
    """Create a test mediation dict."""
    return {
        "id": mediation_id,
        "recommendation_id": recommendation_id,
        "teacher_id": teacher_id,
        "student_id": None,
        "diagnosis_code": "timing_grid_deviation",
        "assignment_id": None,
        "action": action,
        "override": None,
        "rationale": rationale,
        "prior_mediation_id": None,
        "teacher_review_id": None,
        "metadata": {
            "original_priority_adjustment": "increase",
            "original_recommended_priority": "high",
            "original_recommended_repetition_count": 3,
            "original_recommended_delay_days": None,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "0.1",
    }


def make_test_queue(
    assignments: list[dict] | None = None,
) -> dict:
    """Create a test queue dict."""
    return {
        "id": "queue_test123",
        "student_id": "student_123",
        "assignments": assignments or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_test_queue_assignment(
    assignment_id: str = "spa_test123",
    diagnosis_code: str = "timing_grid_deviation",
    priority: str = "normal",
) -> dict:
    """Create a test queue assignment dict."""
    return {
        "scheduled_id": f"sched_{assignment_id}",
        "queue_id": "queue_test123",
        "assignment_id": assignment_id,
        "student_id": "student_123",
        "diagnosis_code": diagnosis_code,
        "title": "Test Assignment",
        "status": "queued",
        "priority": priority,
        "scheduled_order": 1,
        "estimated_minutes": 15,
        "scheduled_for": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "deferred_until": None,
        "metadata": {},
        "version": "0.1",
    }


class TestMediationSubmitCommand:
    """Tests for mediation submit CLI command."""

    def test_creates_approve_mediation(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "approve",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["action"] == "approve"
        assert output["teacher_id"] == "teacher_001"
        assert output["recommendation_id"] == "asr_test123"
        assert output["id"].startswith("tsm_")

    def test_creates_reject_mediation_with_rationale(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "reject",
            "--rationale", "Student needs different approach",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["action"] == "reject"
        assert output["rationale"] == "Student needs different approach"

    def test_creates_defer_mediation_with_rationale(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "defer",
            "--rationale", "Need to discuss with student",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["action"] == "defer"

    def test_creates_approve_modified_with_override(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "approve_modified",
            "--rationale", "Adjusted for student needs",
            "--override-priority", "critical",
            "--override-repetition", "5",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["action"] == "approve_modified"
        assert output["override"]["recommended_priority"] == "critical"
        assert output["override"]["recommended_repetition_count"] == 5

    def test_includes_student_id(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "approve",
            "--student-id", "student_xyz",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_xyz"

    def test_pretty_output(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "approve",
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_recommendation_file(self, tmp_path, capsys):
        result = main([
            "mediation", "submit",
            "--recommendation", str(tmp_path / "nonexistent.json"),
            "--teacher-id", "teacher_001",
            "--action", "approve",
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_stores_original_values_in_metadata(self, tmp_path, capsys):
        rec_file = tmp_path / "recommendation.json"
        rec = make_test_recommendation()
        rec_file.write_text(json.dumps(rec))

        result = main([
            "mediation", "submit",
            "--recommendation", str(rec_file),
            "--teacher-id", "teacher_001",
            "--action", "approve",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "original_priority_adjustment" in output["metadata"]
        assert output["metadata"]["original_priority_adjustment"] == "increase"


class TestMediationApplyCommand:
    """Tests for mediation apply CLI command."""

    def test_applies_approve_mediation_to_queue(self, tmp_path, capsys):
        rec = make_test_recommendation(diagnosis_code="timing_grid_deviation")
        rec_file = tmp_path / "recommendation.json"
        rec_file.write_text(json.dumps(rec))

        mediation = make_test_mediation(action="approve")
        med_file = tmp_path / "mediation.json"
        med_file.write_text(json.dumps(mediation))

        queue = make_test_queue([
            make_test_queue_assignment(
                diagnosis_code="timing_grid_deviation",
                priority="normal",
            ),
        ])
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue))

        result = main([
            "mediation", "apply",
            "--mediation", str(med_file),
            "--recommendation", str(rec_file),
            "--queue", str(queue_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["assignments"]) == 1
        assert output["assignments"][0]["priority"] == "high"

    def test_reject_mediation_adds_metadata_no_priority_change(self, tmp_path, capsys):
        rec = make_test_recommendation(diagnosis_code="timing_grid_deviation")
        rec_file = tmp_path / "recommendation.json"
        rec_file.write_text(json.dumps(rec))

        mediation = make_test_mediation(
            action="reject",
            rationale="Not appropriate",
        )
        med_file = tmp_path / "mediation.json"
        med_file.write_text(json.dumps(mediation))

        queue = make_test_queue([
            make_test_queue_assignment(
                diagnosis_code="timing_grid_deviation",
                priority="normal",
            ),
        ])
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue))

        result = main([
            "mediation", "apply",
            "--mediation", str(med_file),
            "--recommendation", str(rec_file),
            "--queue", str(queue_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["assignments"][0]["priority"] == "normal"
        assert "teacher_scheduling_mediation" in output["assignments"][0]["metadata"]
        assert output["assignments"][0]["metadata"]["teacher_scheduling_mediation"]["mediation_action"] == "reject"

    def test_pretty_output(self, tmp_path, capsys):
        rec = make_test_recommendation()
        rec_file = tmp_path / "recommendation.json"
        rec_file.write_text(json.dumps(rec))

        mediation = make_test_mediation()
        med_file = tmp_path / "mediation.json"
        med_file.write_text(json.dumps(mediation))

        queue = make_test_queue([])
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue))

        result = main([
            "mediation", "apply",
            "--mediation", str(med_file),
            "--recommendation", str(rec_file),
            "--queue", str(queue_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_mediation_file(self, tmp_path, capsys):
        rec = make_test_recommendation()
        rec_file = tmp_path / "recommendation.json"
        rec_file.write_text(json.dumps(rec))

        queue = make_test_queue([])
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue))

        result = main([
            "mediation", "apply",
            "--mediation", str(tmp_path / "nonexistent.json"),
            "--recommendation", str(rec_file),
            "--queue", str(queue_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_recommendation_file(self, tmp_path, capsys):
        mediation = make_test_mediation()
        med_file = tmp_path / "mediation.json"
        med_file.write_text(json.dumps(mediation))

        queue = make_test_queue([])
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue))

        result = main([
            "mediation", "apply",
            "--mediation", str(med_file),
            "--recommendation", str(tmp_path / "nonexistent.json"),
            "--queue", str(queue_file),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_queue_file(self, tmp_path, capsys):
        rec = make_test_recommendation()
        rec_file = tmp_path / "recommendation.json"
        rec_file.write_text(json.dumps(rec))

        mediation = make_test_mediation()
        med_file = tmp_path / "mediation.json"
        med_file.write_text(json.dumps(mediation))

        result = main([
            "mediation", "apply",
            "--mediation", str(med_file),
            "--recommendation", str(rec_file),
            "--queue", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err
