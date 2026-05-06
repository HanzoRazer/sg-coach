"""
Assignment Outcome — Capture and bridge utilities for assignment outcomes.

Sprint 10: Assignment outcome tracking.

This module provides:
- capture_assignment_outcome(): Create event from capture request
- response_type_from_assignment_outcome(): Map outcome to response type
- assignment_outcome_to_feedback_request(): Bridge to feedback pipeline

Core rules:
1. Assignment outcomes are events; assignments are not mutated
2. Outcome capture does not evaluate performance
3. Outcome capture does not update rankings directly
4. Abandoned/worsened outcomes are coaching signal, not user failure
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sg_spec.schemas.assignment_outcome import (
    AssignmentOutcomeCaptureRequest,
    AssignmentOutcomeEvent,
)
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.user_feedback import (
    FeedbackCaptureRequest,
    PracticeOutcome,
    UserFeedbackResponseType,
)


def generate_outcome_id() -> str:
    """Generate a short outcome event ID with ao_ prefix."""
    return f"ao_{uuid.uuid4().hex[:12]}"


def capture_assignment_outcome(
    request: AssignmentOutcomeCaptureRequest,
    *,
    event_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> AssignmentOutcomeEvent:
    """
    Create an AssignmentOutcomeEvent from a capture request.

    Parameters
    ----------
    request:
        The capture request with outcome data.
    event_id:
        Optional ID for the event (for idempotency/testing).
        If not provided, auto-generates ao_<12hex>.
    timestamp:
        Optional timestamp override.
        If not provided, uses schema default (now).

    Returns
    -------
    AssignmentOutcomeEvent ready for storage/processing.

    Notes
    -----
    - Does not store anything
    - Does not mutate any assignment
    - Generates ID if not provided
    """
    resolved_id = event_id if event_id else generate_outcome_id()

    # Build event kwargs
    event_kwargs: Dict[str, Any] = {
        "id": resolved_id,
        "assignment_id": request.assignment_id,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "instrument_id": request.instrument_id,
        "outcome": request.outcome,
        "confidence": request.confidence,
        "comment": request.comment,
        "evidence": dict(request.evidence),
        "source": request.source,
        "interaction_context": dict(request.interaction_context),
    }

    # Use provided timestamp if given
    if timestamp is not None:
        event_kwargs["timestamp"] = timestamp

    return AssignmentOutcomeEvent(**event_kwargs)


def response_type_from_assignment_outcome(
    outcome: PracticeOutcome,
) -> UserFeedbackResponseType:
    """
    Map a PracticeOutcome to a UserFeedbackResponseType.

    Parameters
    ----------
    outcome:
        The practice outcome.

    Returns
    -------
    Corresponding UserFeedbackResponseType.

    Mapping
    -------
    - improved → helped
    - completed → accepted
    - repeated → accepted
    - worsened → did_not_help
    - abandoned → did_not_help
    """
    mapping = {
        PracticeOutcome.improved: UserFeedbackResponseType.helped,
        PracticeOutcome.completed: UserFeedbackResponseType.accepted,
        PracticeOutcome.repeated: UserFeedbackResponseType.accepted,
        PracticeOutcome.worsened: UserFeedbackResponseType.did_not_help,
        PracticeOutcome.abandoned: UserFeedbackResponseType.did_not_help,
    }
    return mapping[outcome]


def assignment_outcome_to_feedback_request(
    *,
    assignment: AssembledPracticeAssignment,
    outcome_event: AssignmentOutcomeEvent,
    response_type: Optional[UserFeedbackResponseType] = None,
) -> FeedbackCaptureRequest:
    """
    Convert an assignment outcome into a FeedbackCaptureRequest.

    This bridges assignment outcomes into the existing learning pipeline,
    allowing outcomes to flow into UserFeedbackEvent → LearningSignal.

    Parameters
    ----------
    assignment:
        The practice assignment that was completed.
    outcome_event:
        The outcome event to convert.
    response_type:
        Optional explicit response type (overrides auto-mapping).

    Returns
    -------
    FeedbackCaptureRequest ready for capture_feedback().

    Notes
    -----
    - Uses outcome_event.session_id, else assignment.params.get("session_id")
    - Uses assignment.finding_id and recommendation_id (falls back to None)
    - Evidence becomes corrected_result if non-empty
    - Interaction context includes assignment linkage
    """
    # Determine response type
    resolved_response_type = (
        response_type
        if response_type is not None
        else response_type_from_assignment_outcome(outcome_event.outcome)
    )

    # Determine session_id with fallback
    session_id = outcome_event.session_id
    if session_id is None:
        session_id = assignment.params.get("session_id")

    # Build interaction context
    interaction_context: Dict[str, Any] = dict(outcome_event.interaction_context)
    interaction_context["assignment_id"] = outcome_event.assignment_id
    interaction_context["assignment_type"] = (
        assignment.assignment_type.value
        if assignment.assignment_type
        else None
    )
    if outcome_event.id:
        interaction_context["outcome_event_id"] = outcome_event.id

    # Evidence becomes corrected_result if non-empty
    corrected_result = (
        dict(outcome_event.evidence) if outcome_event.evidence else None
    )

    return FeedbackCaptureRequest(
        session_id=session_id,
        finding_id=assignment.finding_id,
        recommendation_id=assignment.recommendation_id,
        response_type=resolved_response_type,
        confidence=outcome_event.confidence,
        comment=outcome_event.comment,
        corrected_result=corrected_result,
        outcome=outcome_event.outcome,
        source=outcome_event.source or "assignment_outcome",
        interaction_context=interaction_context,
    )


__all__ = [
    "capture_assignment_outcome",
    "response_type_from_assignment_outcome",
    "assignment_outcome_to_feedback_request",
    "generate_outcome_id",
]
