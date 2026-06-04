"""
Tests for workspace export CLI commands.

Sprint 37: Workspace Export & Share Package.
"""
from __future__ import annotations

import json
import tempfile
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
            ],
            "notes": [],
            "metadata": {},
            "version": "0.1",
        },
        "notes": ["Test note"],
        "metadata": {
            "teacher_internal_notes": "private",
            "source": "test",
        },
        "version": "0.1",
    }


def _create_narrative_json() -> dict:
    """Create narrative JSON."""
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
        "metadata": {"student_name": "John Doe"},
        "version": "0.1",
    }


def _create_timeline_json() -> dict:
    """Create timeline view JSON."""
    return {
        "student_id": "student_123",
        "generated_at": "2025-01-15T10:00:00Z",
        "total_events": 5,
        "diagnosis_groups": [],
        "timeline_events": [],
        "version": "0.1",
    }


class TestWorkspaceExportCommand:
    """Test workspace export CLI command."""

    def test_export_minimal(self, tmp_path: Path) -> None:
        """Test export with minimal workspace."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
        ])

        assert result == 0

    def test_export_with_pretty(self, tmp_path: Path, capsys) -> None:
        """Test export with pretty output."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "manifest" in output

    def test_export_output_structure(self, tmp_path: Path, capsys) -> None:
        """Test export output structure."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["manifest"]["export_id"].startswith("wexp_")
        assert output["manifest"]["format"] == "json"
        assert output["manifest"]["redaction_level"] == "none"
        assert "workspace" in output

    def test_export_with_narrative(self, tmp_path: Path, capsys) -> None:
        """Test export with narrative."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--narrative", str(narrative_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["narrative"] is not None

    def test_export_with_timeline(self, tmp_path: Path, capsys) -> None:
        """Test export with timeline."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        timeline_path = tmp_path / "timeline.json"
        timeline_path.write_text(json.dumps(_create_timeline_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--timeline", str(timeline_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["timeline"] is not None

    def test_export_with_all_inputs(self, tmp_path: Path, capsys) -> None:
        """Test export with all optional inputs."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        timeline_path = tmp_path / "timeline.json"
        timeline_path.write_text(json.dumps(_create_timeline_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--narrative", str(narrative_path),
            "--timeline", str(timeline_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["workspace"] is not None
        assert output["narrative"] is not None
        assert output["timeline"] is not None

    def test_export_redaction_none(self, tmp_path: Path, capsys) -> None:
        """Test export with no redaction."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--redaction", "none",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["manifest"]["redaction_level"] == "none"
        assert output["manifest"]["student_id"] == "student_123"

    def test_export_redaction_student_safe(self, tmp_path: Path, capsys) -> None:
        """Test export with student_safe redaction."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--redaction", "student_safe",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["manifest"]["redaction_level"] == "student_safe"
        assert output["manifest"]["student_id"] == "student_123"
        workspace_metadata = output["workspace"].get("metadata", {})
        assert "teacher_internal_notes" not in workspace_metadata

    def test_export_redaction_anonymized(self, tmp_path: Path, capsys) -> None:
        """Test export with anonymized redaction."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--redaction", "anonymized",
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["manifest"]["redaction_level"] == "anonymized"
        assert output["manifest"]["student_id"] is None
        assert output["manifest"]["runtime_session_id"] is None
        assert output["workspace"]["student_id"] is None

    def test_export_to_output_file(self, tmp_path: Path) -> None:
        """Test export to output file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "export.json"

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
        ])

        assert result == 0
        assert output_path.exists()

        output_data = json.loads(output_path.read_text())
        assert "manifest" in output_data
        assert "workspace" in output_data

    def test_export_to_output_file_pretty(self, tmp_path: Path) -> None:
        """Test export to output file with pretty format."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "export.json"

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
            "--pretty",
        ])

        assert result == 0
        content = output_path.read_text()
        assert "\n" in content

    def test_export_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test export overwrites existing output file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        output_path = tmp_path / "export.json"
        output_path.write_text('{"old": "data"}')

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--output", str(output_path),
        ])

        assert result == 0
        output_data = json.loads(output_path.read_text())
        assert "manifest" in output_data
        assert "old" not in output_data

    def test_export_missing_workspace_file(self) -> None:
        """Test export with missing workspace file."""
        result = main([
            "workspace", "export",
            "--workspace", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_export_missing_narrative_file(self, tmp_path: Path) -> None:
        """Test export with missing narrative file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--narrative", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_export_missing_timeline_file(self, tmp_path: Path) -> None:
        """Test export with missing timeline file."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_minimal_workspace_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--timeline", "/nonexistent/path.json",
        ])

        assert result == 1

    def test_export_invalid_json(self, tmp_path: Path) -> None:
        """Test export with invalid JSON."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text("invalid json")

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
        ])

        assert result == 1

    def test_export_included_sections(self, tmp_path: Path, capsys) -> None:
        """Test export includes sections list."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        narrative_path = tmp_path / "narrative.json"
        narrative_path.write_text(json.dumps(_create_narrative_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
            "--narrative", str(narrative_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        sections = output["manifest"]["included_sections"]
        assert "workspace" in sections
        assert "narrative" in sections

    def test_export_artifact_counts(self, tmp_path: Path, capsys) -> None:
        """Test export includes artifact counts."""
        workspace_path = tmp_path / "workspace.json"
        workspace_path.write_text(json.dumps(_create_workspace_with_layout_json()))

        result = main([
            "workspace", "export",
            "--workspace", str(workspace_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        counts = output["manifest"]["artifact_counts"]
        assert "workspace_panes_total" in counts
        assert counts["workspace_panes_total"] == 2
