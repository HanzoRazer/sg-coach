"""
Tests for session_workspace CLI commands.

Sprint 36: Canonical Session Workspace Projection.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sg_coach.cli import main


def _create_minimal_session_view_json() -> dict:
    """Create minimal guided session view JSON."""
    return {
        "view_id": "gpv_test123456",
        "student_id": "student_123",
        "runtime_session_id": "rts_test123456",
        "generated_at": "2025-01-15T10:00:00Z",
        "assignment": None,
        "playback": None,
        "adaptive_guidance": None,
        "teacher_mediation": None,
        "notes": [],
        "metadata": {},
        "version": "0.1",
    }


def _create_full_session_view_json() -> dict:
    """Create full guided session view JSON with all components."""
    return {
        "view_id": "gpv_test123456",
        "student_id": "student_123",
        "runtime_session_id": "rts_test123456",
        "generated_at": "2025-01-15T10:00:00Z",
        "assignment": {
            "assignment_id": "assign_test123",
            "title": "Test Assignment",
            "assignment_type": "drill",
            "instructions_preview": "Practice this exercise",
            "runtime_active": True,
            "metadata": {},
            "version": "0.1",
        },
        "playback": {
            "runtime_session_id": "rts_test123456",
            "playback_available": True,
            "finding_overlay_count": 3,
            "active_finding_ids": [],
            "metadata": {},
            "version": "0.1",
        },
        "adaptive_guidance": {
            "recommendation_count": 2,
            "critical_priority_count": 1,
            "high_priority_count": 1,
            "active_recommendation_ids": [],
            "evidence_ids": [],
            "metadata": {},
            "version": "0.1",
        },
        "teacher_mediation": {
            "latest_mediation_id": "med_test123456",
            "mediation_count": 1,
            "rejected_count": 0,
            "modified_count": 0,
            "metadata": {},
            "version": "0.1",
        },
        "notes": [],
        "metadata": {},
        "version": "0.1",
    }


def _create_narrative_json() -> dict:
    """Create pedagogical narrative JSON."""
    return {
        "narrative_id": "pn_test12345678",
        "audience": "mixed",
        "generated_at": "2025-01-15T10:00:00Z",
        "title": "Test Narrative",
        "overview": "Test overview",
        "sections": [
            {
                "section_id": "pns_test123456",
                "title": "Test Section",
                "summary": "Test summary",
                "severity": "informational",
                "evidence_ids": [],
                "related_ids": [],
                "metadata": {},
                "version": "0.1",
            },
        ],
        "notes": [],
        "metadata": {},
        "version": "0.1",
    }


def _create_timeline_view_json() -> dict:
    """Create pedagogical timeline view JSON."""
    return {
        "student_id": "student_123",
        "generated_at": "2025-01-15T10:00:00Z",
        "total_events": 5,
        "diagnosis_groups": [],
        "timeline_events": [],
        "version": "0.1",
    }


class TestWorkspaceSessionCommand:
    """Test workspace session CLI command."""

    def test_workspace_session_minimal(self, tmp_path: Path) -> None:
        """Test workspace session with minimal inputs."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 0

    def test_workspace_session_with_pretty(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with pretty output."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "workspace_id" in output

    def test_workspace_session_output_structure(self, tmp_path: Path, capsys) -> None:
        """Test workspace session output structure."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["workspace_id"].startswith("swp_")
        assert output["student_id"] == "student_123"
        assert output["audience"] == "mixed"
        assert "layout" in output
        assert "notes" in output

    def test_workspace_session_with_narrative(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with narrative input."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--narrative", str(narrative_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["narrative"] is not None
        assert output["narrative"]["narrative_id"] == "pn_test12345678"

    def test_workspace_session_with_timeline(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with timeline input."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        timeline_path = tmp_path / "timeline.json"
        timeline_path.write_text(json.dumps(_create_timeline_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--timeline", str(timeline_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["timeline"] is not None
        assert output["timeline"]["total_events"] == 5

    def test_workspace_session_with_all_inputs(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with all optional inputs."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_full_session_view_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        timeline_path = tmp_path / "timeline.json"
        timeline_path.write_text(json.dumps(_create_timeline_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--narrative", str(narrative_path),
            "--timeline", str(timeline_path),
            "--audience", "teacher",
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["audience"] == "teacher"
        assert output["narrative"] is not None
        assert output["timeline"] is not None
        assert output["guided_session"] is not None

    def test_workspace_session_audience_student(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with student audience."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_full_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--audience", "student",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["audience"] == "student"
        mediation_pane = next(
            p for p in output["layout"]["panes"]
            if p["pane_type"] == "teacher_mediation"
        )
        assert mediation_pane["visible"] is False

    def test_workspace_session_audience_teacher(self, tmp_path: Path, capsys) -> None:
        """Test workspace session with teacher audience."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_full_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--audience", "teacher",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["audience"] == "teacher"
        mediation_pane = next(
            p for p in output["layout"]["panes"]
            if p["pane_type"] == "teacher_mediation"
        )
        assert mediation_pane["visible"] is True

    def test_workspace_session_layout_pane_count(self, tmp_path: Path, capsys) -> None:
        """Test workspace session layout has all pane types."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["layout"]["panes"]) == 6

    def test_workspace_session_panes_sorted(self, tmp_path: Path, capsys) -> None:
        """Test workspace session panes are sorted by order_index."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        order_indices = [p["order_index"] for p in output["layout"]["panes"]]
        assert order_indices == sorted(order_indices)

    def test_workspace_session_missing_session_view(self) -> None:
        """Test workspace session with missing session view file."""
        result = main([
            "workspace", "session",
            "--session-view", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_workspace_session_missing_narrative(self, tmp_path: Path) -> None:
        """Test workspace session with missing narrative file."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--narrative", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_workspace_session_missing_timeline(self, tmp_path: Path) -> None:
        """Test workspace session with missing timeline file."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--timeline", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_workspace_session_invalid_json(self, tmp_path: Path) -> None:
        """Test workspace session with invalid JSON."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text("invalid json")

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 1

    def test_workspace_session_notes_generation(self, tmp_path: Path, capsys) -> None:
        """Test workspace session generates notes."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_full_session_view_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        timeline_path = tmp_path / "timeline.json"
        timeline_path.write_text(json.dumps(_create_timeline_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
            "--narrative", str(narrative_path),
            "--timeline", str(timeline_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert isinstance(output["notes"], list)
        assert len(output["notes"]) > 0

    def test_workspace_session_metadata(self, tmp_path: Path, capsys) -> None:
        """Test workspace session includes metadata."""
        session_view_path = tmp_path / "session_view.json"
        session_view_path.write_text(json.dumps(_create_minimal_session_view_json()))

        result = main([
            "workspace", "session",
            "--session-view", str(session_view_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "metadata" in output
        assert "source_session_view_id" in output["metadata"]


class TestWorkspaceUnknownCommand:
    """Test workspace unknown subcommand."""

    def test_workspace_unknown_command(self, capsys) -> None:
        """Test workspace with unknown subcommand."""
        result = main(["workspace"])

        assert result == 1
