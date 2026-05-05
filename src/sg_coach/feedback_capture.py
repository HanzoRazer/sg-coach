"""
Feedback Capture — Convert capture requests to feedback events.

Sprint 5 Dev Order 2: Capture contract only, no storage or learning.

This module provides:
- capture_feedback(): Creates UserFeedbackEvent from FeedbackCaptureRequest
- validate_feedback_linkage(): Checks linkage and returns warnings

Core principle: Capture creates one durable UserFeedbackEvent.
It does not infer learning yet.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sg_spec.schemas.user_feedback import (
    FeedbackCaptureRequest,
    UserFeedbackEvent,
)


def _generate_event_id() -> str:
    """Generate a stable event ID with uf_ prefix."""
    return f"uf_{uuid4().hex}"


def capture_feedback(
    request: FeedbackCaptureRequest,
    *,
    event_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> UserFeedbackEvent:
    """
    Convert a FeedbackCaptureRequest into a UserFeedbackEvent.

    Parameters
    ----------
    request:
        The capture request containing user feedback data.
    event_id:
        Optional override for the event ID. If not provided, auto-generates
        with "uf_" prefix.
    timestamp:
        Optional override for the timestamp. If not provided, uses current
        UTC time.

    Returns
    -------
    A UserFeedbackEvent ready for storage (storage not implemented this sprint).

    Notes
    -----
    - Creates exactly one UserFeedbackEvent per request (1:1)
    - Auto-generates ID if not provided
    - Copies all linkage, response, and metadata fields
    - Does not store the event
    - Does not mutate findings or recommendations
    - Does not compute LearningSignal
    """
    return UserFeedbackEvent(
        # Identity
        id=event_id if event_id is not None else _generate_event_id(),
        # Linkage
        session_id=request.session_id,
        finding_id=request.finding_id,
        recommendation_id=request.recommendation_id,
        # Response
        response_type=request.response_type,
        confidence=request.confidence,
        comment=request.comment,
        corrected_result=request.corrected_result,
        outcome=request.outcome,
        # Capture metadata
        source=request.source,
        interaction_context=request.interaction_context,
        # Timestamp
        timestamp=timestamp if timestamp is not None else datetime.now(timezone.utc),
    )


class FeedbackLinkageWarning:
    """Structured warning about feedback linkage issues."""

    def __init__(self, field: str, code: str, message: str):
        self.field = field
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }

    def __repr__(self) -> str:
        return f"FeedbackLinkageWarning({self.code}: {self.message})"


def validate_feedback_linkage(
    request: FeedbackCaptureRequest,
) -> List[FeedbackLinkageWarning]:
    """
    Validate feedback linkage and return warnings.

    Parameters
    ----------
    request:
        The capture request to validate.

    Returns
    -------
    List of warnings (empty if no issues). Does not raise exceptions.

    Notes
    -----
    - Returns warnings, not exceptions
    - Missing linkage does not block capture in v1
    - Absence of feedback is not rejection
    """
    warnings: List[FeedbackLinkageWarning] = []

    # Check session_id
    if request.session_id is None:
        warnings.append(FeedbackLinkageWarning(
            field="session_id",
            code="missing_session_id",
            message="Feedback event has no session_id",
        ))

    # Check finding_id and recommendation_id
    if request.finding_id is None and request.recommendation_id is None:
        warnings.append(FeedbackLinkageWarning(
            field="finding_id,recommendation_id",
            code="missing_target_linkage",
            message="Feedback event has neither finding_id nor recommendation_id",
        ))

    return warnings


__all__ = [
    "capture_feedback",
    "validate_feedback_linkage",
    "FeedbackLinkageWarning",
]
