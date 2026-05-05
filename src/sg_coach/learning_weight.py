"""
Learning Weight — Compute signal weights from user feedback.

Sprint 5 Dev Order 3: Derives one LearningSignal from one feedback event
plus explicit context. No storage, no lookup, no aggregation, no adaptation.

Weight formula:
    weight = base_effectiveness × confidence_modifier × outcome_modifier

Clamped to [-2.0, +2.0].
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.user_feedback import (
    LearningSignal,
    PracticeOutcome,
    UserFeedbackEvent,
    UserFeedbackResponseType,
)


# Base effectiveness by response type
BASE_EFFECTIVENESS: dict[UserFeedbackResponseType, float] = {
    UserFeedbackResponseType.helped: 1.0,
    UserFeedbackResponseType.accepted: 0.6,
    UserFeedbackResponseType.did_not_help: -0.8,
    UserFeedbackResponseType.rejected: -1.0,
    UserFeedbackResponseType.too_easy: -0.3,
    UserFeedbackResponseType.too_hard: -0.5,
    UserFeedbackResponseType.misunderstood: -0.9,
    UserFeedbackResponseType.user_marked_issue: 0.7,
}

# Outcome modifiers
OUTCOME_MODIFIER: dict[PracticeOutcome, float] = {
    PracticeOutcome.improved: 1.5,
    PracticeOutcome.completed: 1.2,
    PracticeOutcome.repeated: 1.0,
    PracticeOutcome.worsened: 0.5,
    PracticeOutcome.abandoned: 0.3,
}

# Weight bounds
WEIGHT_MIN = -2.0
WEIGHT_MAX = 2.0

# Weak signal threshold
WEAK_SIGNAL_THRESHOLD = 0.2

# Default values for missing inputs
DEFAULT_CONFIDENCE = 0.5
DEFAULT_OUTCOME = PracticeOutcome.repeated


def _generate_signal_id() -> str:
    """Generate a stable signal ID with ls_ prefix."""
    return f"ls_{uuid4().hex}"


def compute_confidence_modifier(confidence: Optional[float]) -> float:
    """
    Compute confidence modifier from user confidence.

    Formula: 0.5 + (confidence × 0.5)

    Parameters
    ----------
    confidence:
        User confidence 0.0-1.0, or None for default.

    Returns
    -------
    Modifier in range [0.5, 1.0].
    """
    if confidence is None:
        confidence = DEFAULT_CONFIDENCE
    return 0.5 + (confidence * 0.5)


def compute_signal_weight(
    response_type: UserFeedbackResponseType,
    confidence: Optional[float] = None,
    outcome: Optional[PracticeOutcome] = None,
) -> float:
    """
    Compute signal weight from feedback components.

    Formula:
        weight = base_effectiveness × confidence_modifier × outcome_modifier
        clamped to [-2.0, +2.0]

    Parameters
    ----------
    response_type:
        How the user responded (required).
    confidence:
        User confidence 0.0-1.0. None uses default 0.5.
    outcome:
        Practice outcome. None uses default 'repeated'.

    Returns
    -------
    Signal weight clamped to [-2.0, +2.0].
    """
    base = BASE_EFFECTIVENESS[response_type]
    conf_mod = compute_confidence_modifier(confidence)

    if outcome is None:
        outcome = DEFAULT_OUTCOME
    outcome_mod = OUTCOME_MODIFIER[outcome]

    weight = base * conf_mod * outcome_mod
    return max(WEIGHT_MIN, min(WEIGHT_MAX, weight))


def is_weak_signal(weight: float) -> bool:
    """Check if a weight is below the weak signal threshold."""
    return abs(weight) < WEAK_SIGNAL_THRESHOLD


def derive_learning_signal(
    event: UserFeedbackEvent,
    *,
    source_finding_code: DiagnosisCode,
    action_type: FeedbackActionType,
    signal_id: Optional[str] = None,
) -> LearningSignal:
    """
    Derive a LearningSignal from a UserFeedbackEvent plus explicit context.

    Parameters
    ----------
    event:
        The feedback event to derive from.
    source_finding_code:
        The diagnosis code that triggered the original finding.
        Required explicitly — no lookup performed.
    action_type:
        The action type that was recommended.
        Required explicitly — no lookup performed.
    signal_id:
        Optional override for the signal ID. Auto-generates if not provided.

    Returns
    -------
    A LearningSignal with computed weight.

    Notes
    -----
    - Does not store the signal
    - Does not look up findings or recommendations
    - Does not aggregate signals
    - Does not adapt behavior
    """
    outcome = event.outcome if event.outcome is not None else DEFAULT_OUTCOME
    weight = compute_signal_weight(
        response_type=event.response_type,
        confidence=event.confidence,
        outcome=event.outcome,
    )

    return LearningSignal(
        id=signal_id if signal_id is not None else _generate_signal_id(),
        source_finding_code=source_finding_code,
        action_type=action_type,
        user_response=event.response_type,
        outcome=outcome,
        weight=weight,
        source_event_id=event.id,
    )


__all__ = [
    "BASE_EFFECTIVENESS",
    "OUTCOME_MODIFIER",
    "WEIGHT_MIN",
    "WEIGHT_MAX",
    "WEAK_SIGNAL_THRESHOLD",
    "compute_confidence_modifier",
    "compute_signal_weight",
    "is_weak_signal",
    "derive_learning_signal",
]
