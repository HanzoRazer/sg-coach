"""
Tests for frontend state projection engine.

Sprint 38: Canonical Frontend State Projection.
"""
from __future__ import annotations

import pytest

from sg_spec.schemas.frontend_state import (
    FRONTEND_STATE_VERSION,
    FrontendPaneState,
    WorkspaceFrontendState,
    WorkspaceNavigationState,
)
from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.practice_assignment import PracticeAssignmentType
from sg_spec.schemas.pedagogical_narrative import (
    NarrativeAudience,
    NarrativeSeverity,
    NarrativeSection,
    PedagogicalNarrative,
)
from sg_spec.schemas.pedagogical_visualization import (
    PedagogicalTimelineView,
)
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspaceAudience,
    WorkspaceLayout,
    WorkspacePane,
    WorkspacePaneType,
)

from sg_coach import (
    FRONTEND_STATE_ENGINE_VERSION,
    build_frontend_pane_states,
    build_workspace_navigation_state,
    build_workspace_frontend_state,
)


class TestBuildFrontendPaneStates:
    """Test build_frontend_pane_states function."""

    def _create_pane(
        self,
        pane_type: WorkspacePaneType,
        order_index: int,
        visible: bool = True,
        pane_id: str | None = None,
    ) -> WorkspacePane:
        return WorkspacePane(
            pane_id=pane_id or f"swpane_{pane_type.value}",
            pane_type=pane_type,
            title=pane_type.value.title(),
            visible=visible,
            order_index=order_index,
            summary=f"{pane_type.value} summary",
        )

    def test_empty_panes(self) -> None:
        result = build_frontend_pane_states(panes=[])

        assert result == []

    def test_single_visible_pane(self) -> None:
        pane = self._create_pane(WorkspacePaneType.assignment, 0, visible=True)

        result = build_frontend_pane_states(panes=[pane])

        assert len(result) == 1
        assert result[0].pane_id == pane.pane_id
        assert result[0].visible is True
        assert result[0].expanded is True
        assert result[0].selected is True
        assert result[0].order_index == 0

    def test_single_hidden_pane(self) -> None:
        pane = self._create_pane(WorkspacePaneType.assignment, 0, visible=False)

        result = build_frontend_pane_states(panes=[pane])

        assert len(result) == 1
        assert result[0].pane_id == pane.pane_id
        assert result[0].visible is False
        assert result[0].expanded is True
        assert result[0].selected is False

    def test_multiple_panes_first_visible_selected(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
            self._create_pane(WorkspacePaneType.playback, 1, visible=True),
            self._create_pane(WorkspacePaneType.narrative, 2, visible=True),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert len(result) == 3
        assert result[0].selected is True
        assert result[1].selected is False
        assert result[2].selected is False

    def test_first_visible_skips_hidden(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=False),
            self._create_pane(WorkspacePaneType.playback, 1, visible=True),
            self._create_pane(WorkspacePaneType.narrative, 2, visible=True),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert result[0].selected is False
        assert result[1].selected is True
        assert result[2].selected is False

    def test_all_hidden_no_selection(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=False),
            self._create_pane(WorkspacePaneType.playback, 1, visible=False),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert all(not p.selected for p in result)

    def test_preserves_pane_id(self) -> None:
        pane = self._create_pane(
            WorkspacePaneType.assignment, 0, pane_id="swpane_custom123"
        )

        result = build_frontend_pane_states(panes=[pane])

        assert result[0].pane_id == "swpane_custom123"

    def test_preserves_order_index(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.narrative, 5),
            self._create_pane(WorkspacePaneType.assignment, 0),
            self._create_pane(WorkspacePaneType.playback, 2),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert result[0].order_index == 0
        assert result[1].order_index == 2
        assert result[2].order_index == 5

    def test_sorts_by_order_index(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.narrative, 5, pane_id="pane_5"),
            self._create_pane(WorkspacePaneType.assignment, 0, pane_id="pane_0"),
            self._create_pane(WorkspacePaneType.playback, 2, pane_id="pane_2"),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert result[0].pane_id == "pane_0"
        assert result[1].pane_id == "pane_2"
        assert result[2].pane_id == "pane_5"

    def test_all_expanded_true(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0),
            self._create_pane(WorkspacePaneType.playback, 1),
        ]

        result = build_frontend_pane_states(panes=panes)

        assert all(p.expanded is True for p in result)

    def test_metadata_is_empty(self) -> None:
        pane = self._create_pane(WorkspacePaneType.assignment, 0)

        result = build_frontend_pane_states(panes=[pane])

        assert result[0].metadata == {}

    def test_version_is_set(self) -> None:
        pane = self._create_pane(WorkspacePaneType.assignment, 0)

        result = build_frontend_pane_states(panes=[pane])

        assert result[0].version == FRONTEND_STATE_VERSION


class TestBuildWorkspaceNavigationState:
    """Test build_workspace_navigation_state function."""

    def _create_pane_state(
        self,
        pane_id: str,
        selected: bool = False,
    ) -> FrontendPaneState:
        return FrontendPaneState(
            pane_id=pane_id,
            visible=True,
            expanded=True,
            selected=selected,
            order_index=0,
        )

    def test_empty_pane_states(self) -> None:
        result = build_workspace_navigation_state(pane_states=[])

        assert result.active_pane_id is None
        assert result.focused_section_id is None
        assert result.selected_evidence_id is None
        assert result.selected_timeline_event_id is None

    def test_no_selected_pane(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=False),
            self._create_pane_state("pane_2", selected=False),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.active_pane_id is None

    def test_selected_pane_becomes_active(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=False),
            self._create_pane_state("pane_2", selected=True),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.active_pane_id == "pane_2"

    def test_first_selected_wins(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=True),
            self._create_pane_state("pane_2", selected=True),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.active_pane_id == "pane_1"

    def test_other_selection_fields_none(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=True),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.focused_section_id is None
        assert result.selected_evidence_id is None
        assert result.selected_timeline_event_id is None

    def test_metadata_is_empty(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=True),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.metadata == {}

    def test_version_is_set(self) -> None:
        pane_states = [
            self._create_pane_state("pane_1", selected=True),
        ]

        result = build_workspace_navigation_state(pane_states=pane_states)

        assert result.version == FRONTEND_STATE_VERSION


class TestBuildWorkspaceFrontendState:
    """Test build_workspace_frontend_state function."""

    def _create_guided_session(
        self,
        view_id: str = "gpv_test123456",
    ) -> GuidedPracticeSessionView:
        return GuidedPracticeSessionView(
            view_id=view_id,
            student_id="student_123",
            runtime_session_id="rps_test123456",
            assignment=GuidedPracticeAssignmentView(
                assignment_id="pa_test123456",
                title="Test Assignment",
                assignment_type=PracticeAssignmentType.drill,
                instructions_preview="Test instructions",
                runtime_active=True,
            ),
            playback=GuidedPracticePlaybackView(
                playback_available=True,
                runtime_session_id="rps_test123456",
                finding_overlay_count=2,
            ),
            adaptive_guidance=GuidedPracticeAdaptiveView(
                recommendation_count=1,
                critical_priority_count=0,
            ),
            teacher_mediation=None,
        )

    def _create_pane(
        self,
        pane_type: WorkspacePaneType,
        order_index: int,
        visible: bool = True,
        pane_id: str | None = None,
    ) -> WorkspacePane:
        return WorkspacePane(
            pane_id=pane_id or f"swpane_{pane_type.value}",
            pane_type=pane_type,
            title=pane_type.value.title(),
            visible=visible,
            order_index=order_index,
            summary=f"{pane_type.value} summary",
        )

    def _create_workspace(
        self,
        workspace_id: str = "swp_test123456",
        panes: list[WorkspacePane] | None = None,
        narrative: PedagogicalNarrative | None = None,
        timeline: PedagogicalTimelineView | None = None,
    ) -> SessionWorkspaceProjection:
        if panes is None:
            panes = [
                self._create_pane(WorkspacePaneType.assignment, 0),
                self._create_pane(WorkspacePaneType.playback, 1),
            ]

        layout = WorkspaceLayout(
            layout_id="swl_test123456",
            audience=WorkspaceAudience.mixed,
            panes=panes,
        )

        return SessionWorkspaceProjection(
            workspace_id=workspace_id,
            student_id="student_123",
            runtime_session_id="rps_test123456",
            audience=WorkspaceAudience.mixed,
            guided_session=self._create_guided_session(),
            narrative=narrative,
            timeline=timeline,
            layout=layout,
        )

    def test_minimal_workspace(self) -> None:
        workspace = self._create_workspace()

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.frontend_state_id.startswith("wfs_")
        assert result.workspace_id == workspace.workspace_id
        assert len(result.pane_states) == 2
        assert result.navigation is not None
        assert result.version == FRONTEND_STATE_VERSION

    def test_frontend_state_id_format(self) -> None:
        workspace = self._create_workspace()

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.frontend_state_id.startswith("wfs_")
        assert len(result.frontend_state_id) == 16

    def test_preserves_workspace_id(self) -> None:
        workspace = self._create_workspace(workspace_id="swp_custom999")

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.workspace_id == "swp_custom999"

    def test_pane_states_match_workspace_panes(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, pane_id="pane_a"),
            self._create_pane(WorkspacePaneType.playback, 1, pane_id="pane_b"),
            self._create_pane(WorkspacePaneType.narrative, 2, pane_id="pane_c"),
        ]
        workspace = self._create_workspace(panes=panes)

        result = build_workspace_frontend_state(workspace=workspace)

        assert len(result.pane_states) == 3
        assert result.pane_states[0].pane_id == "pane_a"
        assert result.pane_states[1].pane_id == "pane_b"
        assert result.pane_states[2].pane_id == "pane_c"

    def test_navigation_has_active_pane(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
        ]
        workspace = self._create_workspace(panes=panes)

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.navigation.active_pane_id == panes[0].pane_id

    def test_metadata_contains_source_ids(self) -> None:
        workspace = self._create_workspace(workspace_id="swp_source123")

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.metadata["source_workspace_id"] == "swp_source123"
        assert result.metadata["source_student_id"] == "student_123"

    def test_generated_at_set(self) -> None:
        workspace = self._create_workspace()

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.generated_at is not None

    def test_notes_contain_visible_count(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
            self._create_pane(WorkspacePaneType.playback, 1, visible=True),
        ]
        workspace = self._create_workspace(panes=panes)

        result = build_workspace_frontend_state(workspace=workspace)

        assert any("2 visible" in note for note in result.notes)

    def test_notes_contain_hidden_count(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
            self._create_pane(WorkspacePaneType.playback, 1, visible=False),
        ]
        workspace = self._create_workspace(panes=panes)

        result = build_workspace_frontend_state(workspace=workspace)

        assert any("1 hidden" in note for note in result.notes)

    def test_notes_contain_initial_focus(self) -> None:
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
        ]
        workspace = self._create_workspace(panes=panes)

        result = build_workspace_frontend_state(workspace=workspace)

        assert any("Initial focus" in note for note in result.notes)

    def test_notes_with_narrative(self) -> None:
        narrative = PedagogicalNarrative(
            narrative_id="pn_test123456",
            audience=NarrativeAudience.student,
            title="Test Narrative",
            overview="Test overview text for the narrative",
            sections=[
                NarrativeSection(
                    section_id="pns_test123456",
                    title="Test Section",
                    summary="Test summary text",
                    severity=NarrativeSeverity.informational,
                )
            ],
        )
        workspace = self._create_workspace(narrative=narrative)

        result = build_workspace_frontend_state(workspace=workspace)

        assert any("Narrative" in note for note in result.notes)

    def test_notes_with_timeline(self) -> None:
        timeline = PedagogicalTimelineView(
            student_id="student_123",
            total_events=5,
        )
        workspace = self._create_workspace(timeline=timeline)

        result = build_workspace_frontend_state(workspace=workspace)

        assert any("Timeline" in note for note in result.notes)

    def test_notes_max_five(self) -> None:
        narrative = PedagogicalNarrative(
            narrative_id="pn_test123456",
            audience=NarrativeAudience.student,
            title="Test Narrative",
            overview="Test overview text for the narrative",
            sections=[
                NarrativeSection(
                    section_id="pns_test123456",
                    title="Test Section",
                    summary="Test summary text",
                    severity=NarrativeSeverity.informational,
                )
            ],
        )
        timeline = PedagogicalTimelineView(
            student_id="student_123",
            total_events=5,
        )
        panes = [
            self._create_pane(WorkspacePaneType.assignment, 0, visible=True),
            self._create_pane(WorkspacePaneType.playback, 1, visible=True),
            self._create_pane(WorkspacePaneType.narrative, 2, visible=False),
        ]
        workspace = self._create_workspace(
            panes=panes, narrative=narrative, timeline=timeline
        )

        result = build_workspace_frontend_state(workspace=workspace)

        assert len(result.notes) <= 5

    def test_empty_layout_panes(self) -> None:
        workspace = self._create_workspace(panes=[])

        result = build_workspace_frontend_state(workspace=workspace)

        assert len(result.pane_states) == 0
        assert result.navigation.active_pane_id is None


class TestVersionConstant:
    """Test version constants."""

    def test_engine_version_is_string(self) -> None:
        assert isinstance(FRONTEND_STATE_ENGINE_VERSION, str)

    def test_engine_version_format(self) -> None:
        parts = FRONTEND_STATE_ENGINE_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestIntegration:
    """Integration tests for frontend state projection."""

    def _create_full_workspace(self) -> SessionWorkspaceProjection:
        guided_session = GuidedPracticeSessionView(
            view_id="gpv_integration",
            student_id="student_integration",
            runtime_session_id="rps_integration",
            assignment=GuidedPracticeAssignmentView(
                assignment_id="pa_integration",
                title="Integration Test",
                assignment_type=PracticeAssignmentType.drill,
                instructions_preview="Test instructions",
                runtime_active=True,
            ),
            playback=GuidedPracticePlaybackView(
                playback_available=True,
                runtime_session_id="rps_integration",
                finding_overlay_count=3,
            ),
            adaptive_guidance=GuidedPracticeAdaptiveView(
                recommendation_count=2,
                critical_priority_count=1,
            ),
            teacher_mediation=GuidedPracticeTeacherMediationView(
                mediation_count=1,
                teacher_override_count=1,
            ),
        )

        panes = [
            WorkspacePane(
                pane_id="swpane_assign",
                pane_type=WorkspacePaneType.assignment,
                title="Assignment",
                visible=True,
                order_index=0,
                summary="Assignment pane",
            ),
            WorkspacePane(
                pane_id="swpane_play",
                pane_type=WorkspacePaneType.playback,
                title="Playback",
                visible=True,
                order_index=1,
                summary="Playback pane",
            ),
            WorkspacePane(
                pane_id="swpane_adapt",
                pane_type=WorkspacePaneType.adaptive_guidance,
                title="Adaptive",
                visible=True,
                order_index=2,
                summary="Adaptive pane",
            ),
            WorkspacePane(
                pane_id="swpane_mediate",
                pane_type=WorkspacePaneType.teacher_mediation,
                title="Mediation",
                visible=False,
                order_index=3,
                summary="Mediation pane",
            ),
        ]

        layout = WorkspaceLayout(
            layout_id="swl_integration",
            audience=WorkspaceAudience.mixed,
            panes=panes,
        )

        narrative = PedagogicalNarrative(
            narrative_id="pn_integration",
            audience=NarrativeAudience.student,
            title="Integration Narrative",
            overview="Overview text for the integration test narrative",
            sections=[
                NarrativeSection(
                    section_id="pns_integration",
                    title="Section",
                    summary="Summary text for integration test",
                    severity=NarrativeSeverity.informational,
                )
            ],
        )

        timeline = PedagogicalTimelineView(
            student_id="student_integration",
            total_events=10,
        )

        return SessionWorkspaceProjection(
            workspace_id="swp_integration",
            student_id="student_integration",
            runtime_session_id="rps_integration",
            audience=WorkspaceAudience.mixed,
            guided_session=guided_session,
            narrative=narrative,
            timeline=timeline,
            layout=layout,
        )

    def test_full_workspace_projection(self) -> None:
        workspace = self._create_full_workspace()

        result = build_workspace_frontend_state(workspace=workspace)

        assert result.frontend_state_id.startswith("wfs_")
        assert result.workspace_id == "swp_integration"
        assert len(result.pane_states) == 4

        assert result.pane_states[0].pane_id == "swpane_assign"
        assert result.pane_states[0].selected is True
        assert result.pane_states[0].visible is True

        assert result.pane_states[1].pane_id == "swpane_play"
        assert result.pane_states[1].selected is False
        assert result.pane_states[1].visible is True

        assert result.pane_states[2].pane_id == "swpane_adapt"
        assert result.pane_states[2].selected is False
        assert result.pane_states[2].visible is True

        assert result.pane_states[3].pane_id == "swpane_mediate"
        assert result.pane_states[3].selected is False
        assert result.pane_states[3].visible is False

        assert result.navigation.active_pane_id == "swpane_assign"
        assert result.navigation.focused_section_id is None

        assert len(result.notes) <= 5

    def test_serialization_roundtrip(self) -> None:
        workspace = self._create_full_workspace()

        result = build_workspace_frontend_state(workspace=workspace)

        data = result.model_dump(mode="json")
        restored = WorkspaceFrontendState.model_validate(data)

        assert restored.frontend_state_id == result.frontend_state_id
        assert restored.workspace_id == result.workspace_id
        assert len(restored.pane_states) == len(result.pane_states)
        assert restored.navigation.active_pane_id == result.navigation.active_pane_id
