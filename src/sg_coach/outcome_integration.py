"""
Outcome Integration — Connect assignment outcomes to queue and progression.

Sprint 24: Session-to-queue outcome integration.

Provides:
- process_assignment_outcome(): Main integration function
- outcome_to_queue_status(): Map outcome to queue status
- should_advance_curriculum(): Check if outcome advances progression

Core rules:
- Integration is pure (no store writes)
- Returns updated state objects
- Graceful failure with reasons
- No autonomous scheduling
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.curriculum_progression import (
    CurriculumProgressState,
    CurriculumRecommendation,
)
from sg_spec.schemas.outcome_integration import AssignmentOutcomeProcessingResult
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueEvent,
    PracticeQueueEventType,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_curriculum import get_next_curriculum_step, mark_content_completed


OUTCOME_INTEGRATION_VERSION = "0.1.0"


def _generate_event_id() -> str:
    """Generate event ID with pqe_ prefix."""
    return f"pqe_{secrets.token_hex(6)}"


def outcome_to_queue_status(
    outcome: PracticeOutcome,
) -> Optional[PracticeQueueStatus]:
    """
    Map practice outcome to queue status.

    Parameters
    ----------
    outcome:
        The practice outcome.

    Returns
    -------
    New queue status, or None if no status change.

    Mapping:
    - completed → queue completed
    - improved → queue completed
    - abandoned → queue abandoned
    - worsened → None (stays active)
    - repeated → None (stays active)
    """
    if outcome == PracticeOutcome.completed:
        return PracticeQueueStatus.completed
    elif outcome == PracticeOutcome.improved:
        return PracticeQueueStatus.completed
    elif outcome == PracticeOutcome.abandoned:
        return PracticeQueueStatus.abandoned
    elif outcome == PracticeOutcome.worsened:
        return None
    elif outcome == PracticeOutcome.repeated:
        return None
    return None


def should_advance_curriculum(outcome: PracticeOutcome) -> bool:
    """
    Check if outcome should advance curriculum progression.

    Parameters
    ----------
    outcome:
        The practice outcome.

    Returns
    -------
    True if curriculum should advance.

    Rules:
    - completed → advance
    - improved → advance
    - repeated → do not advance
    - worsened → do not advance
    - abandoned → do not advance
    """
    return outcome in (PracticeOutcome.completed, PracticeOutcome.improved)


def _find_assignment_in_queue(
    queue: PracticeQueue,
    assignment_id: str,
) -> Optional[ScheduledPracticeAssignment]:
    """Find a scheduled assignment in the queue by assignment_id."""
    for scheduled in queue.assignments:
        if scheduled.assignment_id == assignment_id:
            return scheduled
    return None


def _update_queue_assignment_status(
    queue: PracticeQueue,
    assignment_id: str,
    new_status: PracticeQueueStatus,
    event_type: PracticeQueueEventType,
    *,
    completed_at: datetime | None = None,
) -> Tuple[PracticeQueue, PracticeQueueEvent]:
    """Update assignment status in queue and create event."""
    updated_assignments: list[ScheduledPracticeAssignment] = []

    for scheduled in queue.assignments:
        if scheduled.assignment_id == assignment_id:
            updated = ScheduledPracticeAssignment(
                scheduled_id=scheduled.scheduled_id,
                queue_id=scheduled.queue_id,
                assignment_id=scheduled.assignment_id,
                student_id=scheduled.student_id,
                diagnosis_code=scheduled.diagnosis_code,
                title=scheduled.title,
                status=new_status,
                priority=scheduled.priority,
                scheduled_order=scheduled.scheduled_order,
                estimated_minutes=scheduled.estimated_minutes,
                scheduled_for=scheduled.scheduled_for,
                created_at=scheduled.created_at,
                completed_at=completed_at if completed_at else scheduled.completed_at,
                deferred_until=scheduled.deferred_until,
                metadata=scheduled.metadata,
                version=scheduled.version,
            )
            updated_assignments.append(updated)
        else:
            updated_assignments.append(scheduled)

    event = PracticeQueueEvent(
        id=_generate_event_id(),
        queue_id=queue.id or "",
        assignment_id=assignment_id,
        event_type=event_type,
    )

    new_queue = PracticeQueue(
        id=queue.id,
        student_id=queue.student_id,
        assignments=updated_assignments,
        generated_at=queue.generated_at,
        version=queue.version,
    )

    return new_queue, event


def process_assignment_outcome(
    *,
    assignment: AssembledPracticeAssignment,
    outcome_event: AssignmentOutcomeEvent,
    queue: PracticeQueue,
    progress_state: CurriculumProgressState,
) -> AssignmentOutcomeProcessingResult:
    """
    Process an assignment outcome across queue and progression.

    Parameters
    ----------
    assignment:
        The assembled practice assignment.
    outcome_event:
        The outcome event to process.
    queue:
        Current practice queue.
    progress_state:
        Current curriculum progress state.

    Returns
    -------
    AssignmentOutcomeProcessingResult with updated state.

    Notes
    -----
    This function is pure — it does not write to stores.
    Caller is responsible for persisting returned events/state.

    Processing rules:
    1. Validate assignment exists in queue
    2. Map outcome to queue status
    3. Update queue if status changes
    4. Check if curriculum should advance
    5. Advance curriculum if applicable
    6. Get next curriculum step if advanced
    """
    reasons: list[str] = []
    updated_queue = queue
    updated_progress = progress_state
    queue_event: Optional[PracticeQueueEvent] = None
    curriculum_recommendation: Optional[CurriculumRecommendation] = None
    advanced_curriculum = False

    scheduled = _find_assignment_in_queue(queue, assignment.id)
    if scheduled is None:
        return AssignmentOutcomeProcessingResult(
            processed=False,
            assignment_id=assignment.id,
            outcome_event_id=outcome_event.id,
            updated_queue=queue,
            updated_progress_state=progress_state,
            queue_event=None,
            curriculum_recommendation=None,
            advanced_curriculum=False,
            reasons=["assignment_not_in_queue"],
        )

    outcome = outcome_event.outcome
    new_status = outcome_to_queue_status(outcome)

    if new_status is not None:
        completed_at = None
        if new_status == PracticeQueueStatus.completed:
            completed_at = datetime.now(timezone.utc)
            event_type = PracticeQueueEventType.assignment_completed
        elif new_status == PracticeQueueStatus.abandoned:
            event_type = PracticeQueueEventType.assignment_abandoned
        else:
            event_type = PracticeQueueEventType.assignment_completed

        updated_queue, queue_event = _update_queue_assignment_status(
            queue,
            assignment.id,
            new_status,
            event_type,
            completed_at=completed_at,
        )

    if should_advance_curriculum(outcome):
        content_id = None
        if assignment.params:
            content_id = assignment.params.get("curriculum_content_id")

        if content_id is None:
            reasons.append("missing_curriculum_content_id")
        elif assignment.diagnosis_code is None:
            reasons.append("missing_diagnosis_code")
        else:
            updated_progress = mark_content_completed(
                progress_state,
                content_id,
            )
            advanced_curriculum = True

            try:
                curriculum_recommendation = get_next_curriculum_step(
                    diagnosis_code=assignment.diagnosis_code,
                    progress_state=updated_progress,
                )
                if curriculum_recommendation is None:
                    reasons.append("no_next_curriculum_step")
            except Exception:
                reasons.append("curriculum_lookup_failed")

    return AssignmentOutcomeProcessingResult(
        processed=True,
        assignment_id=assignment.id,
        outcome_event_id=outcome_event.id,
        updated_queue=updated_queue,
        updated_progress_state=updated_progress,
        queue_event=queue_event,
        curriculum_recommendation=curriculum_recommendation,
        advanced_curriculum=advanced_curriculum,
        reasons=reasons,
    )


__all__ = [
    "OUTCOME_INTEGRATION_VERSION",
    "outcome_to_queue_status",
    "should_advance_curriculum",
    "process_assignment_outcome",
]
