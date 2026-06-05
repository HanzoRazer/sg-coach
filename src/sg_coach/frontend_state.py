"""
Frontend State Projection Engine.

Sprint 38: Canonical Frontend State Projection.

Provides:
- build_frontend_pane_states(): Build pane states from workspace panes
- build_workspace_navigation_state(): Build navigation state
- build_workspace_frontend_state(): Build complete frontend state

Core rules:
- Frontend state mirrors canonical workspace structure
- Frontend state preserves pane identity and visibility
- Frontend state is framework-independent
- Frontend state must remain deterministic
- Frontend state builders must never mutate workspace projections
- Pane ordering derives from workspace ordering
"""
from __future__ import annotations

import secrets
from typing import Sequence

from sg_spec.schemas.frontend_state import (
    FRONTEND_STATE_VERSION,
    FrontendPaneState,
    WorkspaceFrontendState,
    WorkspaceNavigationState,
)
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspacePane,
    WorkspacePaneType,
)


FRONTEND_STATE_ENGINE_VERSION = "0.1.0"


def _generate_frontend_state_id() -> str:
    """Generate unique frontend state ID."""
    return f"wfs_{secrets.token_hex(6)}"


def build_frontend_pane_states(
    *,
    panes: Sequence[WorkspacePane],
) -> list[FrontendPaneState]:
    """
    Build frontend pane states from workspace panes.

    Parameters
    ----------
    panes:
        Ordered list of workspace panes.

    Returns
    -------
    List of FrontendPaneState objects preserving workspace pane identity.

    Notes
    -----
    - All panes are included (visible and hidden)
    - Hidden panes have visible=False
    - All panes start with expanded=True
    - Exactly one visible pane gets selected=True (first visible pane)
    - Pane ordering matches workspace order_index
    """
    pane_states: list[FrontendPaneState] = []
    first_visible_found = False

    sorted_panes = sorted(panes, key=lambda p: p.order_index)

    for pane in sorted_panes:
        selected = False
        if pane.visible and not first_visible_found:
            selected = True
            first_visible_found = True

        pane_state = FrontendPaneState(
            pane_id=pane.pane_id,
            visible=pane.visible,
            expanded=True,
            selected=selected,
            order_index=pane.order_index,
            metadata={},
        )
        pane_states.append(pane_state)

    return pane_states


def build_workspace_navigation_state(
    *,
    pane_states: Sequence[FrontendPaneState],
) -> WorkspaceNavigationState:
    """
    Build workspace navigation state.

    Parameters
    ----------
    pane_states:
        List of frontend pane states.

    Returns
    -------
    WorkspaceNavigationState with active pane set to selected pane.

    Notes
    -----
    - active_pane_id is set to the selected pane's pane_id
    - Other selection fields start as None
    """
    active_pane_id = None

    for pane_state in pane_states:
        if pane_state.selected:
            active_pane_id = pane_state.pane_id
            break

    return WorkspaceNavigationState(
        active_pane_id=active_pane_id,
        focused_section_id=None,
        selected_evidence_id=None,
        selected_timeline_event_id=None,
        metadata={},
    )


def _generate_frontend_state_notes(
    pane_states: Sequence[FrontendPaneState],
    workspace: SessionWorkspaceProjection | None,
) -> list[str]:
    """Generate deterministic frontend state notes."""
    notes: list[str] = []

    visible_count = sum(1 for p in pane_states if p.visible)
    hidden_count = sum(1 for p in pane_states if not p.visible)

    if visible_count > 0:
        notes.append(f"Workspace contains {visible_count} visible pane(s).")

    if hidden_count > 0:
        notes.append(f"Workspace contains {hidden_count} hidden pane(s).")

    selected_pane = next((p for p in pane_states if p.selected), None)
    if selected_pane:
        notes.append(f"Initial focus: pane {selected_pane.pane_id}.")

    if workspace and workspace.narrative:
        notes.append("Narrative content is available for review.")

    if workspace and workspace.timeline and workspace.timeline.total_events > 0:
        notes.append("Timeline evidence is available for review.")

    return notes[:5]


def build_workspace_frontend_state(
    *,
    workspace: SessionWorkspaceProjection,
) -> WorkspaceFrontendState:
    """
    Build complete frontend state from workspace projection.

    Parameters
    ----------
    workspace:
        The source workspace projection.

    Returns
    -------
    WorkspaceFrontendState with all components.

    Notes
    -----
    - Does not mutate the source workspace
    - Preserves all pane identity from workspace
    - Creates deterministic initial UI state
    """
    panes = workspace.layout.panes if workspace.layout else []

    pane_states = build_frontend_pane_states(panes=panes)

    navigation = build_workspace_navigation_state(pane_states=pane_states)

    notes = _generate_frontend_state_notes(
        pane_states=pane_states,
        workspace=workspace,
    )

    return WorkspaceFrontendState(
        frontend_state_id=_generate_frontend_state_id(),
        workspace_id=workspace.workspace_id,
        pane_states=pane_states,
        navigation=navigation,
        notes=notes,
        metadata={
            "source_workspace_id": workspace.workspace_id,
            "source_student_id": workspace.student_id,
        },
    )


__all__ = [
    "FRONTEND_STATE_ENGINE_VERSION",
    "build_frontend_pane_states",
    "build_workspace_navigation_state",
    "build_workspace_frontend_state",
]
