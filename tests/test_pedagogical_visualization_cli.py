"""
Tests for Pedagogical Visualization CLI commands.

Sprint 33: Pedagogical Timeline Visualization Layer.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_coach.cli import main


def make_test_ledger_entry_data(
    source: str = "runtime_review",
    severity: str = "informational",
    diagnosis_code: str | None = None,
) -> dict:
    """Create test ledger entry data."""
    entry = {
        "evidence_id": "ped_test123456",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "title": "Test Entry",
        "summary": "Test summary",
        "severity": severity,
        "provenance": [],
        "metadata": {},
    }
    if diagnosis_code:
        entry["diagnosis_code"] = diagnosis_code
    return entry


def make_test_ledger_data(
    student_id: str = "student_123",
    entries: list[dict] | None = None,
) -> dict:
    """Create test ledger data."""
    return {
        "student_id": student_id,
        "entries": entries or [],
        "version": "0.1",
    }


class TestTimelineViewCommand:
    """Tests for the timeline-view CLI command."""

    def test_empty_ledger(self, tmp_path: Path) -> None:
        ledger_path = tmp_path / "ledger.json"
        ledger_data = make_test_ledger_data(entries=[])
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

    def test_single_entry(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entry = make_test_ledger_entry_data()
        ledger_data = make_test_ledger_data(entries=[entry])
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total_events"] == 1

    def test_with_student_id_override(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entry = make_test_ledger_entry_data()
        ledger_data = make_test_ledger_data(
            student_id="original_id",
            entries=[entry],
        )
        ledger_path.write_text(json.dumps(ledger_data))

        result = main([
            "timeline-view",
            "--ledger", str(ledger_path),
            "--student-id", "override_id",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "override_id"

    def test_pretty_output(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entry = make_test_ledger_entry_data()
        ledger_data = make_test_ledger_data(entries=[entry])
        ledger_path.write_text(json.dumps(ledger_data))

        result = main([
            "timeline-view",
            "--ledger", str(ledger_path),
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        # Pretty output should be indented
        assert "  " in captured.out

    def test_multiple_entries_with_diagnosis(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entries = [
            make_test_ledger_entry_data(
                diagnosis_code="timing_grid_deviation",
            ),
            make_test_ledger_entry_data(
                diagnosis_code="timing_grid_deviation",
            ),
            make_test_ledger_entry_data(
                diagnosis_code="pitch_deviation",
            ),
        ]
        ledger_data = make_test_ledger_data(entries=entries)
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["total_events"] == 3
        assert len(output["diagnosis_groups"]) == 2

    def test_critical_severity_note(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entries = [
            make_test_ledger_entry_data(
                severity="critical",
                diagnosis_code="timing_grid_deviation",
            ),
        ]
        ledger_data = make_test_ledger_data(entries=entries)
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert any("critical" in note.lower() for note in output["notes"])

    def test_missing_ledger_file(self, tmp_path: Path) -> None:
        ledger_path = tmp_path / "nonexistent.json"
        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 1

    def test_invalid_ledger_json(self, tmp_path: Path) -> None:
        ledger_path = tmp_path / "invalid.json"
        ledger_path.write_text("not valid json")
        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 1

    def test_teacher_mediation_sources(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entries = [
            make_test_ledger_entry_data(source="teacher_scheduling_mediation"),
            make_test_ledger_entry_data(source="teacher_review"),
        ]
        ledger_data = make_test_ledger_data(entries=entries)
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Both should map to teacher_mediation event type
        assert all(
            e["event_type"] == "teacher_mediation"
            for e in output["timeline_events"]
        )

    def test_adaptive_scheduling_sources(self, tmp_path: Path, capsys) -> None:
        ledger_path = tmp_path / "ledger.json"
        entries = [
            make_test_ledger_entry_data(source="queue_event"),
            make_test_ledger_entry_data(source="practice_assignment"),
        ]
        ledger_data = make_test_ledger_data(entries=entries)
        ledger_path.write_text(json.dumps(ledger_data))

        result = main(["timeline-view", "--ledger", str(ledger_path)])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Both should map to adaptive_scheduling event type
        assert all(
            e["event_type"] == "adaptive_scheduling"
            for e in output["timeline_events"]
        )
