"""
Tests for frontend interaction event store.

Sprint 39: Frontend Interaction Event Contract.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_spec.schemas.frontend_interaction import (
    FrontendInteractionEvent,
    FrontendInteractionType,
)
from sg_spec.schemas.frontend_state import (
    FrontendPaneState,
    WorkspaceFrontendState,
    WorkspaceNavigationState,
)

from sg_coach import (
    FRONTEND_INTERACTION_STORE_VERSION,
    FrontendInteractionStore,
)


class TestFrontendInteractionStoreAppend:
    """Test append_event functionality."""

    def test_append_creates_file(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_1",
        )

        store.append_event(event)

        assert store_path.exists()

    def test_append_writes_jsonl(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_1",
        )

        store.append_event(event)

        content = store_path.read_text()
        assert "fie_test123456ab" in content
        assert "select_pane" in content
        assert content.endswith("\n")

    def test_append_multiple_events(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for i in range(3):
            event = FrontendInteractionEvent(
                event_id=f"fie_event{i:010d}",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id=f"pane_{i}",
            )
            store.append_event(event)

        lines = store_path.read_text().strip().split("\n")
        assert len(lines) == 3


class TestFrontendInteractionStoreList:
    """Test list_events functionality."""

    def _create_events(self) -> list[FrontendInteractionEvent]:
        return [
            FrontendInteractionEvent(
                event_id="fie_event000001",
                workspace_id="swp_workspace_a",
                frontend_state_id="wfs_state_a",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id="pane_1",
            ),
            FrontendInteractionEvent(
                event_id="fie_event000002",
                workspace_id="swp_workspace_a",
                frontend_state_id="wfs_state_b",
                interaction_type=FrontendInteractionType.expand_pane,
                pane_id="pane_2",
            ),
            FrontendInteractionEvent(
                event_id="fie_event000003",
                workspace_id="swp_workspace_b",
                frontend_state_id="wfs_state_c",
                interaction_type=FrontendInteractionType.collapse_pane,
                pane_id="pane_3",
            ),
        ]

    def test_list_all_events(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events()

        assert len(events) == 3

    def test_list_empty_store(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        events = store.list_events()

        assert events == []

    def test_list_filter_by_workspace_id(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events(workspace_id="swp_workspace_a")

        assert len(events) == 2
        assert all(e.workspace_id == "swp_workspace_a" for e in events)

    def test_list_filter_by_frontend_state_id(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events(frontend_state_id="wfs_state_a")

        assert len(events) == 1
        assert events[0].frontend_state_id == "wfs_state_a"

    def test_list_filter_by_both(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events(
            workspace_id="swp_workspace_a",
            frontend_state_id="wfs_state_a",
        )

        assert len(events) == 1

    def test_list_no_matches(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events(workspace_id="swp_nonexistent")

        assert len(events) == 0

    def test_list_preserves_order(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for event in self._create_events():
            store.append_event(event)

        events = store.list_events()

        assert events[0].event_id == "fie_event000001"
        assert events[1].event_id == "fie_event000002"
        assert events[2].event_id == "fie_event000003"


class TestFrontendInteractionStoreReplay:
    """Test replay_events functionality."""

    def _create_state(self) -> WorkspaceFrontendState:
        pane_states = [
            FrontendPaneState(pane_id="pane_1", visible=True, expanded=True, selected=True, order_index=0),
            FrontendPaneState(pane_id="pane_2", visible=True, expanded=True, selected=False, order_index=1),
            FrontendPaneState(pane_id="pane_3", visible=True, expanded=True, selected=False, order_index=2),
        ]

        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=pane_states,
            navigation=WorkspaceNavigationState(active_pane_id="pane_1"),
        )

    def test_replay_empty_events(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)
        state = self._create_state()

        result = store.replay_events(state, [])

        assert result.navigation.active_pane_id == "pane_1"

    def test_replay_single_event(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)
        state = self._create_state()

        events = [
            FrontendInteractionEvent(
                event_id="fie_test123456ab",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id="pane_2",
            ),
        ]

        result = store.replay_events(state, events)

        assert result.navigation.active_pane_id == "pane_2"
        assert result.pane_states[1].selected is True

    def test_replay_multiple_events(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)
        state = self._create_state()

        events = [
            FrontendInteractionEvent(
                event_id="fie_event000001",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id="pane_2",
            ),
            FrontendInteractionEvent(
                event_id="fie_event000002",
                interaction_type=FrontendInteractionType.collapse_pane,
                pane_id="pane_2",
            ),
            FrontendInteractionEvent(
                event_id="fie_event000003",
                interaction_type=FrontendInteractionType.select_evidence,
                evidence_id="evidence_123",
            ),
        ]

        result = store.replay_events(state, events)

        assert result.navigation.active_pane_id == "pane_2"
        assert result.pane_states[1].expanded is False
        assert result.navigation.selected_evidence_id == "evidence_123"

    def test_replay_is_deterministic(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)
        state = self._create_state()

        events = [
            FrontendInteractionEvent(
                event_id="fie_event000001",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id="pane_3",
            ),
            FrontendInteractionEvent(
                event_id="fie_event000002",
                interaction_type=FrontendInteractionType.collapse_pane,
                pane_id="pane_1",
            ),
        ]

        result1 = store.replay_events(state, events)
        result2 = store.replay_events(state, events)

        assert result1.navigation.active_pane_id == result2.navigation.active_pane_id
        assert result1.pane_states[0].expanded == result2.pane_states[0].expanded

    def test_replay_does_not_mutate_initial_state(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)
        state = self._create_state()
        original_active = state.navigation.active_pane_id

        events = [
            FrontendInteractionEvent(
                event_id="fie_test123456ab",
                interaction_type=FrontendInteractionType.select_pane,
                pane_id="pane_3",
            ),
        ]

        store.replay_events(state, events)

        assert state.navigation.active_pane_id == original_active


class TestFrontendInteractionStoreClear:
    """Test clear functionality."""

    def test_clear_removes_file(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
        )
        store.append_event(event)
        assert store_path.exists()

        store.clear()

        assert not store_path.exists()

    def test_clear_nonexistent_is_safe(self, tmp_path: Path) -> None:
        store_path = tmp_path / "nonexistent.jsonl"
        store = FrontendInteractionStore(store_path)

        store.clear()


class TestFrontendInteractionStoreCount:
    """Test count functionality."""

    def test_count_empty_store(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        assert store.count() == 0

    def test_count_with_events(self, tmp_path: Path) -> None:
        store_path = tmp_path / "interactions.jsonl"
        store = FrontendInteractionStore(store_path)

        for i in range(5):
            event = FrontendInteractionEvent(
                event_id=f"fie_event{i:010d}",
                interaction_type=FrontendInteractionType.select_pane,
            )
            store.append_event(event)

        assert store.count() == 5


class TestVersionConstant:
    """Test version constant."""

    def test_store_version_is_string(self) -> None:
        assert isinstance(FRONTEND_INTERACTION_STORE_VERSION, str)

    def test_store_version_format(self) -> None:
        parts = FRONTEND_INTERACTION_STORE_VERSION.split(".")
        assert len(parts) == 3
