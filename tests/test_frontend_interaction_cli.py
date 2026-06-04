"""
Tests for frontend interaction event CLI commands.

Sprint 39: Frontend Interaction Event Contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sg_coach.cli import main


def _create_minimal_state_json() -> dict:
    """Create minimal frontend state JSON."""
    return {
        "frontend_state_id": "wfs_test123456",
        "workspace_id": "swp_workspace123",
        "generated_at": "2025-01-15T10:00:00Z",
        "pane_states": [
            {
                "pane_id": "pane_1",
                "visible": True,
                "expanded": True,
                "selected": True,
                "order_index": 0,
                "metadata": {},
                "version": "0.1",
            },
            {
                "pane_id": "pane_2",
                "visible": True,
                "expanded": True,
                "selected": False,
                "order_index": 1,
                "metadata": {},
                "version": "0.1",
            },
            {
                "pane_id": "pane_3",
                "visible": False,
                "expanded": True,
                "selected": False,
                "order_index": 2,
                "metadata": {},
                "version": "0.1",
            },
        ],
        "navigation": {
            "active_pane_id": "pane_1",
            "focused_section_id": None,
            "selected_evidence_id": None,
            "selected_timeline_event_id": None,
            "metadata": {},
            "version": "0.1",
        },
        "notes": [],
        "metadata": {},
        "version": "0.1",
    }


def _create_select_pane_event_json(pane_id: str = "pane_2") -> dict:
    """Create select_pane event JSON."""
    return {
        "event_id": "fie_test123456ab",
        "interaction_type": "select_pane",
        "pane_id": pane_id,
        "timestamp": "2025-01-15T10:01:00Z",
        "metadata": {},
        "version": "0.1",
    }


def _create_collapse_pane_event_json(pane_id: str = "pane_1") -> dict:
    """Create collapse_pane event JSON."""
    return {
        "event_id": "fie_collapse00001",
        "interaction_type": "collapse_pane",
        "pane_id": pane_id,
        "timestamp": "2025-01-15T10:02:00Z",
        "metadata": {},
        "version": "0.1",
    }


def _create_clear_selection_event_json() -> dict:
    """Create clear_selection event JSON."""
    return {
        "event_id": "fie_clear0000001",
        "interaction_type": "clear_selection",
        "timestamp": "2025-01-15T10:03:00Z",
        "metadata": {},
        "version": "0.1",
    }


class TestFrontendEventApplyCommand:
    """Test frontend-event apply CLI command."""

    def test_apply_select_pane(self, tmp_path: Path, capsys) -> None:
        """Test apply select_pane event."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json("pane_2")))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["navigation"]["active_pane_id"] == "pane_2"

    def test_apply_with_pretty(self, tmp_path: Path, capsys) -> None:
        """Test apply with pretty output."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json()))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_apply_collapse_pane(self, tmp_path: Path, capsys) -> None:
        """Test apply collapse_pane event."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_collapse_pane_event_json("pane_1")))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        pane_1 = next(p for p in output["pane_states"] if p["pane_id"] == "pane_1")
        assert pane_1["expanded"] is False

    def test_apply_preserves_frontend_state_id(self, tmp_path: Path, capsys) -> None:
        """Test apply preserves frontend_state_id."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json()))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["frontend_state_id"] == "wfs_test123456"

    def test_apply_updates_generated_at(self, tmp_path: Path, capsys) -> None:
        """Test apply updates generated_at."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json()))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "2025-01-15T10:01:00" in output["generated_at"]

    def test_apply_hidden_pane_adds_warning(self, tmp_path: Path, capsys) -> None:
        """Test apply to hidden pane adds warning."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json("pane_3")))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "interaction_warnings" in output["metadata"]
        assert output["metadata"]["interaction_warnings"][0]["warning"] == "pane_not_visible"

    def test_apply_missing_state_file(self, tmp_path: Path) -> None:
        """Test apply with missing state file."""
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json()))

        result = main([
            "frontend-event", "apply",
            "--state", "/nonexistent/state.json",
            "--event", str(event_path),
        ])

        assert result == 1

    def test_apply_missing_event_file(self, tmp_path: Path) -> None:
        """Test apply with missing event file."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", "/nonexistent/event.json",
        ])

        assert result == 1

    def test_apply_invalid_state_json(self, tmp_path: Path) -> None:
        """Test apply with invalid state JSON."""
        state_path = tmp_path / "state.json"
        state_path.write_text("invalid json")

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(_create_select_pane_event_json()))

        result = main([
            "frontend-event", "apply",
            "--state", str(state_path),
            "--event", str(event_path),
        ])

        assert result == 1


class TestFrontendEventReplayCommand:
    """Test frontend-event replay CLI command."""

    def test_replay_empty_events(self, tmp_path: Path, capsys) -> None:
        """Test replay with empty events file."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        events_path = tmp_path / "events.jsonl"
        events_path.write_text("")

        result = main([
            "frontend-event", "replay",
            "--state", str(state_path),
            "--events", str(events_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["navigation"]["active_pane_id"] == "pane_1"

    def test_replay_single_event(self, tmp_path: Path, capsys) -> None:
        """Test replay with single event."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        events_path = tmp_path / "events.jsonl"
        events_path.write_text(json.dumps(_create_select_pane_event_json("pane_2")) + "\n")

        result = main([
            "frontend-event", "replay",
            "--state", str(state_path),
            "--events", str(events_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["navigation"]["active_pane_id"] == "pane_2"

    def test_replay_multiple_events(self, tmp_path: Path, capsys) -> None:
        """Test replay with multiple events."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        events = [
            _create_select_pane_event_json("pane_2"),
            _create_collapse_pane_event_json("pane_2"),
        ]
        events_path = tmp_path / "events.jsonl"
        events_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")

        result = main([
            "frontend-event", "replay",
            "--state", str(state_path),
            "--events", str(events_path),
        ])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["navigation"]["active_pane_id"] == "pane_2"
        pane_2 = next(p for p in output["pane_states"] if p["pane_id"] == "pane_2")
        assert pane_2["expanded"] is False

    def test_replay_with_pretty(self, tmp_path: Path, capsys) -> None:
        """Test replay with pretty output."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        events_path = tmp_path / "events.jsonl"
        events_path.write_text(json.dumps(_create_select_pane_event_json()) + "\n")

        result = main([
            "frontend-event", "replay",
            "--state", str(state_path),
            "--events", str(events_path),
            "--pretty",
        ])

        assert result == 0
        captured = capsys.readouterr()
        assert "\n" in captured.out

    def test_replay_missing_state_file(self, tmp_path: Path) -> None:
        """Test replay with missing state file."""
        events_path = tmp_path / "events.jsonl"
        events_path.write_text("")

        result = main([
            "frontend-event", "replay",
            "--state", "/nonexistent/state.json",
            "--events", str(events_path),
        ])

        assert result == 1

    def test_replay_missing_events_file(self, tmp_path: Path) -> None:
        """Test replay with missing events file."""
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(_create_minimal_state_json()))

        result = main([
            "frontend-event", "replay",
            "--state", str(state_path),
            "--events", "/nonexistent/events.jsonl",
        ])

        assert result == 1


class TestFrontendEventUnknownCommand:
    """Test unknown frontend-event command."""

    def test_unknown_command(self, capsys) -> None:
        """Test unknown subcommand exits with error."""
        with pytest.raises(SystemExit) as exc_info:
            main([
                "frontend-event", "unknown",
            ])

        assert exc_info.value.code == 2
