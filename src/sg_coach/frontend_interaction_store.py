"""
Frontend Interaction Event Store.

Sprint 39: Frontend Interaction Event Contract.

Provides:
- FrontendInteractionStore: Append-only JSONL store for interaction events

Core rules:
- Events are append-only
- Events can be filtered by workspace_id or frontend_state_id
- Event replay must be reproducible
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from sg_spec.schemas.frontend_interaction import FrontendInteractionEvent
from sg_spec.schemas.frontend_state import WorkspaceFrontendState

from .frontend_interaction import apply_frontend_interaction


FRONTEND_INTERACTION_STORE_VERSION = "0.1.0"


class FrontendInteractionStore:
    """
    Append-only JSONL store for frontend interaction events.

    Events are stored one per line in JSONL format.
    """

    def __init__(self, path: Path) -> None:
        """
        Initialize the store.

        Parameters
        ----------
        path:
            Path to the JSONL file.
        """
        self.path = path

    def append_event(self, event: FrontendInteractionEvent) -> None:
        """
        Append an event to the store.

        Parameters
        ----------
        event:
            The event to append.
        """
        with self.path.open("a", encoding="utf-8") as f:
            line = json.dumps(event.model_dump(mode="json"), default=str)
            f.write(line + "\n")

    def list_events(
        self,
        *,
        workspace_id: str | None = None,
        frontend_state_id: str | None = None,
    ) -> list[FrontendInteractionEvent]:
        """
        List events, optionally filtered.

        Parameters
        ----------
        workspace_id:
            If provided, only return events matching this workspace ID.
        frontend_state_id:
            If provided, only return events matching this frontend state ID.

        Returns
        -------
        List of matching events in chronological order.
        """
        if not self.path.exists():
            return []

        events: list[FrontendInteractionEvent] = []

        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    event = FrontendInteractionEvent.model_validate(data)

                    if workspace_id is not None:
                        if event.workspace_id != workspace_id:
                            continue

                    if frontend_state_id is not None:
                        if event.frontend_state_id != frontend_state_id:
                            continue

                    events.append(event)
                except (json.JSONDecodeError, ValueError):
                    continue

        return events

    def replay_events(
        self,
        initial_state: WorkspaceFrontendState,
        events: Sequence[FrontendInteractionEvent],
    ) -> WorkspaceFrontendState:
        """
        Replay a sequence of events to produce final state.

        Parameters
        ----------
        initial_state:
            The starting frontend state.
        events:
            The events to replay in order.

        Returns
        -------
        The final WorkspaceFrontendState after all events.
        """
        current_state = initial_state

        for event in events:
            current_state = apply_frontend_interaction(
                state=current_state,
                event=event,
            )

        return current_state

    def clear(self) -> None:
        """Clear all events from the store."""
        if self.path.exists():
            self.path.unlink()

    def count(self) -> int:
        """Count total events in the store."""
        if not self.path.exists():
            return 0

        count = 0
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1

        return count


__all__ = [
    "FRONTEND_INTERACTION_STORE_VERSION",
    "FrontendInteractionStore",
]
