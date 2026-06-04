"""
Runtime Flow Store — Append-only JSONL store for runtime session events.

Sprint 25: Queue-to-runtime practice session flow.

Provides:
- RuntimeFlowStore: Event-sourced store for runtime session audit

Core rules:
- Append-only JSONL format
- Single file: runtime_events.jsonl
- Filter by runtime_session_id
- Does NOT store queue events or progress state
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sg_spec.schemas.runtime_flow import (
    RuntimeSessionEvent,
    RuntimeSessionEventType,
)


RUNTIME_FLOW_STORE_VERSION = "0.1.0"


class RuntimeFlowStore:
    """
    Append-only JSONL store for runtime session events.

    Stores events to runtime_events.jsonl.
    Provides filtering by runtime_session_id.

    Does NOT store:
    - PracticeQueue or PracticeQueueEvent (use PracticeQueueStore)
    - CurriculumProgressState
    - RuntimeSessionResult
    """

    def __init__(self, base_dir: Path | str) -> None:
        """
        Initialize the runtime flow store.

        Parameters
        ----------
        base_dir:
            Base directory for store files.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def events_file(self) -> Path:
        """Path to the runtime events JSONL file."""
        return self.base_dir / "runtime_events.jsonl"

    def append_event(self, event: RuntimeSessionEvent) -> None:
        """
        Append a runtime session event to the store.

        Parameters
        ----------
        event:
            The runtime session event to append.
        """
        event_dict = event.model_dump(mode="json")

        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_dict) + "\n")

    def list_events(
        self,
        *,
        runtime_session_id: Optional[str] = None,
    ) -> List[RuntimeSessionEvent]:
        """
        List runtime session events with optional filtering.

        Parameters
        ----------
        runtime_session_id:
            Filter by runtime session ID (optional).

        Returns
        -------
        List of matching RuntimeSessionEvent objects.
        """
        if not self.events_file.exists():
            return []

        events: List[RuntimeSessionEvent] = []

        with open(self.events_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    event = RuntimeSessionEvent(**data)

                    if runtime_session_id is not None:
                        if event.runtime_session_id != runtime_session_id:
                            continue

                    events.append(event)
                except (json.JSONDecodeError, Exception):
                    continue

        return events

    def load_runtime_session_events(
        self,
        runtime_session_id: str,
    ) -> List[RuntimeSessionEvent]:
        """
        Load all events for a specific runtime session.

        Parameters
        ----------
        runtime_session_id:
            The runtime session ID to filter by.

        Returns
        -------
        List of RuntimeSessionEvent objects for the session.
        """
        return self.list_events(runtime_session_id=runtime_session_id)

    def get_latest_event(
        self,
        runtime_session_id: str,
    ) -> Optional[RuntimeSessionEvent]:
        """
        Get the most recent event for a runtime session.

        Parameters
        ----------
        runtime_session_id:
            The runtime session ID.

        Returns
        -------
        The most recent event, or None if no events exist.
        """
        events = self.load_runtime_session_events(runtime_session_id)
        if not events:
            return None
        return events[-1]

    def get_session_status(
        self,
        runtime_session_id: str,
    ) -> Optional[RuntimeSessionEventType]:
        """
        Get the current status of a runtime session based on events.

        Parameters
        ----------
        runtime_session_id:
            The runtime session ID.

        Returns
        -------
        The event type of the latest event, or None if no events.
        """
        latest = self.get_latest_event(runtime_session_id)
        if latest is None:
            return None
        return latest.event_type


__all__ = [
    "RUNTIME_FLOW_STORE_VERSION",
    "RuntimeFlowStore",
]
