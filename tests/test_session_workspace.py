"""
Tests for session_workspace module.

Sprint 36: Canonical Session Workspace Projection.
"""
from __future__ import annotations

import pytest

from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.pedagogical_narrative import (
    NarrativeAudience,
    NarrativeSeverity,
    NarrativeSection,
    PedagogicalNarrative,
)
from sg_spec.schemas.pedagogical_visualization import (
    PedagogicalTimelineView,
)
from sg_spec.schemas.practice_assignment import PracticeAssignmentType
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspaceAudience,
    WorkspaceLayout,
    WorkspacePane,
    WorkspacePaneType,
)

from sg_coach.session_workspace import (
    SESSION_WORKSPACE_ENGINE_VERSION,
    PANE_ORDER,
    PANE_TITLES,
    build_workspace_panes,
    build_workspace_layout,
    build_session_workspace_projection,
)


class TestConstants:
    """Test module-level constants."""

    def test_version_is_string(self) -> None:
        assert isinstance(SESSION_WORKSPACE_ENGINE_VERSION, str)
        assert len(SESSION_WORKSPACE_ENGINE_VERSION) > 0

    def test_pane_order_has_all_types(self) -> None:
        for pane_type in WorkspacePaneType:
            assert pane_type in PANE_ORDER

    def test_pane_titles_has_all_types(self) -> None:
        for pane_type in WorkspacePaneType:
            assert pane_type in PANE_TITLES
            assert len(PANE_TITLES[pane_type]) > 0

    def test_pane_order_values_are_unique(self) -> None:
        values = list(PANE_ORDER.values())
        assert len(values) == len(set(values))


def _create_minimal_session_view(
    *,
    student_id: str | None = None,
    runtime_session_id: str | None = None,
) -> GuidedPracticeSessionView:
    """Create minimal guided session view for testing."""
    return GuidedPracticeSessionView(
        view_id="gpv_test123456",
        student_id=student_id,
        runtime_session_id=runtime_session_id,
        assignment=None,
        playback=None,
        adaptive_guidance=None,
        teacher_mediation=None,
    )


def _create_assignment_view(
    *,
    assignment_id: str = "assign_test123",
    title: str = "Test Assignment",
    runtime_active: bool = False,
) -> GuidedPracticeAssignmentView:
    """Create assignment view for testing."""
    return GuidedPracticeAssignmentView(
        assignment_id=assignment_id,
        title=title,
        assignment_type=PracticeAssignmentType.drill,
        instructions_preview="Practice this exercise",
        runtime_active=runtime_active,
    )


def _create_playback_view(
    *,
    runtime_session_id: str = "rts_test123456",
    playback_available: bool = True,
    finding_overlay_count: int = 3,
) -> GuidedPracticePlaybackView:
    """Create playback view for testing."""
    return GuidedPracticePlaybackView(
        runtime_session_id=runtime_session_id,
        playback_available=playback_available,
        finding_overlay_count=finding_overlay_count,
        active_finding_ids=[],
    )


def _create_adaptive_view(
    *,
    recommendation_count: int = 2,
    critical_priority_count: int = 0,
) -> GuidedPracticeAdaptiveView:
    """Create adaptive guidance view for testing."""
    return GuidedPracticeAdaptiveView(
        recommendation_count=recommendation_count,
        critical_priority_count=critical_priority_count,
        high_priority_count=1,
    )


def _create_mediation_view(
    *,
    mediation_count: int = 1,
    latest_mediation_id: str = "med_test123456",
) -> GuidedPracticeTeacherMediationView:
    """Create mediation view for testing."""
    return GuidedPracticeTeacherMediationView(
        latest_mediation_id=latest_mediation_id,
        mediation_count=mediation_count,
        rejected_count=0,
        modified_count=0,
    )


def _create_narrative(
    *,
    narrative_id: str = "pn_test12345678",
    title: str = "Test Narrative",
) -> PedagogicalNarrative:
    """Create pedagogical narrative for testing."""
    return PedagogicalNarrative(
        narrative_id=narrative_id,
        audience=NarrativeAudience.mixed,
        title=title,
        overview="Test overview",
        sections=[
            NarrativeSection(
                section_id="pns_test123456",
                title="Test Section",
                summary="Test summary",
                severity=NarrativeSeverity.informational,
            ),
        ],
    )


def _create_timeline_view(
    *,
    student_id: str | None = "student_123",
    total_events: int = 5,
) -> PedagogicalTimelineView:
    """Create timeline view for testing."""
    return PedagogicalTimelineView(
        student_id=student_id,
        total_events=total_events,
        diagnosis_groups=[],
        timeline_events=[],
    )


class TestBuildWorkspacePanes:
    """Test build_workspace_panes function."""

    def test_minimal_session_returns_all_pane_types(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        pane_types = {p.pane_type for p in panes}
        assert len(pane_types) == len(WorkspacePaneType)

    def test_panes_are_sorted_by_order_index(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        order_indices = [p.order_index for p in panes]
        assert order_indices == sorted(order_indices)

    def test_minimal_session_all_panes_hidden_except_assignment(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        visible_panes = [p for p in panes if p.visible]
        assert len(visible_panes) == 0

    def test_assignment_pane_visible_when_present(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"assignment": _create_assignment_view()}
        )
        panes = build_workspace_panes(guided_session=session)

        assignment_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.assignment
        )
        assert assignment_pane.visible is True

    def test_playback_pane_visible_when_available(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"playback": _create_playback_view(playback_available=True)}
        )
        panes = build_workspace_panes(guided_session=session)

        playback_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.playback
        )
        assert playback_pane.visible is True

    def test_playback_pane_hidden_when_not_available(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"playback": _create_playback_view(playback_available=False)}
        )
        panes = build_workspace_panes(guided_session=session)

        playback_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.playback
        )
        assert playback_pane.visible is False

    def test_adaptive_pane_visible_with_recommendations(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"adaptive_guidance": _create_adaptive_view(recommendation_count=2)}
        )
        panes = build_workspace_panes(guided_session=session)

        adaptive_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance
        )
        assert adaptive_pane.visible is True

    def test_adaptive_pane_hidden_without_recommendations(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"adaptive_guidance": _create_adaptive_view(recommendation_count=0)}
        )
        panes = build_workspace_panes(guided_session=session)

        adaptive_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance
        )
        assert adaptive_pane.visible is False

    def test_mediation_pane_hidden_for_student_audience(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )
        panes = build_workspace_panes(
            guided_session=session,
            audience=WorkspaceAudience.student,
        )

        mediation_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is False

    def test_mediation_pane_visible_for_teacher_audience(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )
        panes = build_workspace_panes(
            guided_session=session,
            audience=WorkspaceAudience.teacher,
        )

        mediation_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is True

    def test_mediation_pane_visible_for_mixed_audience(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )
        panes = build_workspace_panes(
            guided_session=session,
            audience=WorkspaceAudience.mixed,
        )

        mediation_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is True

    def test_narrative_pane_visible_when_provided(self) -> None:
        session = _create_minimal_session_view()
        narrative = _create_narrative()
        panes = build_workspace_panes(
            guided_session=session,
            narrative=narrative,
        )

        narrative_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.narrative
        )
        assert narrative_pane.visible is True
        assert narrative_pane.summary == narrative.title

    def test_narrative_pane_hidden_when_not_provided(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        narrative_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.narrative
        )
        assert narrative_pane.visible is False

    def test_timeline_pane_visible_with_events(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view(total_events=5)
        panes = build_workspace_panes(
            guided_session=session,
            timeline=timeline,
        )

        timeline_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.timeline
        )
        assert timeline_pane.visible is True

    def test_timeline_pane_hidden_without_events(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view(total_events=0)
        panes = build_workspace_panes(
            guided_session=session,
            timeline=timeline,
        )

        timeline_pane = next(
            p for p in panes if p.pane_type == WorkspacePaneType.timeline
        )
        assert timeline_pane.visible is False

    def test_pane_ids_are_unique(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        pane_ids = [p.pane_id for p in panes]
        assert len(pane_ids) == len(set(pane_ids))

    def test_pane_ids_have_correct_prefix(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        for pane in panes:
            assert pane.pane_id.startswith("swpane_")

    def test_pane_titles_match_constants(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        for pane in panes:
            assert pane.title == PANE_TITLES[pane.pane_type]

    def test_pane_order_matches_constants(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        for pane in panes:
            assert pane.order_index == PANE_ORDER[pane.pane_type]


class TestAssignmentPaneSummary:
    """Test assignment pane summary generation."""

    def test_no_assignment_summary(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.assignment)
        assert pane.summary == "No active assignment"

    def test_active_assignment_summary(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "assignment": _create_assignment_view(
                    title="Test Exercise",
                    runtime_active=True,
                )
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.assignment)
        assert "Active practice session" in pane.summary
        assert "Test Exercise" in pane.summary

    def test_inactive_assignment_summary(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "assignment": _create_assignment_view(
                    title="Test Exercise",
                    runtime_active=False,
                )
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.assignment)
        assert "Practice assignment" in pane.summary
        assert "Test Exercise" in pane.summary


class TestPlaybackPaneSummary:
    """Test playback pane summary generation."""

    def test_no_playback_summary(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.playback)
        assert "not available" in pane.summary.lower()

    def test_playback_available_summary(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "playback": _create_playback_view(
                    playback_available=True,
                    finding_overlay_count=3,
                )
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.playback)
        assert "3 finding overlays" in pane.summary


class TestAdaptivePaneSummary:
    """Test adaptive guidance pane summary generation."""

    def test_no_adaptive_summary(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance)
        assert "No adaptive guidance" in pane.summary

    def test_adaptive_with_recommendations_summary(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "adaptive_guidance": _create_adaptive_view(
                    recommendation_count=2,
                    critical_priority_count=0,
                )
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance)
        assert "2 recommendations" in pane.summary

    def test_adaptive_with_critical_summary(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "adaptive_guidance": _create_adaptive_view(
                    recommendation_count=3,
                    critical_priority_count=1,
                )
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance)
        assert "3 recommendations" in pane.summary
        assert "1 critical" in pane.summary


class TestBuildWorkspaceLayout:
    """Test build_workspace_layout function."""

    def test_layout_has_correct_audience(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        layout = build_workspace_layout(
            panes=panes,
            audience=WorkspaceAudience.teacher,
        )

        assert layout.audience == WorkspaceAudience.teacher

    def test_layout_id_has_correct_prefix(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        layout = build_workspace_layout(
            panes=panes,
            audience=WorkspaceAudience.mixed,
        )

        assert layout.layout_id.startswith("swl_")

    def test_layout_panes_are_sorted(self) -> None:
        session = _create_minimal_session_view()
        panes = build_workspace_panes(guided_session=session)

        layout = build_workspace_layout(
            panes=panes,
            audience=WorkspaceAudience.mixed,
        )

        order_indices = [p.order_index for p in layout.panes]
        assert order_indices == sorted(order_indices)


class TestBuildSessionWorkspaceProjection:
    """Test build_session_workspace_projection function."""

    def test_projection_id_has_correct_prefix(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.workspace_id.startswith("swp_")

    def test_projection_includes_student_id(self) -> None:
        session = _create_minimal_session_view(student_id="student_123")

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.student_id == "student_123"

    def test_projection_includes_runtime_session_id(self) -> None:
        session = _create_minimal_session_view(runtime_session_id="rts_test123456")

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.runtime_session_id == "rts_test123456"

    def test_projection_includes_audience(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.teacher,
        )

        assert projection.audience == WorkspaceAudience.teacher

    def test_projection_includes_guided_session(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.guided_session is not None
        assert projection.guided_session.view_id == session.view_id

    def test_projection_includes_narrative_when_provided(self) -> None:
        session = _create_minimal_session_view()
        narrative = _create_narrative()

        projection = build_session_workspace_projection(
            guided_session=session,
            narrative=narrative,
        )

        assert projection.narrative is not None
        assert projection.narrative.narrative_id == narrative.narrative_id

    def test_projection_includes_timeline_when_provided(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view()

        projection = build_session_workspace_projection(
            guided_session=session,
            timeline=timeline,
        )

        assert projection.timeline is not None
        assert projection.timeline.total_events == timeline.total_events

    def test_projection_includes_layout(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.layout is not None
        assert isinstance(projection.layout, WorkspaceLayout)

    def test_projection_layout_matches_audience(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.student,
        )

        assert projection.layout.audience == WorkspaceAudience.student

    def test_projection_has_generated_at(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert projection.generated_at is not None

    def test_projection_metadata_includes_source_view_id(self) -> None:
        session = _create_minimal_session_view()

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert "source_session_view_id" in projection.metadata
        assert projection.metadata["source_session_view_id"] == session.view_id

    def test_projection_metadata_includes_narrative_id(self) -> None:
        session = _create_minimal_session_view()
        narrative = _create_narrative(narrative_id="pn_test12345678")

        projection = build_session_workspace_projection(
            guided_session=session,
            narrative=narrative,
        )

        assert "narrative_id" in projection.metadata
        assert projection.metadata["narrative_id"] == "pn_test12345678"

    def test_projection_metadata_includes_timeline_student_id(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view(student_id="student_456")

        projection = build_session_workspace_projection(
            guided_session=session,
            timeline=timeline,
        )

        assert "timeline_student_id" in projection.metadata
        assert projection.metadata["timeline_student_id"] == "student_456"


class TestProjectionNotes:
    """Test workspace projection notes generation."""

    def test_playback_note_when_visible(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"playback": _create_playback_view(playback_available=True)}
        )

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert any("Playback" in note for note in projection.notes)

    def test_mediation_note_for_teacher(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.teacher,
        )

        assert any("mediation" in note.lower() for note in projection.notes)

    def test_narrative_note_when_present(self) -> None:
        session = _create_minimal_session_view()
        narrative = _create_narrative()

        projection = build_session_workspace_projection(
            guided_session=session,
            narrative=narrative,
        )

        assert any("Narrative" in note for note in projection.notes)

    def test_timeline_note_with_events(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view(total_events=5)

        projection = build_session_workspace_projection(
            guided_session=session,
            timeline=timeline,
        )

        assert any("Timeline" in note for note in projection.notes)

    def test_critical_adaptive_note(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "adaptive_guidance": _create_adaptive_view(
                    recommendation_count=2,
                    critical_priority_count=1,
                )
            }
        )

        projection = build_session_workspace_projection(
            guided_session=session,
        )

        assert any("Critical" in note for note in projection.notes)

    def test_notes_limited_to_five(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "assignment": _create_assignment_view(),
                "playback": _create_playback_view(playback_available=True),
                "adaptive_guidance": _create_adaptive_view(
                    recommendation_count=2,
                    critical_priority_count=1,
                ),
                "teacher_mediation": _create_mediation_view(mediation_count=1),
            }
        )
        narrative = _create_narrative()
        timeline = _create_timeline_view(total_events=5)

        projection = build_session_workspace_projection(
            guided_session=session,
            narrative=narrative,
            timeline=timeline,
        )

        assert len(projection.notes) <= 5


class TestAudienceFiltering:
    """Test audience-based visibility filtering."""

    def test_student_audience_hides_mediation(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.student,
        )

        mediation_pane = next(
            p for p in projection.layout.panes
            if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is False

    def test_teacher_audience_shows_mediation(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.teacher,
        )

        mediation_pane = next(
            p for p in projection.layout.panes
            if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is True

    def test_mixed_audience_shows_mediation(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={"teacher_mediation": _create_mediation_view(mediation_count=1)}
        )

        projection = build_session_workspace_projection(
            guided_session=session,
            audience=WorkspaceAudience.mixed,
        )

        mediation_pane = next(
            p for p in projection.layout.panes
            if p.pane_type == WorkspacePaneType.teacher_mediation
        )
        assert mediation_pane.visible is True


class TestPaneMetadata:
    """Test pane metadata population."""

    def test_assignment_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "assignment": _create_assignment_view(assignment_id="assign_abc123")
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.assignment)
        assert "assignment_id" in pane.metadata
        assert pane.metadata["assignment_id"] == "assign_abc123"

    def test_playback_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "playback": _create_playback_view(runtime_session_id="rts_abc12345")
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.playback)
        assert "runtime_session_id" in pane.metadata
        assert pane.metadata["runtime_session_id"] == "rts_abc12345"

    def test_adaptive_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "adaptive_guidance": _create_adaptive_view(recommendation_count=3)
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.adaptive_guidance)
        assert "recommendation_count" in pane.metadata
        assert pane.metadata["recommendation_count"] == 3

    def test_mediation_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        session = session.model_copy(
            update={
                "teacher_mediation": _create_mediation_view(mediation_count=2)
            }
        )
        panes = build_workspace_panes(guided_session=session)

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.teacher_mediation)
        assert "mediation_count" in pane.metadata
        assert pane.metadata["mediation_count"] == 2

    def test_narrative_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        narrative = _create_narrative(narrative_id="pn_metadata123")
        panes = build_workspace_panes(
            guided_session=session,
            narrative=narrative,
        )

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.narrative)
        assert "narrative_id" in pane.metadata
        assert pane.metadata["narrative_id"] == "pn_metadata123"

    def test_timeline_pane_metadata(self) -> None:
        session = _create_minimal_session_view()
        timeline = _create_timeline_view(total_events=7)
        panes = build_workspace_panes(
            guided_session=session,
            timeline=timeline,
        )

        pane = next(p for p in panes if p.pane_type == WorkspacePaneType.timeline)
        assert "total_events" in pane.metadata
        assert pane.metadata["total_events"] == 7
