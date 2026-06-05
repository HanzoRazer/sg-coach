"""
Tests for frontend interaction event engine.

Sprint 39: Frontend Interaction Event Contract.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
    FRONTEND_INTERACTION_ENGINE_VERSION,
    generate_event_id,
    apply_frontend_interaction,
)


class TestGenerateEventId:
    """Test generate_event_id function."""

    def test_starts_with_fie(self) -> None:
        event_id = generate_event_id()
        assert event_id.startswith("fie_")

    def test_correct_length(self) -> None:
        event_id = generate_event_id()
        assert len(event_id) == 16

    def test_unique(self) -> None:
        ids = [generate_event_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestApplySelectPane:
    """Test select_pane interaction."""

    def _create_state(
        self,
        pane_ids: list[str] | None = None,
        visible_ids: list[str] | None = None,
        selected_id: str | None = None,
    ) -> WorkspaceFrontendState:
        if pane_ids is None:
            pane_ids = ["pane_1", "pane_2", "pane_3"]
        if visible_ids is None:
            visible_ids = pane_ids

        pane_states = []
        for i, pane_id in enumerate(pane_ids):
            pane_states.append(
                FrontendPaneState(
                    pane_id=pane_id,
                    visible=pane_id in visible_ids,
                    expanded=True,
                    selected=pane_id == selected_id,
                    order_index=i,
                )
            )

        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            workspace_id="swp_workspace123",
            pane_states=pane_states,
            navigation=WorkspaceNavigationState(
                active_pane_id=selected_id,
            ),
        )

    def test_select_pane_updates_selected(self) -> None:
        state = self._create_state(selected_id="pane_1")
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_2",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[0].selected is False
        assert result.pane_states[1].selected is True
        assert result.pane_states[2].selected is False

    def test_select_pane_updates_active_pane_id(self) -> None:
        state = self._create_state(selected_id="pane_1")
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_2",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.active_pane_id == "pane_2"

    def test_select_pane_clears_previous_selection(self) -> None:
        state = self._create_state(selected_id="pane_1")
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_3",
        )

        result = apply_frontend_interaction(state=state, event=event)

        selected_count = sum(1 for p in result.pane_states if p.selected)
        assert selected_count == 1

    def test_select_hidden_pane_returns_warning(self) -> None:
        state = self._create_state(visible_ids=["pane_1", "pane_2"])
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_3",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        warnings = result.metadata["interaction_warnings"]
        assert len(warnings) == 1
        assert warnings[0]["warning"] == "pane_not_visible"

    def test_select_unknown_pane_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="unknown_pane",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        warnings = result.metadata["interaction_warnings"]
        assert warnings[0]["warning"] == "pane_id_not_found"
        assert warnings[0]["target_id"] == "unknown_pane"

    def test_select_pane_without_pane_id_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id=None,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        warnings = result.metadata["interaction_warnings"]
        assert warnings[0]["warning"] == "pane_id_required"

    def test_select_pane_preserves_frontend_state_id(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_2",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.frontend_state_id == state.frontend_state_id

    def test_select_pane_updates_generated_at(self) -> None:
        state = self._create_state()
        event_ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_2",
            timestamp=event_ts,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.generated_at == event_ts

    def test_select_pane_does_not_mutate_source(self) -> None:
        state = self._create_state(selected_id="pane_1")
        original_selected = state.pane_states[0].selected
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="pane_2",
        )

        apply_frontend_interaction(state=state, event=event)

        assert state.pane_states[0].selected == original_selected


class TestApplyExpandPane:
    """Test expand_pane interaction."""

    def _create_state(self, expanded_ids: list[str] | None = None) -> WorkspaceFrontendState:
        pane_ids = ["pane_1", "pane_2", "pane_3"]
        if expanded_ids is None:
            expanded_ids = pane_ids

        pane_states = []
        for i, pane_id in enumerate(pane_ids):
            pane_states.append(
                FrontendPaneState(
                    pane_id=pane_id,
                    visible=True,
                    expanded=pane_id in expanded_ids,
                    selected=i == 0,
                    order_index=i,
                )
            )

        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=pane_states,
            navigation=WorkspaceNavigationState(active_pane_id="pane_1"),
        )

    def test_expand_pane_sets_expanded_true(self) -> None:
        state = self._create_state(expanded_ids=["pane_1", "pane_3"])
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.expand_pane,
            pane_id="pane_2",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[1].expanded is True

    def test_expand_already_expanded_is_idempotent(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.expand_pane,
            pane_id="pane_1",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[0].expanded is True

    def test_expand_unknown_pane_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.expand_pane,
            pane_id="unknown",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        assert result.metadata["interaction_warnings"][0]["warning"] == "pane_id_not_found"


class TestApplyCollapsePane:
    """Test collapse_pane interaction."""

    def _create_state(self, selected_id: str = "pane_1") -> WorkspaceFrontendState:
        pane_states = [
            FrontendPaneState(pane_id="pane_1", visible=True, expanded=True, selected=selected_id == "pane_1", order_index=0),
            FrontendPaneState(pane_id="pane_2", visible=True, expanded=True, selected=selected_id == "pane_2", order_index=1),
        ]

        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=pane_states,
            navigation=WorkspaceNavigationState(active_pane_id=selected_id),
        )

    def test_collapse_pane_sets_expanded_false(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.collapse_pane,
            pane_id="pane_1",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[0].expanded is False

    def test_collapse_selected_pane_keeps_selected(self) -> None:
        state = self._create_state(selected_id="pane_1")
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.collapse_pane,
            pane_id="pane_1",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[0].expanded is False
        assert result.pane_states[0].selected is True
        assert result.navigation.active_pane_id == "pane_1"

    def test_collapse_unknown_pane_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.collapse_pane,
            pane_id="unknown",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata


class TestApplySelectEvidence:
    """Test select_evidence interaction."""

    def _create_state(self) -> WorkspaceFrontendState:
        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=[],
            navigation=WorkspaceNavigationState(
                active_pane_id="pane_1",
                selected_evidence_id=None,
            ),
        )

    def test_select_evidence_sets_id(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_evidence,
            evidence_id="evidence_123",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_evidence_id == "evidence_123"

    def test_select_evidence_clears_previous(self) -> None:
        state = self._create_state()
        state = state.model_copy(
            update={"navigation": state.navigation.model_copy(update={"selected_evidence_id": "old_evidence"})}
        )
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_evidence,
            evidence_id="new_evidence",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_evidence_id == "new_evidence"

    def test_select_evidence_with_none_clears(self) -> None:
        state = self._create_state()
        state = state.model_copy(
            update={"navigation": state.navigation.model_copy(update={"selected_evidence_id": "old_evidence"})}
        )
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_evidence,
            evidence_id=None,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_evidence_id is None


class TestApplySelectTimelineEvent:
    """Test select_timeline_event interaction."""

    def _create_state(self) -> WorkspaceFrontendState:
        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=[],
            navigation=WorkspaceNavigationState(
                active_pane_id="pane_1",
                selected_timeline_event_id=None,
            ),
        )

    def test_select_timeline_event_sets_id(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.select_timeline_event,
            timeline_event_id="ptv_event123",
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_timeline_event_id == "ptv_event123"


class TestApplyClearSelection:
    """Test clear_selection interaction."""

    def _create_state(self) -> WorkspaceFrontendState:
        pane_states = [
            FrontendPaneState(pane_id="pane_1", visible=True, expanded=True, selected=True, order_index=0),
        ]
        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=pane_states,
            navigation=WorkspaceNavigationState(
                active_pane_id="pane_1",
                focused_section_id="section_123",
                selected_evidence_id="evidence_123",
                selected_timeline_event_id="ptv_event123",
            ),
        )

    def test_clear_selection_clears_focused_section(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.focused_section_id is None

    def test_clear_selection_clears_evidence(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_evidence_id is None

    def test_clear_selection_clears_timeline_event(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.selected_timeline_event_id is None

    def test_clear_selection_preserves_active_pane(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.navigation.active_pane_id == "pane_1"

    def test_clear_selection_preserves_pane_selected(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert result.pane_states[0].selected is True


class TestIdMismatchValidation:
    """Test ID mismatch soft validation."""

    def _create_state(self) -> WorkspaceFrontendState:
        return WorkspaceFrontendState(
            frontend_state_id="wfs_correct123",
            workspace_id="swp_correct123",
            pane_states=[],
            navigation=WorkspaceNavigationState(),
        )

    def test_frontend_state_id_mismatch_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            frontend_state_id="wfs_wrong123456",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        warnings = result.metadata["interaction_warnings"]
        assert warnings[0]["warning"] == "frontend_state_id_mismatch"

    def test_workspace_id_mismatch_returns_warning(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            workspace_id="swp_wrong123456",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" in result.metadata
        warnings = result.metadata["interaction_warnings"]
        assert warnings[0]["warning"] == "workspace_id_mismatch"

    def test_none_ids_do_not_block(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            frontend_state_id=None,
            workspace_id=None,
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" not in result.metadata or len(result.metadata.get("interaction_warnings", [])) == 0

    def test_matching_ids_succeed(self) -> None:
        state = self._create_state()
        event = FrontendInteractionEvent(
            event_id="fie_test123456ab",
            frontend_state_id="wfs_correct123",
            workspace_id="swp_correct123",
            interaction_type=FrontendInteractionType.clear_selection,
        )

        result = apply_frontend_interaction(state=state, event=event)

        assert "interaction_warnings" not in result.metadata or len(result.metadata.get("interaction_warnings", [])) == 0


class TestWarningAccumulation:
    """Test that warnings accumulate correctly."""

    def _create_state_with_existing_warning(self) -> WorkspaceFrontendState:
        return WorkspaceFrontendState(
            frontend_state_id="wfs_test123456",
            pane_states=[],
            navigation=WorkspaceNavigationState(),
            metadata={
                "interaction_warnings": [
                    {"event_id": "old_event", "interaction_type": "select_pane", "warning": "old_warning"}
                ]
            },
        )

    def test_warnings_append_to_existing(self) -> None:
        state = self._create_state_with_existing_warning()
        event = FrontendInteractionEvent(
            event_id="fie_new123456ab",
            interaction_type=FrontendInteractionType.select_pane,
            pane_id="unknown",
        )

        result = apply_frontend_interaction(state=state, event=event)

        warnings = result.metadata["interaction_warnings"]
        assert len(warnings) == 2
        assert warnings[0]["event_id"] == "old_event"
        assert warnings[1]["event_id"] == "fie_new123456ab"


class TestVersionConstant:
    """Test version constant."""

    def test_engine_version_is_string(self) -> None:
        assert isinstance(FRONTEND_INTERACTION_ENGINE_VERSION, str)

    def test_engine_version_format(self) -> None:
        parts = FRONTEND_INTERACTION_ENGINE_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
