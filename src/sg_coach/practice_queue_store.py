"""
Practice Queue Store — Append-only persistence for practice queue events.

Sprint 23: Assignment scheduling and practice queue management.

Provides:
- PracticeQueueStore: JSONL-backed queue persistence

Persistence model:
- Single JSONL file with all events
- Queue state rebuilt from events
- Filter by student_id
- Idempotent assignment scheduling
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueEvent,
    PracticeQueueEventType,
    PracticeQueuePriority,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)


PRACTICE_QUEUE_STORE_VERSION = "0.1.0"


def _generate_event_id() -> str:
    """Generate event ID with pqe_ prefix."""
    return f"pqe_{secrets.token_hex(6)}"


def _generate_queue_id() -> str:
    """Generate queue ID with queue_ prefix."""
    return f"queue_{secrets.token_hex(6)}"


def _generate_scheduled_id() -> str:
    """Generate scheduled entry ID with sq_ prefix."""
    return f"sq_{secrets.token_hex(6)}"


class PracticeQueueStore:
    """
    Append-only JSONL store for practice queue events.

    Usage:
        store = PracticeQueueStore(Path("practice_queue.jsonl"))
        store.schedule_assignment(...)
        queue = store.load_queue(student_id="student_123")
    """

    def __init__(self, path: Path) -> None:
        """
        Initialize store.

        Parameters
        ----------
        path:
            Path to JSONL file.
        """
        self.path = path

    def append_event(self, event: PracticeQueueEvent) -> None:
        """
        Append an event to the store.

        Parameters
        ----------
        event:
            The event to append.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def list_events(
        self,
        *,
        student_id: str | None = None,
        queue_id: str | None = None,
        assignment_id: str | None = None,
    ) -> list[PracticeQueueEvent]:
        """
        List events from store with optional filters.

        Parameters
        ----------
        student_id:
            Filter by student_id in metadata.
        queue_id:
            Filter by queue_id.
        assignment_id:
            Filter by assignment_id.

        Returns
        -------
        List of matching events.
        """
        if not self.path.exists():
            return []

        events: list[PracticeQueueEvent] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                event = PracticeQueueEvent.model_validate(data)

                if queue_id is not None and event.queue_id != queue_id:
                    continue
                if assignment_id is not None and event.assignment_id != assignment_id:
                    continue
                if student_id is not None:
                    event_student_id = event.metadata.get("student_id")
                    if event_student_id != student_id:
                        continue

                events.append(event)

        return events

    def schedule_assignment(
        self,
        *,
        assignment_id: str,
        title: str,
        queue_id: str | None = None,
        student_id: str | None = None,
        priority: PracticeQueuePriority = PracticeQueuePriority.normal,
        scheduled_order: int = 0,
        estimated_minutes: int | None = None,
        diagnosis_code: str | None = None,
    ) -> PracticeQueueEvent:
        """
        Schedule an assignment (create assignment_scheduled event).

        Parameters
        ----------
        assignment_id:
            The assignment ID to schedule.
        title:
            Assignment title.
        queue_id:
            Optional queue ID. Generates if None.
        student_id:
            Optional student ID.
        priority:
            Queue priority.
        scheduled_order:
            Position in queue.
        estimated_minutes:
            Optional estimated duration.
        diagnosis_code:
            Optional diagnosis code.

        Returns
        -------
        The created event.

        Notes
        -----
        Idempotent: if assignment_id already scheduled in queue, returns
        existing event without creating duplicate.
        """
        if queue_id is None:
            queue_id = _generate_queue_id()

        existing_events = self.list_events(
            queue_id=queue_id,
            assignment_id=assignment_id,
        )
        for evt in existing_events:
            if evt.event_type == PracticeQueueEventType.assignment_scheduled:
                return evt

        event = PracticeQueueEvent(
            id=_generate_event_id(),
            queue_id=queue_id,
            assignment_id=assignment_id,
            event_type=PracticeQueueEventType.assignment_scheduled,
            metadata={
                "title": title,
                "student_id": student_id,
                "priority": priority.value,
                "scheduled_order": scheduled_order,
                "estimated_minutes": estimated_minutes,
                "diagnosis_code": diagnosis_code,
                "scheduled_id": _generate_scheduled_id(),
            },
        )
        self.append_event(event)
        return event

    def mark_started(
        self,
        *,
        queue_id: str,
        assignment_id: str,
    ) -> PracticeQueueEvent:
        """
        Mark an assignment as started.

        Parameters
        ----------
        queue_id:
            The queue ID.
        assignment_id:
            The assignment ID.

        Returns
        -------
        The created event.
        """
        event = PracticeQueueEvent(
            id=_generate_event_id(),
            queue_id=queue_id,
            assignment_id=assignment_id,
            event_type=PracticeQueueEventType.assignment_started,
        )
        self.append_event(event)
        return event

    def mark_completed(
        self,
        *,
        queue_id: str,
        assignment_id: str,
        completed_at: datetime | None = None,
    ) -> PracticeQueueEvent:
        """
        Mark an assignment as completed.

        Parameters
        ----------
        queue_id:
            The queue ID.
        assignment_id:
            The assignment ID.
        completed_at:
            Optional completion timestamp.

        Returns
        -------
        The created event.
        """
        if completed_at is None:
            completed_at = datetime.now(timezone.utc)

        event = PracticeQueueEvent(
            id=_generate_event_id(),
            queue_id=queue_id,
            assignment_id=assignment_id,
            event_type=PracticeQueueEventType.assignment_completed,
            metadata={"completed_at": completed_at.isoformat()},
        )
        self.append_event(event)
        return event

    def mark_deferred(
        self,
        *,
        queue_id: str,
        assignment_id: str,
        deferred_until: datetime | None = None,
    ) -> PracticeQueueEvent:
        """
        Mark an assignment as deferred.

        Parameters
        ----------
        queue_id:
            The queue ID.
        assignment_id:
            The assignment ID.
        deferred_until:
            Optional datetime when assignment becomes eligible.

        Returns
        -------
        The created event.
        """
        event = PracticeQueueEvent(
            id=_generate_event_id(),
            queue_id=queue_id,
            assignment_id=assignment_id,
            event_type=PracticeQueueEventType.assignment_deferred,
            metadata={
                "deferred_until": deferred_until.isoformat() if deferred_until else None
            },
        )
        self.append_event(event)
        return event

    def mark_abandoned(
        self,
        *,
        queue_id: str,
        assignment_id: str,
    ) -> PracticeQueueEvent:
        """
        Mark an assignment as abandoned.

        Parameters
        ----------
        queue_id:
            The queue ID.
        assignment_id:
            The assignment ID.

        Returns
        -------
        The created event.
        """
        event = PracticeQueueEvent(
            id=_generate_event_id(),
            queue_id=queue_id,
            assignment_id=assignment_id,
            event_type=PracticeQueueEventType.assignment_abandoned,
        )
        self.append_event(event)
        return event

    def load_queue(
        self,
        *,
        queue_id: str | None = None,
        student_id: str | None = None,
    ) -> PracticeQueue:
        """
        Load queue by rebuilding from events.

        Parameters
        ----------
        queue_id:
            Optional queue ID to load. If None, builds from all events.
        student_id:
            Optional student ID filter.

        Returns
        -------
        Rebuilt PracticeQueue.

        Notes
        -----
        Rebuild rules:
        - assignment_scheduled → create queued item
        - assignment_started → active
        - assignment_completed → completed
        - assignment_deferred → deferred
        - assignment_abandoned → abandoned

        Idempotent: duplicate schedule events for same assignment_id ignored.
        """
        events = self.list_events(queue_id=queue_id, student_id=student_id)

        assignments_by_id: dict[str, ScheduledPracticeAssignment] = {}
        resolved_queue_id: str | None = queue_id
        resolved_student_id: str | None = student_id

        for event in events:
            if resolved_queue_id is None:
                resolved_queue_id = event.queue_id

            if event.event_type == PracticeQueueEventType.assignment_scheduled:
                if event.assignment_id in assignments_by_id:
                    continue

                metadata = event.metadata
                scheduled_id = metadata.get("scheduled_id", _generate_scheduled_id())
                title = metadata.get("title", "Untitled")
                event_student_id = metadata.get("student_id")
                priority_str = metadata.get("priority", "normal")
                scheduled_order = metadata.get("scheduled_order", 0)
                estimated_minutes = metadata.get("estimated_minutes")
                diagnosis_code_str = metadata.get("diagnosis_code")

                if resolved_student_id is None and event_student_id:
                    resolved_student_id = event_student_id

                try:
                    priority = PracticeQueuePriority(priority_str)
                except ValueError:
                    priority = PracticeQueuePriority.normal

                from sg_spec.schemas.adaptive_feedback import DiagnosisCode
                diagnosis_code = None
                if diagnosis_code_str:
                    try:
                        diagnosis_code = DiagnosisCode(diagnosis_code_str)
                    except ValueError:
                        pass

                assignment = ScheduledPracticeAssignment(
                    scheduled_id=scheduled_id,
                    queue_id=event.queue_id,
                    assignment_id=event.assignment_id,
                    student_id=event_student_id,
                    diagnosis_code=diagnosis_code,
                    title=title,
                    status=PracticeQueueStatus.queued,
                    priority=priority,
                    scheduled_order=scheduled_order,
                    estimated_minutes=estimated_minutes if estimated_minutes and estimated_minutes >= 1 else None,
                    created_at=event.timestamp,
                )
                assignments_by_id[event.assignment_id] = assignment

            elif event.event_type == PracticeQueueEventType.assignment_started:
                if event.assignment_id in assignments_by_id:
                    old = assignments_by_id[event.assignment_id]
                    assignments_by_id[event.assignment_id] = ScheduledPracticeAssignment(
                        scheduled_id=old.scheduled_id,
                        queue_id=old.queue_id,
                        assignment_id=old.assignment_id,
                        student_id=old.student_id,
                        diagnosis_code=old.diagnosis_code,
                        title=old.title,
                        status=PracticeQueueStatus.active,
                        priority=old.priority,
                        scheduled_order=old.scheduled_order,
                        estimated_minutes=old.estimated_minutes,
                        scheduled_for=old.scheduled_for,
                        created_at=old.created_at,
                        completed_at=old.completed_at,
                        deferred_until=old.deferred_until,
                        metadata=old.metadata,
                        version=old.version,
                    )

            elif event.event_type == PracticeQueueEventType.assignment_completed:
                if event.assignment_id in assignments_by_id:
                    old = assignments_by_id[event.assignment_id]
                    completed_at_str = event.metadata.get("completed_at")
                    completed_at = None
                    if completed_at_str:
                        try:
                            completed_at = datetime.fromisoformat(completed_at_str)
                        except ValueError:
                            completed_at = event.timestamp
                    else:
                        completed_at = event.timestamp

                    assignments_by_id[event.assignment_id] = ScheduledPracticeAssignment(
                        scheduled_id=old.scheduled_id,
                        queue_id=old.queue_id,
                        assignment_id=old.assignment_id,
                        student_id=old.student_id,
                        diagnosis_code=old.diagnosis_code,
                        title=old.title,
                        status=PracticeQueueStatus.completed,
                        priority=old.priority,
                        scheduled_order=old.scheduled_order,
                        estimated_minutes=old.estimated_minutes,
                        scheduled_for=old.scheduled_for,
                        created_at=old.created_at,
                        completed_at=completed_at,
                        deferred_until=old.deferred_until,
                        metadata=old.metadata,
                        version=old.version,
                    )

            elif event.event_type == PracticeQueueEventType.assignment_deferred:
                if event.assignment_id in assignments_by_id:
                    old = assignments_by_id[event.assignment_id]
                    deferred_until_str = event.metadata.get("deferred_until")
                    deferred_until = None
                    if deferred_until_str:
                        try:
                            deferred_until = datetime.fromisoformat(deferred_until_str)
                        except ValueError:
                            pass

                    assignments_by_id[event.assignment_id] = ScheduledPracticeAssignment(
                        scheduled_id=old.scheduled_id,
                        queue_id=old.queue_id,
                        assignment_id=old.assignment_id,
                        student_id=old.student_id,
                        diagnosis_code=old.diagnosis_code,
                        title=old.title,
                        status=PracticeQueueStatus.deferred,
                        priority=old.priority,
                        scheduled_order=old.scheduled_order,
                        estimated_minutes=old.estimated_minutes,
                        scheduled_for=old.scheduled_for,
                        created_at=old.created_at,
                        completed_at=old.completed_at,
                        deferred_until=deferred_until,
                        metadata=old.metadata,
                        version=old.version,
                    )

            elif event.event_type == PracticeQueueEventType.assignment_abandoned:
                if event.assignment_id in assignments_by_id:
                    old = assignments_by_id[event.assignment_id]
                    assignments_by_id[event.assignment_id] = ScheduledPracticeAssignment(
                        scheduled_id=old.scheduled_id,
                        queue_id=old.queue_id,
                        assignment_id=old.assignment_id,
                        student_id=old.student_id,
                        diagnosis_code=old.diagnosis_code,
                        title=old.title,
                        status=PracticeQueueStatus.abandoned,
                        priority=old.priority,
                        scheduled_order=old.scheduled_order,
                        estimated_minutes=old.estimated_minutes,
                        scheduled_for=old.scheduled_for,
                        created_at=old.created_at,
                        completed_at=old.completed_at,
                        deferred_until=old.deferred_until,
                        metadata=old.metadata,
                        version=old.version,
                    )

        assignments_list = sorted(
            assignments_by_id.values(),
            key=lambda a: (a.scheduled_order, a.created_at),
        )

        return PracticeQueue(
            id=resolved_queue_id,
            student_id=resolved_student_id,
            assignments=assignments_list,
        )


__all__ = [
    "PRACTICE_QUEUE_STORE_VERSION",
    "PracticeQueueStore",
]
