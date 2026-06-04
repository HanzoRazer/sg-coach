"""
Tests for frontend state CLI commands.

Sprint 38: Canonical Frontend State Projection.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sg_coach.cli import main


def _create_minimal_workspace_json() -> dict:
    """Create minimal workspace JSON."""
    return {
        "workspace_id": "swp_test123456",
        "audience": "mixed",
        "generated_at": "2025-01-15T10:00:00Z",
        "guided_session": None,
        "narrative": None,
        "timeline": None,
        "layout": None,
        "notes": [],
        "metadata": {},
        "version": "0.1",
    }


def _create_workspace_with_layout_json() -> dict:
    """Create workspace with layout JSON."""
    return {
        "workspace_id": "swp_test123456",
        "student_id": "student_123",
        "runtime_session_id": "rts_test123456",
        "audience": "mixed",
        "generated_at": "2025-01-15T10:00:00Z",
        "guided_session": None,
        "narrative": None,
        "timeline": None,
        "layout": {
            "layout_id": "swl_test123456",
            "audience": "mixed",
            "panes": [
                {
                    "pane_id": "swpane_001",
                    "pane_type": "assignment",
                    "title": "Assignment",
                    "visible": True,
                    "order_index": 0,
                    "metadata": {},
                    "version": "0.1",
                },
                {
                    "pane_id": "swpane_002",
                    "pane_type": "playback",
                    "title": "Playback",
                    "visible": True,
                    "order_index": 1,
                    "metadata": {},
                    "version": "0.1",
                },
                {
                    "pane_id": "swpane_003",
                    "pane_type": "narrative",
                    "title": "Narrative",
                    "visible": False,
                    "order_index": 2,
                    "metadata": {},
                    "version": "0.1",
                },
            ],
            "notes": [],
            "metadata": {},
            "version": "0.1",
        },
        "notes": ["Test note"],
        "metadata": {
            "source": "test",
        },
        "version": "0.1",
    }


class TestWorkspaceFrontendStateCommand:
    """Test workspace frontend-state CLI command."""

    def test_frontend_state_minimal(self, tmp_path: Path) -> None:
        """Test frontend-state with minimal workspace."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0

    def test_frontend_state_with_pretty(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state with pretty output."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "frontend_state_id" in output

    def test_frontend_state_output_structure(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state output structure."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["frontend_state_id"].startswith("wfs_")
        assert output["workspace_id"] == "swp_test123456"
        assert "pane_states" in output
        assert "navigation" in output
        assert "notes" in output

    def test_frontend_state_with_layout(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state with layout."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["pane_states"]) == 3

    def test_frontend_state_pane_states(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state pane states."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        pane_states = output["pane_states"]
        assert pane_states[0]["pane_id"] == "swpane_001"
        assert pane_states[0]["visible"] is True
        assert pane_states[0]["selected"] is True
        assert pane_states[0]["expanded"] is True

        assert pane_states[1]["pane_id"] == "swpane_002"
        assert pane_states[1]["selected"] is False

        assert pane_states[2]["pane_id"] == "swpane_003"
        assert pane_states[2]["visible"] is False
        assert pane_states[2]["selected"] is False

    def test_frontend_state_navigation(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state navigation state."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        navigation = output["navigation"]
        assert navigation["active_pane_id"] == "swpane_001"
        assert navigation["focused_section_id"] is None
        assert navigation["selected_evidence_id"] is None

    def test_frontend_state_notes(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state notes."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["notes"]) > 0
        assert any("visible" in note for note in output["notes"])

    def test_frontend_state_to_output_file(self, tmp_path: Path) -> None:
        """Test frontend-state to output file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "frontend_state.json"

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
        ])

        assert result == 0
        assert output_path.exists()

        output_data = json.loads(output_path.read_text())
        assert "frontend_state_id" in output_data
        assert "pane_states" in output_data

    def test_frontend_state_to_output_file_pretty(self, tmp_path: Path) -> None:
        """Test frontend-state to output file with pretty format."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "frontend_state.json"

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
            "--pretty",
        ])

        assert result == 0
        content = output_path.read_text()
        assert "\n" in content

    def test_frontend_state_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test frontend-state overwrites existing output file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "frontend_state.json"
        output_path.write_text('{"old": "data"}')

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
        ])

        assert result == 0
        output_data = json.loads(output_path.read_text())
        assert "frontend_state_id" in output_data
        assert "old" not in output_data

    def test_frontend_state_missing_workspace_file(self) -> None:
        """Test frontend-state with missing workspace file."""
        result = main([
            "workspace", "frontend-state",
            "--workspace", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_frontend_state_invalid_json(self, tmp_path: Path) -> None:
        """Test frontend-state with invalid JSON."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text("invalid json")

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 1

    def test_frontend_state_metadata(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state metadata."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["metadata"]["source_workspace_id"] == "swp_test123456"
        assert output["metadata"]["source_student_id"] == "student_123"

    def test_frontend_state_version(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state version."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["version"] == "0.1"

    def test_frontend_state_generated_at(self, tmp_path: Path, capsys) -> None:
        """Test frontend-state generated_at field."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "frontend-state",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "generated_at" in output
