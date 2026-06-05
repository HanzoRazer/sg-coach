"""
Practice Queue Engine — Deterministic practice flow management.

Sprint 23: Assignment scheduling and practice queue management.

Provides:
- build_practice_queue(): Create queue from assignments
- queue_priority_for_assignment(): Determine priority from assignment
- sort_practice_queue(): Sort queue by priority and order
- mark_assignment_active(): Transition to active status
- mark_assignment_completed(): Transition to completed status
- mark_assignment_deferred(): Transition to deferred status
- mark_assignment_abandoned(): Transition to abandoned status
- next_queue_assignment(): Get next eligible assignment

Core rules:
- Queue ordering is deterministic
- Queue entries wrap assignments; they do not replace them
- State changes produce events
- Immutable update pattern
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple

from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueEvent,
    PracticeQueueEventType,
    PracticeQueuePriority,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)


QUEUE_VERSION = "0.1.0"

PRIORITY_ORDER = {
    PracticeQueuePriority.critical: 0,
    PracticeQueuePriority.high: 1,
    PracticeQueuePriority.normal: 2,
    PracticeQueuePriority.low: 3,
}


def _generate_queue_id() -> str:
    """Generate queue ID with queue_ prefix."""
    return f"queue_{secrets.token_hex(6)}"


def _generate_scheduled_id() -> str:
    """Generate scheduled entry ID with sq_ prefix."""
    return f"sq_{secrets.token_hex(6)}"


def _generate_event_id() -> str:
    """Generate event ID with pqe_ prefix."""
    return f"pqe_{secrets.token_hex(6)}"


def queue_priority_for_assignment(
    assignment: AssembledPracticeAssignment,
) -> PracticeQueuePriority:
    """
    Determine queue priority from assignment.

    Parameters
    ----------
    assignment:
        The assembled practice assignment.

    Returns
    -------
    PracticeQueuePriority based on assignment status and severity.

    Rules:
    - assignment.status == unresolved → critical
    - assignment.params.get("severity") == "primary" → high
    - assignment.params.get("severity") == "secondary" → normal
    - assignment.params.get("severity") in ["info", "minor"] → low
    - else normal
    """
    if assignment.status == PracticeAssignmentStatus.unresolved:
        return PracticeQueuePriority.critical

    severity = assignment.params.get("severity") if assignment.params else None

    if severity == "primary":
        return PracticeQueuePriority.high
    elif severity == "secondary":
        return PracticeQueuePriority.normal
    elif severity in ("info", "minor"):
        return PracticeQueuePriority.low

    return PracticeQueuePriority.normal


def build_practice_queue(
    *,
    assignments: Sequence[AssembledPracticeAssignment],
    student_id: str | None = None,
    queue_id: str | None = None,
) -> PracticeQueue:
    """
    Build a practice queue from assignments.

    Parameters
    ----------
    assignments:
        Sequence of assembled practice assignments.
    student_id:
        Optional student ID for the queue.
    queue_id:
        Optional queue ID. If None, generates a new one.

    Returns
    -------
    PracticeQueue with scheduled assignments.

    Notes
    -----
    - Generates queue_id and scheduled_id values at build time
    - Preserves input ordering for scheduled_order
    - Determines priority from assignment status/params
    - Extracts estimated_minutes from assignment.params if present
    """
    if queue_id is None:
        queue_id = _generate_queue_id()

    scheduled_assignments: list[ScheduledPracticeAssignment] = []

    for i, assignment in enumerate(assignments):
        estimated_minutes = None
        if assignment.params:
            raw_minutes = assignment.params.get("estimated_minutes")
            if isinstance(raw_minutes, int) and raw_minutes >= 1:
                estimated_minutes = raw_minutes

        scheduled = ScheduledPracticeAssignment(
            scheduled_id=_generate_scheduled_id(),
            queue_id=queue_id,
            assignment_id=assignment.id,
            student_id=student_id,
            diagnosis_code=assignment.diagnosis_code,
            title=assignment.title,
            status=PracticeQueueStatus.queued,
            priority=queue_priority_for_assignment(assignment),
            scheduled_order=i,
            estimated_minutes=estimated_minutes,
            metadata={
                "assignment_type": assignment.assignment_type.value,
            },
        )
        scheduled_assignments.append(scheduled)

    return PracticeQueue(
        id=queue_id,
        student_id=student_id,
        assignments=scheduled_assignments,
    )


def sort_practice_queue(
    queue: PracticeQueue,
) -> PracticeQueue:
    """
    Sort queue assignments by priority and order.

    Parameters
    ----------
    queue:
        The practice queue to sort.

    Returns
    -------
    New PracticeQueue with sorted assignments.

    Sorting order:
    1. priority descending (critical, high, normal, low)
    2. scheduled_order ascending
    3. created_at ascending

    Immutable update.
    """
    sorted_assignments = sorted(
        queue.assignments,
        key=lambda a: (
            PRIORITY_ORDER.get(a.priority, 2),
            a.scheduled_order,
            a.created_at,
        ),
    )

    return PracticeQueue(
        id=queue.id,
        student_id=queue.student_id,
        assignments=sorted_assignments,
        generated_at=queue.generated_at,
        version=queue.version,
    )


def _update_assignment_status(
    queue: PracticeQueue,
    assignment_id: str,
    new_status: PracticeQueueStatus,
    event_type: PracticeQueueEventType,
    *,
    completed_at: datetime | None = None,
    deferred_until: datetime | None = None,
    metadata: dict | None = None,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """Internal helper to update assignment status and create event."""
    updated_assignments: list[ScheduledPracticeAssignment] = []
    found = False

    for assignment in queue.assignments:
        if assignment.assignment_id == assignment_id:
            found = True
            updated = ScheduledPracticeAssignment(
                scheduled_id=assignment.scheduled_id,
                queue_id=assignment.queue_id,
                assignment_id=assignment.assignment_id,
                student_id=assignment.student_id,
                diagnosis_code=assignment.diagnosis_code,
                title=assignment.title,
                status=new_status,
                priority=assignment.priority,
                scheduled_order=assignment.scheduled_order,
                estimated_minutes=assignment.estimated_minutes,
                scheduled_for=assignment.scheduled_for,
                created_at=assignment.created_at,
                completed_at=completed_at if completed_at else assignment.completed_at,
                deferred_until=deferred_until if deferred_until else assignment.deferred_until,
                metadata=assignment.metadata,
                version=assignment.version,
            )
            updated_assignments.append(updated)
        else:
            updated_assignments.append(assignment)

    if not found:
        raise ValueError(f"Assignment not found in queue: {assignment_id}")

    event = PracticeQueueEvent(
        id=_generate_event_id(),
        queue_id=queue.id or "",
        assignment_id=assignment_id,
        event_type=event_type,
        metadata=metadata or {},
    )

    new_queue = PracticeQueue(
        id=queue.id,
        student_id=queue.student_id,
        assignments=updated_assignments,
        generated_at=queue.generated_at,
        version=queue.version,
    )

    return new_queue, event


def mark_assignment_active(
    queue: PracticeQueue,
    assignment_id: str,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """
    Mark an assignment as active.

    Parameters
    ----------
    queue:
        The practice queue.
    assignment_id:
        The assignment to mark active.

    Returns
    -------
    Tuple of (new_queue, event).

    Raises
    ------
    ValueError:
        If assignment not found in queue.
    """
    return _update_assignment_status(
        queue,
        assignment_id,
        PracticeQueueStatus.active,
        PracticeQueueEventType.assignment_started,
    )


def mark_assignment_completed(
    queue: PracticeQueue,
    assignment_id: str,
    *,
    completed_at: datetime | None = None,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """
    Mark an assignment as completed.

    Parameters
    ----------
    queue:
        The practice queue.
    assignment_id:
        The assignment to mark completed.
    completed_at:
        Optional completion timestamp. Defaults to now.

    Returns
    -------
    Tuple of (new_queue, event).

    Raises
    ------
    ValueError:
        If assignment not found in queue.
    """
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)

    return _update_assignment_status(
        queue,
        assignment_id,
        PracticeQueueStatus.completed,
        PracticeQueueEventType.assignment_completed,
        completed_at=completed_at,
    )


def mark_assignment_deferred(
    queue: PracticeQueue,
    assignment_id: str,
    *,
    deferred_until: datetime | None = None,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """
    Mark an assignment as deferred.

    Parameters
    ----------
    queue:
        The practice queue.
    assignment_id:
        The assignment to defer.
    deferred_until:
        Optional datetime when assignment becomes eligible again.

    Returns
    -------
    Tuple of (new_queue, event).

    Raises
    ------
    ValueError:
        If assignment not found in queue.
    """
    return _update_assignment_status(
        queue,
        assignment_id,
        PracticeQueueStatus.deferred,
        PracticeQueueEventType.assignment_deferred,
        deferred_until=deferred_until,
        metadata={"deferred_until": deferred_until.isoformat() if deferred_until else None},
    )


def mark_assignment_abandoned(
    queue: PracticeQueue,
    assignment_id: str,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """
    Mark an assignment as abandoned.

    Parameters
    ----------
    queue:
        The practice queue.
    assignment_id:
        The assignment to abandon.

    Returns
    -------
    Tuple of (new_queue, event).

    Raises
    ------
    ValueError:
        If assignment not found in queue.
    """
    return _update_assignment_status(
        queue,
        assignment_id,
        PracticeQueueStatus.abandoned,
        PracticeQueueEventType.assignment_abandoned,
    )


def next_queue_assignment(
    queue: PracticeQueue,
) -> Optional[ScheduledPracticeAssignment]:
    """
    Get the next eligible assignment from queue.

    Parameters
    ----------
    queue:
        The practice queue.

    Returns
    -------
    Next eligible ScheduledPracticeAssignment, or None if none available.

    Rules:
    1. Sort queue by priority/order
    2. Skip completed assignments
    3. Skip abandoned assignments
    4. Skip deferred assignments with future deferred_until
    5. Return first valid assignment

    Deferred assignments with past deferred_until are eligible.
    """
    sorted_queue = sort_practice_queue(queue)
    now = datetime.now(timezone.utc)

    for assignment in sorted_queue.assignments:
        if assignment.status == PracticeQueueStatus.completed:
            continue

        if assignment.status == PracticeQueueStatus.abandoned:
            continue

        if assignment.status == PracticeQueueStatus.deferred:
            if assignment.deferred_until is not None:
                if assignment.deferred_until > now:
                    continue

        return assignment

    return None


__all__ = [
    "QUEUE_VERSION",
    "build_practice_queue",
    "queue_priority_for_assignment",
    "sort_practice_queue",
    "mark_assignment_active",
    "mark_assignment_completed",
    "mark_assignment_deferred",
    "mark_assignment_abandoned",
    "next_queue_assignment",
]
