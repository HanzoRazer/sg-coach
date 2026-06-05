"""
Frontend Interaction Event Engine.

Sprint 39: Frontend Interaction Event Contract.

Provides:
- apply_frontend_interaction(): Apply an interaction event to frontend state
- generate_event_id(): Generate unique event ID

Core rules:
- Interaction events describe UI intent only
- Interaction events never mutate pedagogical evidence
- Frontend state updates remain deterministic
- Event replay must be reproducible
- Framework-specific browser events are out of scope
"""
from __future__ import annotations

import secrets
from typing import Any

from sg_spec.schemas.frontend_interaction import (
    FrontendInteractionEvent,
    FrontendInteractionType,
)
from sg_spec.schemas.frontend_state import (
    FrontendPaneState,
    WorkspaceFrontendState,
    WorkspaceNavigationState,
)


FRONTEND_INTERACTION_ENGINE_VERSION = "0.1.0"


def generate_event_id() -> str:
    """Generate unique event ID."""
    return f"fie_{secrets.token_hex(6)}"


def _add_warning(
    metadata: dict[str, Any],
    event: FrontendInteractionEvent,
    warning: str,
    target_id: str | None = None,
) -> dict[str, Any]:
    """Add warning to metadata's interaction_warnings list."""
    new_metadata = dict(metadata)
    warnings = list(new_metadata.get("interaction_warnings", []))

    warning_entry: dict[str, Any] = {
        "event_id": event.event_id,
        "interaction_type": event.interaction_type.value,
        "warning": warning,
    }
    if target_id is not None:
        warning_entry["target_id"] = target_id

    warnings.append(warning_entry)
    new_metadata["interaction_warnings"] = warnings
    return new_metadata


def _check_id_mismatch(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> tuple[bool, dict[str, Any] | None]:
    """Check for frontend_state_id or workspace_id mismatch.

    Returns (has_mismatch, warning_metadata).
    """
    if event.frontend_state_id is not None:
        if event.frontend_state_id != state.frontend_state_id:
            warning_metadata = _add_warning(
                state.metadata,
                event,
                "frontend_state_id_mismatch",
                event.frontend_state_id,
            )
            return True, warning_metadata

    if event.workspace_id is not None:
        if event.workspace_id != state.workspace_id:
            warning_metadata = _add_warning(
                state.metadata,
                event,
                "workspace_id_mismatch",
                event.workspace_id,
            )
            return True, warning_metadata

    return False, None


def _apply_select_pane(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply select_pane interaction."""
    if event.pane_id is None:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_required",
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    pane_found = False
    pane_visible = False

    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            pane_found = True
            pane_visible = pane_state.visible
            break

    if not pane_found:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_not_found",
            event.pane_id,
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    if not pane_visible:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_not_visible",
            event.pane_id,
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    new_pane_states = []
    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            new_pane_states.append(
                pane_state.model_copy(update={"selected": True})
            )
        else:
            new_pane_states.append(
                pane_state.model_copy(update={"selected": False})
            )

    new_navigation = state.navigation.model_copy(
        update={"active_pane_id": event.pane_id}
    )

    return state.model_copy(
        deep=True,
        update={
            "pane_states": new_pane_states,
            "navigation": new_navigation,
            "generated_at": event.timestamp,
        },
    )


def _apply_expand_pane(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply expand_pane interaction."""
    if event.pane_id is None:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_required",
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    pane_found = False
    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            pane_found = True
            break

    if not pane_found:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_not_found",
            event.pane_id,
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    new_pane_states = []
    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            new_pane_states.append(
                pane_state.model_copy(update={"expanded": True})
            )
        else:
            new_pane_states.append(pane_state.model_copy())

    return state.model_copy(
        deep=True,
        update={
            "pane_states": new_pane_states,
            "generated_at": event.timestamp,
        },
    )


def _apply_collapse_pane(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply collapse_pane interaction."""
    if event.pane_id is None:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_required",
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    pane_found = False
    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            pane_found = True
            break

    if not pane_found:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "pane_id_not_found",
            event.pane_id,
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    new_pane_states = []
    for pane_state in state.pane_states:
        if pane_state.pane_id == event.pane_id:
            new_pane_states.append(
                pane_state.model_copy(update={"expanded": False})
            )
        else:
            new_pane_states.append(pane_state.model_copy())

    return state.model_copy(
        deep=True,
        update={
            "pane_states": new_pane_states,
            "generated_at": event.timestamp,
        },
    )


def _apply_select_evidence(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply select_evidence interaction."""
    new_navigation = state.navigation.model_copy(
        update={"selected_evidence_id": event.evidence_id}
    )

    return state.model_copy(
        deep=True,
        update={
            "navigation": new_navigation,
            "generated_at": event.timestamp,
        },
    )


def _apply_select_timeline_event(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply select_timeline_event interaction."""
    new_navigation = state.navigation.model_copy(
        update={"selected_timeline_event_id": event.timeline_event_id}
    )

    return state.model_copy(
        deep=True,
        update={
            "navigation": new_navigation,
            "generated_at": event.timestamp,
        },
    )


def _apply_clear_selection(
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """Apply clear_selection interaction."""
    new_navigation = state.navigation.model_copy(
        update={
            "focused_section_id": None,
            "selected_evidence_id": None,
            "selected_timeline_event_id": None,
        }
    )

    return state.model_copy(
        deep=True,
        update={
            "navigation": new_navigation,
            "generated_at": event.timestamp,
        },
    )


def apply_frontend_interaction(
    *,
    state: WorkspaceFrontendState,
    event: FrontendInteractionEvent,
) -> WorkspaceFrontendState:
    """
    Apply an interaction event to frontend state.

    Parameters
    ----------
    state:
        The current frontend state.
    event:
        The interaction event to apply.

    Returns
    -------
    WorkspaceFrontendState with the interaction applied.

    Notes
    -----
    - Does not mutate the source state
    - Returns unchanged state with warning on invalid targets
    - Keeps the same frontend_state_id
    - Updates generated_at to event timestamp
    """
    has_mismatch, warning_metadata = _check_id_mismatch(state, event)
    if has_mismatch:
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )

    if event.interaction_type == FrontendInteractionType.select_pane:
        return _apply_select_pane(state, event)
    elif event.interaction_type == FrontendInteractionType.expand_pane:
        return _apply_expand_pane(state, event)
    elif event.interaction_type == FrontendInteractionType.collapse_pane:
        return _apply_collapse_pane(state, event)
    elif event.interaction_type == FrontendInteractionType.select_evidence:
        return _apply_select_evidence(state, event)
    elif event.interaction_type == FrontendInteractionType.select_timeline_event:
        return _apply_select_timeline_event(state, event)
    elif event.interaction_type == FrontendInteractionType.clear_selection:
        return _apply_clear_selection(state, event)
    else:
        warning_metadata = _add_warning(
            state.metadata,
            event,
            "unknown_interaction_type",
        )
        return state.model_copy(
            deep=True,
            update={"metadata": warning_metadata, "generated_at": event.timestamp},
        )


__all__ = [
    "FRONTEND_INTERACTION_ENGINE_VERSION",
    "generate_event_id",
    "apply_frontend_interaction",
]
