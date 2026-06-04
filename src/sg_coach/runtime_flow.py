"""
Runtime Flow Engine — Queue-to-runtime practice session orchestration.

Sprint 25: Queue-to-runtime practice session flow.
Sprint 26: Runtime session evaluation attachment.

Provides:
- start_runtime_session(): Start a runtime session from a scheduled assignment
- complete_runtime_session(): Complete a session with an outcome
- abandon_runtime_session(): Abandon a session without outcome integration
- start_next_queue_assignment(): Start the next available assignment from queue
- attach_session_record(): Attach SessionRecord evidence to runtime session
- attach_evaluation(): Attach CoachEvaluation evidence to runtime session
- attach_runtime_evidence(): Attach both SessionRecord and CoachEvaluation
- runtime_session_has_evidence(): Check if runtime session has full evidence

Core rules:
- All functions are pure orchestration helpers
- Caller is responsible for persisting state
- Runtime sessions wrap queue execution, not SessionRecord
- Abandonment bypasses outcome integration
- Evidence attachment is explicit, not automatic
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.coach_schemas import CoachEvaluation, SessionRecord
from sg_spec.schemas.curriculum_progression import CurriculumProgressState
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueEvent,
    PracticeQueueEventType,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.runtime_flow import (
    RuntimeEvidenceAttachmentResult,
    RuntimePracticeSession,
    RuntimeSessionEvent,
    RuntimeSessionEventType,
    RuntimeSessionResult,
    RuntimeSessionStatus,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from .outcome_integration import process_assignment_outcome
from .practice_queue import mark_assignment_abandoned, mark_assignment_active, next_queue_assignment

from sg_spec.schemas.runtime_flow import _rebuild_models
_rebuild_models()


RUNTIME_FLOW_VERSION = "0.2.0"


def _generate_runtime_session_id() -> str:
    """Generate runtime session ID with rts_ prefix."""
    return f"rts_{secrets.token_hex(6)}"


def _generate_runtime_event_id() -> str:
    """Generate runtime event ID with rse_ prefix."""
    return f"rse_{secrets.token_hex(6)}"


def _generate_outcome_event_id() -> str:
    """Generate outcome event ID with aoe_ prefix."""
    return f"aoe_{secrets.token_hex(6)}"


def _find_scheduled_assignment(
    queue: PracticeQueue,
    scheduled_id: str,
) -> Optional[ScheduledPracticeAssignment]:
    """Find a scheduled assignment in the queue by scheduled_id."""
    for scheduled in queue.assignments:
        if scheduled.scheduled_id == scheduled_id:
            return scheduled
    return None


def start_runtime_session(
    *,
    queue: PracticeQueue,
    scheduled_assignment: ScheduledPracticeAssignment,
    assignment_lookup: Callable[[str], Optional[AssembledPracticeAssignment]],
) -> Tuple[RuntimePracticeSession, PracticeQueue, PracticeQueueEvent, RuntimeSessionEvent]:
    """
    Start a runtime practice session from a scheduled assignment.

    Parameters
    ----------
    queue:
        Current practice queue.
    scheduled_assignment:
        The scheduled assignment to start.
    assignment_lookup:
        Callable to look up AssembledPracticeAssignment by assignment_id.

    Returns
    -------
    Tuple of:
    - RuntimePracticeSession: The created runtime session
    - PracticeQueue: Updated queue with assignment marked active
    - PracticeQueueEvent: Queue event for assignment activation
    - RuntimeSessionEvent: Runtime event for session start

    Raises
    ------
    ValueError:
        If assignment_lookup returns None.

    Notes
    -----
    This function is pure — caller is responsible for persisting
    the returned queue and events.
    """
    assignment = assignment_lookup(scheduled_assignment.assignment_id)
    if assignment is None:
        raise ValueError("assignment_not_found")

    found = _find_scheduled_assignment(queue, scheduled_assignment.scheduled_id)
    if found is None:
        raise ValueError("scheduled_assignment_not_in_queue")

    updated_queue, queue_event = mark_assignment_active(
        queue,
        scheduled_assignment.assignment_id,
    )

    now = datetime.now(timezone.utc)
    runtime_session_id = _generate_runtime_session_id()

    runtime_session = RuntimePracticeSession(
        runtime_session_id=runtime_session_id,
        queue_id=queue.id or "",
        scheduled_id=scheduled_assignment.scheduled_id,
        assignment_id=scheduled_assignment.assignment_id,
        student_id=scheduled_assignment.student_id,
        status=RuntimeSessionStatus.active,
        started_at=now,
        assignment=assignment,
    )

    runtime_event = RuntimeSessionEvent(
        id=_generate_runtime_event_id(),
        runtime_session_id=runtime_session_id,
        event_type=RuntimeSessionEventType.session_started,
        timestamp=now,
    )

    return runtime_session, updated_queue, queue_event, runtime_event


def complete_runtime_session(
    *,
    runtime_session: RuntimePracticeSession,
    outcome: PracticeOutcome,
    queue: PracticeQueue,
    progress_state: CurriculumProgressState,
) -> Tuple[RuntimeSessionResult, RuntimeSessionEvent]:
    """
    Complete a runtime practice session with an outcome.

    Parameters
    ----------
    runtime_session:
        The active runtime session to complete.
    outcome:
        The practice outcome.
    queue:
        Current practice queue.
    progress_state:
        Current curriculum progress state.

    Returns
    -------
    Tuple of:
    - RuntimeSessionResult: Result with integration outcome
    - RuntimeSessionEvent: Runtime event for outcome processing

    Notes
    -----
    This function is pure — caller is responsible for persisting
    the integration result's updated state.

    If runtime_session.assignment is None, returns a failed result
    with processed=False and reasons=["missing_assignment"].
    """
    now = datetime.now(timezone.utc)

    if runtime_session.assignment is None:
        result = RuntimeSessionResult(
            runtime_session_id=runtime_session.runtime_session_id,
            processed=False,
            queue_updated=False,
            curriculum_advanced=False,
            reasons=["missing_assignment"],
        )
        runtime_event = RuntimeSessionEvent(
            id=_generate_runtime_event_id(),
            runtime_session_id=runtime_session.runtime_session_id,
            event_type=RuntimeSessionEventType.outcome_processed,
            timestamp=now,
            metadata={"processed": False, "reason": "missing_assignment"},
        )
        return result, runtime_event

    outcome_event = AssignmentOutcomeEvent(
        id=_generate_outcome_event_id(),
        assignment_id=runtime_session.assignment_id,
        outcome=outcome,
        timestamp=now,
    )

    integration_result = process_assignment_outcome(
        assignment=runtime_session.assignment,
        outcome_event=outcome_event,
        queue=queue,
        progress_state=progress_state,
    )

    result = RuntimeSessionResult(
        runtime_session_id=runtime_session.runtime_session_id,
        processed=integration_result.processed,
        queue_updated=integration_result.queue_event is not None,
        curriculum_advanced=integration_result.advanced_curriculum,
        outcome_event=outcome_event,
        integration_result=integration_result,
        reasons=integration_result.reasons,
    )

    runtime_event = RuntimeSessionEvent(
        id=_generate_runtime_event_id(),
        runtime_session_id=runtime_session.runtime_session_id,
        event_type=RuntimeSessionEventType.outcome_processed,
        timestamp=now,
        metadata={
            "outcome": outcome.value,
            "queue_updated": result.queue_updated,
            "curriculum_advanced": result.curriculum_advanced,
        },
    )

    return result, runtime_event


def abandon_runtime_session(
    *,
    runtime_session: RuntimePracticeSession,
    queue: PracticeQueue,
) -> Tuple[RuntimePracticeSession, PracticeQueue, PracticeQueueEvent, RuntimeSessionEvent]:
    """
    Abandon a runtime practice session.

    Parameters
    ----------
    runtime_session:
        The runtime session to abandon.
    queue:
        Current practice queue.

    Returns
    -------
    Tuple of:
    - RuntimePracticeSession: Updated session with abandoned status
    - PracticeQueue: Updated queue with assignment marked abandoned
    - PracticeQueueEvent: Queue event for assignment abandonment
    - RuntimeSessionEvent: Runtime event for session abandonment

    Notes
    -----
    Abandonment does NOT:
    - Create AssignmentOutcomeEvent
    - Call process_assignment_outcome()
    - Advance curriculum

    This is an explicit escape hatch, not a practice outcome.
    """
    now = datetime.now(timezone.utc)

    updated_queue, queue_event = mark_assignment_abandoned(
        queue,
        runtime_session.assignment_id,
    )

    updated_session = RuntimePracticeSession(
        runtime_session_id=runtime_session.runtime_session_id,
        queue_id=runtime_session.queue_id,
        scheduled_id=runtime_session.scheduled_id,
        assignment_id=runtime_session.assignment_id,
        student_id=runtime_session.student_id,
        status=RuntimeSessionStatus.abandoned,
        started_at=runtime_session.started_at,
        completed_at=now,
        assignment=runtime_session.assignment,
        session_id=runtime_session.session_id,
        metadata=runtime_session.metadata,
    )

    runtime_event = RuntimeSessionEvent(
        id=_generate_runtime_event_id(),
        runtime_session_id=runtime_session.runtime_session_id,
        event_type=RuntimeSessionEventType.session_abandoned,
        timestamp=now,
    )

    return updated_session, updated_queue, queue_event, runtime_event


def start_next_queue_assignment(
    *,
    queue: PracticeQueue,
    assignment_lookup: Callable[[str], Optional[AssembledPracticeAssignment]],
) -> Tuple[
    Optional[RuntimePracticeSession],
    PracticeQueue,
    Optional[PracticeQueueEvent],
    Optional[RuntimeSessionEvent],
]:
    """
    Start the next available assignment from the queue.

    Parameters
    ----------
    queue:
        Current practice queue.
    assignment_lookup:
        Callable to look up AssembledPracticeAssignment by assignment_id.

    Returns
    -------
    Tuple of:
    - RuntimePracticeSession or None: Created session (None if no assignment available)
    - PracticeQueue: Possibly updated queue
    - PracticeQueueEvent or None: Queue event if assignment started
    - RuntimeSessionEvent or None: Runtime event if session started

    Notes
    -----
    This function handles missing assignments gracefully:
    - If queue is empty, returns (None, queue, None, None)
    - If assignment_lookup returns None, skips and returns (None, queue, None, None)

    Unlike start_runtime_session, this function does NOT raise ValueError
    for missing assignments.
    """
    scheduled = next_queue_assignment(queue)
    if scheduled is None:
        return None, queue, None, None

    assignment = assignment_lookup(scheduled.assignment_id)
    if assignment is None:
        return None, queue, None, None

    try:
        runtime_session, updated_queue, queue_event, runtime_event = start_runtime_session(
            queue=queue,
            scheduled_assignment=scheduled,
            assignment_lookup=assignment_lookup,
        )
        return runtime_session, updated_queue, queue_event, runtime_event
    except ValueError:
        return None, queue, None, None


def attach_session_record(
    *,
    runtime_session: RuntimePracticeSession,
    session_record: SessionRecord,
) -> Tuple[RuntimePracticeSession, RuntimeSessionEvent]:
    """
    Attach a SessionRecord to a runtime practice session.

    Parameters
    ----------
    runtime_session:
        The runtime session to attach evidence to.
    session_record:
        The SessionRecord evidence to attach.

    Returns
    -------
    Tuple of:
    - RuntimePracticeSession: Updated session with evidence attached
    - RuntimeSessionEvent: Event for evidence attachment

    Notes
    -----
    This function is pure — caller is responsible for persisting.
    """
    now = datetime.now(timezone.utc)

    updated_session = RuntimePracticeSession(
        runtime_session_id=runtime_session.runtime_session_id,
        queue_id=runtime_session.queue_id,
        scheduled_id=runtime_session.scheduled_id,
        assignment_id=runtime_session.assignment_id,
        student_id=runtime_session.student_id,
        status=runtime_session.status,
        started_at=runtime_session.started_at,
        completed_at=runtime_session.completed_at,
        assignment=runtime_session.assignment,
        session_id=str(session_record.session_id),
        evaluation_id=runtime_session.evaluation_id,
        session_record=session_record,
        evaluation=runtime_session.evaluation,
        metadata=runtime_session.metadata,
    )

    runtime_event = RuntimeSessionEvent(
        id=_generate_runtime_event_id(),
        runtime_session_id=runtime_session.runtime_session_id,
        event_type=RuntimeSessionEventType.session_record_attached,
        timestamp=now,
        metadata={"session_id": str(session_record.session_id)},
    )

    return updated_session, runtime_event


def attach_evaluation(
    *,
    runtime_session: RuntimePracticeSession,
    evaluation: CoachEvaluation,
) -> Tuple[RuntimePracticeSession, RuntimeSessionEvent]:
    """
    Attach a CoachEvaluation to a runtime practice session.

    Parameters
    ----------
    runtime_session:
        The runtime session to attach evaluation to.
    evaluation:
        The CoachEvaluation to attach.

    Returns
    -------
    Tuple of:
    - RuntimePracticeSession: Updated session with evaluation attached
    - RuntimeSessionEvent: Event for evaluation attachment

    Raises
    ------
    ValueError:
        If runtime_session.session_record is None (session_record_required).
        If evaluation.session_id doesn't match session_record.session_id (session_evaluation_mismatch).

    Notes
    -----
    Requires session_record to be attached first.
    Validates that evaluation references the same session_id.
    """
    if runtime_session.session_record is None:
        raise ValueError("session_record_required")

    if runtime_session.session_record.session_id != evaluation.session_id:
        raise ValueError("session_evaluation_mismatch")

    now = datetime.now(timezone.utc)

    updated_session = RuntimePracticeSession(
        runtime_session_id=runtime_session.runtime_session_id,
        queue_id=runtime_session.queue_id,
        scheduled_id=runtime_session.scheduled_id,
        assignment_id=runtime_session.assignment_id,
        student_id=runtime_session.student_id,
        status=runtime_session.status,
        started_at=runtime_session.started_at,
        completed_at=runtime_session.completed_at,
        assignment=runtime_session.assignment,
        session_id=runtime_session.session_id,
        evaluation_id=str(evaluation.session_id),
        session_record=runtime_session.session_record,
        evaluation=evaluation,
        metadata=runtime_session.metadata,
    )

    runtime_event = RuntimeSessionEvent(
        id=_generate_runtime_event_id(),
        runtime_session_id=runtime_session.runtime_session_id,
        event_type=RuntimeSessionEventType.evaluation_attached,
        timestamp=now,
        metadata={"evaluation_session_id": str(evaluation.session_id)},
    )

    return updated_session, runtime_event


def attach_runtime_evidence(
    *,
    runtime_session: RuntimePracticeSession,
    session_record: SessionRecord,
    evaluation: CoachEvaluation,
) -> RuntimeEvidenceAttachmentResult:
    """
    Attach both SessionRecord and CoachEvaluation to a runtime session.

    Parameters
    ----------
    runtime_session:
        The runtime session to attach evidence to.
    session_record:
        The SessionRecord evidence.
    evaluation:
        The CoachEvaluation evidence.

    Returns
    -------
    RuntimeEvidenceAttachmentResult with updated session and any warnings.

    Notes
    -----
    This is a combined helper that attaches both pieces of evidence.
    If session_id matching cannot be verified, adds reason
    "session_evaluation_link_unverified".
    Does not raise — accumulates warnings in reasons.
    """
    reasons: list[str] = []

    session_with_record, _ = attach_session_record(
        runtime_session=runtime_session,
        session_record=session_record,
    )

    if session_record.session_id != evaluation.session_id:
        reasons.append("session_evaluation_link_unverified")

    session_with_evidence = RuntimePracticeSession(
        runtime_session_id=session_with_record.runtime_session_id,
        queue_id=session_with_record.queue_id,
        scheduled_id=session_with_record.scheduled_id,
        assignment_id=session_with_record.assignment_id,
        student_id=session_with_record.student_id,
        status=session_with_record.status,
        started_at=session_with_record.started_at,
        completed_at=session_with_record.completed_at,
        assignment=session_with_record.assignment,
        session_id=session_with_record.session_id,
        evaluation_id=str(evaluation.session_id),
        session_record=session_with_record.session_record,
        evaluation=evaluation,
        metadata=session_with_record.metadata,
    )

    return RuntimeEvidenceAttachmentResult(
        attached=True,
        runtime_session_id=runtime_session.runtime_session_id,
        session_id=str(session_record.session_id),
        evaluation_id=str(evaluation.session_id),
        runtime_session=session_with_evidence,
        reasons=reasons,
    )


def runtime_session_has_evidence(runtime_session: RuntimePracticeSession) -> bool:
    """
    Check if a runtime session has full evidence attached.

    Parameters
    ----------
    runtime_session:
        The runtime session to check.

    Returns
    -------
    True only if both session_record and evaluation exist.
    """
    return (
        runtime_session.session_record is not None
        and runtime_session.evaluation is not None
    )


__all__ = [
    "RUNTIME_FLOW_VERSION",
    "start_runtime_session",
    "complete_runtime_session",
    "abandon_runtime_session",
    "start_next_queue_assignment",
    "attach_session_record",
    "attach_evaluation",
    "attach_runtime_evidence",
    "runtime_session_has_evidence",
]
