"""
Tests for Adaptive Scheduling CLI.

Sprint 30: Evidence-Driven Adaptive Scheduling.
"""
import json
from datetime import datetime, timezone

import pytest

from sg_coach.cli import main


def make_test_entry(
    evidence_id: str = "ped_test123",
    source: str = "longitudinal_review",
    diagnosis_code: str | None = "timing_grid_deviation",
    metadata: dict | None = None,
) -> dict:
    """Create a test evidence entry dict."""
    return {
        "evidence_id": evidence_id,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "diagnosis_code": diagnosis_code,
        "title": "Test entry",
        "summary": "Test summary",
        "metadata": metadata or {},
    }


def make_test_ledger(
    entries: list[dict] | None = None,
    student_id: str | None = None,
) -> dict:
    """Create a test ledger dict."""
    return {
        "student_id": student_id,
        "entries": entries or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
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


class TestAdaptiveSchedulingCommand:
    """Tests for adaptive-scheduling CLI command."""

    def test_generates_plan_from_ledger(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        entries = [
            make_test_entry(
                evidence_id="ped_001",
                source="longitudinal_review",
                diagnosis_code="timing_grid_deviation",
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_test_ledger(entries)
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "recommendations" in output
        assert "source_evidence_count" in output
        assert output["source_evidence_count"] == 1

    def test_generates_recommendations_for_worsening_trend(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        entries = [
            make_test_entry(
                evidence_id="ped_001",
                source="longitudinal_review",
                diagnosis_code="timing_grid_deviation",
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_test_ledger(entries)
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["recommendations"]) == 1
        assert output["recommendations"][0]["priority_adjustment"] == "increase"

    def test_empty_ledger_produces_empty_plan(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["recommendations"] == []
        assert output["source_evidence_count"] == 0

    def test_uses_student_id_from_flag(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
            "--student-id", "student_explicit",
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_explicit"

    def test_uses_student_id_from_ledger(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([], student_id="student_from_ledger")
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_from_ledger"

    def test_accepts_queue_file(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        queue_file = tmp_path / "queue.json"
        queue = make_test_queue([])
        queue_file.write_text(json.dumps(queue))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
            "--queue", str(queue_file),
        ])

        assert result == 0

    def test_pretty_output(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
            "--pretty",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out
        assert "  " in captured.out

    def test_error_missing_ledger_file(self, tmp_path, capsys):
        result = main([
            "adaptive-scheduling",
            "--ledger", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_error_missing_queue_file(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
            "--queue", str(tmp_path / "nonexistent.json"),
        ])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_generated_at_populated(self, tmp_path, capsys):
        ledger_file = tmp_path / "ledger.json"
        ledger = make_test_ledger([])
        ledger_file.write_text(json.dumps(ledger))

        result = main([
            "adaptive-scheduling",
            "--ledger", str(ledger_file),
        ])

        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "generated_at" in output
