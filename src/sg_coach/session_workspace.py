"""
Session Workspace Projection Engine.

Sprint 36: Canonical Session Workspace Projection.

Provides:
- build_workspace_panes(): Build deterministic pane list
- build_workspace_layout(): Build workspace layout
- build_session_workspace_projection(): Build complete workspace projection

Core rules:
- Workspace projections are composition layers only
- Canonical runtime/evidence structures remain authoritative
- Pane ordering must remain deterministic
- Audience filtering must remain explicit
- AI layout generation is prohibited
- Workspace builders must never mutate source projections
"""
from __future__ import annotations

import secrets
from typing import Any, Sequence

from sg_spec.schemas.guided_practice_view import GuidedPracticeSessionView
from sg_spec.schemas.pedagogical_narrative import PedagogicalNarrative
from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspaceAudience,
    WorkspaceLayout,
    WorkspacePane,
    WorkspacePaneType,
)


SESSION_WORKSPACE_ENGINE_VERSION = "0.1.0"

PANE_ORDER = {
    WorkspacePaneType.assignment: 0,
    WorkspacePaneType.playback: 1,
    WorkspacePaneType.adaptive_guidance: 2,
    WorkspacePaneType.teacher_mediation: 3,
    WorkspacePaneType.narrative: 4,
    WorkspacePaneType.timeline: 5,
}

PANE_TITLES = {
    WorkspacePaneType.assignment: "Assignment",
    WorkspacePaneType.playback: "Playback",
    WorkspacePaneType.adaptive_guidance: "Adaptive Guidance",
    WorkspacePaneType.teacher_mediation: "Teacher Mediation",
    WorkspacePaneType.narrative: "Coaching Narrative",
    WorkspacePaneType.timeline: "Timeline",
}


def _generate_workspace_id() -> str:
    """Generate unique workspace ID."""
    return f"swp_{secrets.token_hex(6)}"


def _generate_layout_id() -> str:
    """Generate unique layout ID."""
    return f"swl_{secrets.token_hex(6)}"


def _generate_pane_id() -> str:
    """Generate unique pane ID."""
    return f"swpane_{secrets.token_hex(6)}"


def _build_assignment_pane(
    guided_session: GuidedPracticeSessionView,
) -> WorkspacePane:
    """Build assignment pane from guided session."""
    assignment = guided_session.assignment
    visible = assignment is not None

    if assignment:
        if assignment.runtime_active:
            summary = f"Active practice session: {assignment.title}"
        else:
            summary = f"Practice assignment: {assignment.title}"
    else:
        summary = "No active assignment"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.assignment,
        title=PANE_TITLES[WorkspacePaneType.assignment],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.assignment],
        summary=summary,
        metadata={"assignment_id": assignment.assignment_id if assignment else None},
    )


def _build_playback_pane(
    guided_session: GuidedPracticeSessionView,
) -> WorkspacePane:
    """Build playback pane from guided session."""
    playback = guided_session.playback
    visible = playback is not None and playback.playback_available

    if playback and playback.playback_available:
        summary = f"Playback available with {playback.finding_overlay_count} finding overlays"
    else:
        summary = "Playback not available"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.playback,
        title=PANE_TITLES[WorkspacePaneType.playback],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.playback],
        summary=summary,
        metadata={
            "runtime_session_id": playback.runtime_session_id if playback else None,
        },
    )


def _build_adaptive_guidance_pane(
    guided_session: GuidedPracticeSessionView,
) -> WorkspacePane:
    """Build adaptive guidance pane from guided session."""
    adaptive = guided_session.adaptive_guidance
    visible = adaptive is not None and adaptive.recommendation_count > 0

    if adaptive and adaptive.recommendation_count > 0:
        summary = f"Adaptive guidance active with {adaptive.recommendation_count} recommendations"
        if adaptive.critical_priority_count > 0:
            summary += f" ({adaptive.critical_priority_count} critical)"
    else:
        summary = "No adaptive guidance active"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.adaptive_guidance,
        title=PANE_TITLES[WorkspacePaneType.adaptive_guidance],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.adaptive_guidance],
        summary=summary,
        metadata={
            "recommendation_count": adaptive.recommendation_count if adaptive else 0,
        },
    )


def _build_teacher_mediation_pane(
    guided_session: GuidedPracticeSessionView,
    audience: WorkspaceAudience,
) -> WorkspacePane:
    """Build teacher mediation pane from guided session."""
    mediation = guided_session.teacher_mediation
    has_mediation = mediation is not None and mediation.mediation_count > 0

    if audience == WorkspaceAudience.student:
        visible = False
    else:
        visible = has_mediation

    if has_mediation:
        summary = f"Teacher mediation active with {mediation.mediation_count} decisions"
    else:
        summary = "No teacher mediation"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.teacher_mediation,
        title=PANE_TITLES[WorkspacePaneType.teacher_mediation],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.teacher_mediation],
        summary=summary,
        metadata={
            "mediation_count": mediation.mediation_count if mediation else 0,
        },
    )


def _build_narrative_pane(
    narrative: PedagogicalNarrative | None,
) -> WorkspacePane:
    """Build narrative pane from pedagogical narrative."""
    visible = narrative is not None

    if narrative:
        summary = narrative.title
    else:
        summary = "No coaching narrative available"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.narrative,
        title=PANE_TITLES[WorkspacePaneType.narrative],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.narrative],
        summary=summary,
        metadata={
            "narrative_id": narrative.narrative_id if narrative else None,
        },
    )


def _build_timeline_pane(
    timeline: PedagogicalTimelineView | None,
) -> WorkspacePane:
    """Build timeline pane from pedagogical timeline view."""
    visible = timeline is not None and timeline.total_events > 0

    if timeline and timeline.total_events > 0:
        summary = f"Timeline contains {timeline.total_events} pedagogical events"
    else:
        summary = "No timeline evidence available"

    return WorkspacePane(
        pane_id=_generate_pane_id(),
        pane_type=WorkspacePaneType.timeline,
        title=PANE_TITLES[WorkspacePaneType.timeline],
        visible=visible,
        order_index=PANE_ORDER[WorkspacePaneType.timeline],
        summary=summary,
        metadata={
            "total_events": timeline.total_events if timeline else 0,
        },
    )


def build_workspace_panes(
    *,
    guided_session: GuidedPracticeSessionView,
    narrative: PedagogicalNarrative | None = None,
    timeline: PedagogicalTimelineView | None = None,
    audience: WorkspaceAudience = WorkspaceAudience.mixed,
) -> list[WorkspacePane]:
    """
    Build deterministic pane list for workspace.

    Parameters
    ----------
    guided_session:
        The guided practice session view.
    narrative:
        Optional pedagogical narrative.
    timeline:
        Optional pedagogical timeline view.
    audience:
        Target audience for workspace.

    Returns
    -------
    List of WorkspacePane objects in deterministic order.
    """
    panes = [
        _build_assignment_pane(guided_session),
        _build_playback_pane(guided_session),
        _build_adaptive_guidance_pane(guided_session),
        _build_teacher_mediation_pane(guided_session, audience),
        _build_narrative_pane(narrative),
        _build_timeline_pane(timeline),
    ]

    panes.sort(key=lambda p: p.order_index)

    return panes


def build_workspace_layout(
    *,
    panes: Sequence[WorkspacePane],
    audience: WorkspaceAudience,
) -> WorkspaceLayout:
    """
    Build workspace layout from panes.

    Parameters
    ----------
    panes:
        Ordered list of workspace panes.
    audience:
        Target audience for layout.

    Returns
    -------
    WorkspaceLayout with deterministic pane arrangement.
    """
    layout_panes = list(panes)
    layout_panes.sort(key=lambda p: p.order_index)

    notes: list[str] = []

    return WorkspaceLayout(
        layout_id=_generate_layout_id(),
        audience=audience,
        panes=layout_panes,
        notes=notes,
    )


def _generate_workspace_notes(
    panes: Sequence[WorkspacePane],
    guided_session: GuidedPracticeSessionView,
    narrative: PedagogicalNarrative | None,
    timeline: PedagogicalTimelineView | None,
) -> list[str]:
    """Generate deterministic workspace notes."""
    notes: list[str] = []

    for pane in panes:
        if not pane.visible:
            continue

        if pane.pane_type == WorkspacePaneType.playback:
            notes.append("Playback review is available.")
        elif pane.pane_type == WorkspacePaneType.teacher_mediation:
            notes.append("Teacher mediation pane is active.")
        elif pane.pane_type == WorkspacePaneType.narrative:
            notes.append("Narrative coaching explanation is available.")
        elif pane.pane_type == WorkspacePaneType.timeline:
            if timeline and timeline.total_events > 0:
                notes.append("Timeline evidence contains recent pedagogical activity.")
        elif pane.pane_type == WorkspacePaneType.adaptive_guidance:
            adaptive = guided_session.adaptive_guidance
            if adaptive and adaptive.critical_priority_count > 0:
                notes.append("Critical adaptive guidance requires attention.")

    return notes[:5]


def build_session_workspace_projection(
    *,
    guided_session: GuidedPracticeSessionView,
    narrative: PedagogicalNarrative | None = None,
    timeline: PedagogicalTimelineView | None = None,
    audience: WorkspaceAudience = WorkspaceAudience.mixed,
) -> SessionWorkspaceProjection:
    """
    Build complete session workspace projection.

    Parameters
    ----------
    guided_session:
        The guided practice session view.
    narrative:
        Optional pedagogical narrative.
    timeline:
        Optional pedagogical timeline view.
    audience:
        Target audience for workspace.

    Returns
    -------
    SessionWorkspaceProjection with all components.
    """
    panes = build_workspace_panes(
        guided_session=guided_session,
        narrative=narrative,
        timeline=timeline,
        audience=audience,
    )

    layout = build_workspace_layout(
        panes=panes,
        audience=audience,
    )

    notes = _generate_workspace_notes(
        panes=panes,
        guided_session=guided_session,
        narrative=narrative,
        timeline=timeline,
    )

    metadata: dict[str, Any] = {
        "source_session_view_id": guided_session.view_id,
    }
    if narrative:
        metadata["narrative_id"] = narrative.narrative_id
    if timeline and timeline.student_id:
        metadata["timeline_student_id"] = timeline.student_id

    return SessionWorkspaceProjection(
        workspace_id=_generate_workspace_id(),
        student_id=guided_session.student_id,
        runtime_session_id=guided_session.runtime_session_id,
        audience=audience,
        guided_session=guided_session,
        narrative=narrative,
        timeline=timeline,
        layout=layout,
        notes=notes,
        metadata=metadata,
    )


__all__ = [
    "SESSION_WORKSPACE_ENGINE_VERSION",
    "PANE_ORDER",
    "PANE_TITLES",
    "build_workspace_panes",
    "build_workspace_layout",
    "build_session_workspace_projection",
]
