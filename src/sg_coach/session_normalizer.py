"""
Session Normalizer — Convert legacy params to normalized session inputs.

Sprint 3: Enables clean evaluate_session(session) signature by moving
evaluator-specific inputs into session.normalized.

Migration layer that preserves backward compatibility while encouraging
canonical normalized input patterns.

Rule: existing session.normalized wins over legacy params.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .schemas import (
    SessionRecord,
    NormalizedSessionData,
    HarmonyEvaluationInput,
    TimingEvaluationInput,
    PitchEvaluationInput,
)
from .exercise_classifier import extract_key_from_program


def normalize_session(
    session: SessionRecord,
    *,
    performed_notes: Optional[Sequence[int]] = None,
    expected_times: Optional[Sequence[float]] = None,
    performed_times: Optional[Sequence[float]] = None,
    timing_threshold_ms: float = 40.0,
    expected_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    performed_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    pitch_cents_threshold: float = 25.0,
) -> SessionRecord:
    """
    Normalize session by populating session.normalized from legacy params.

    Parameters
    ----------
    session:
        SessionRecord to normalize.
    performed_notes:
        Legacy harmony input (pitch classes 0-11).
    expected_times:
        Legacy timing input (expected event times in seconds).
    performed_times:
        Legacy timing input (performed event times in seconds).
    timing_threshold_ms:
        Timing deviation threshold in milliseconds.
    expected_pitch_events:
        Legacy pitch input (expected note events).
    performed_pitch_events:
        Legacy pitch input (performed note events).
    pitch_cents_threshold:
        Pitch deviation threshold in cents.

    Returns
    -------
    SessionRecord with normalized field populated.

    Precedence
    ----------
    Existing session.normalized wins over legacy params:
    - If session.normalized.timing exists, ignore legacy timing params
    - If session.normalized.pitch exists, ignore legacy pitch params
    - If session.normalized.harmony exists, ignore legacy harmony params

    Does not mutate the input session — returns a copy.
    """
    # Start with existing normalized data or empty container
    existing = session.normalized
    if existing is None:
        existing = NormalizedSessionData()

    # Build harmony input (only if not already set)
    harmony = existing.harmony
    if harmony is None and performed_notes is not None:
        key = session.key or extract_key_from_program(session.program_ref)
        harmony = HarmonyEvaluationInput(
            key=key,
            performed_notes=list(performed_notes),
            expected_orbit=None,  # Computed by evaluator from key
        )

    # Build timing input (only if not already set)
    timing = existing.timing
    if timing is None and expected_times is not None and performed_times is not None:
        timing = TimingEvaluationInput(
            expected_times=list(expected_times),
            performed_times=list(performed_times),
            threshold_ms=timing_threshold_ms,
        )

    # Build pitch input (only if not already set)
    pitch = existing.pitch
    if pitch is None and expected_pitch_events is not None and performed_pitch_events is not None:
        pitch = PitchEvaluationInput(
            expected_pitch_events=list(expected_pitch_events),
            performed_pitch_events=list(performed_pitch_events),
            cents_threshold=pitch_cents_threshold,
        )

    # Create new normalized container with merged inputs
    normalized = NormalizedSessionData(
        harmony=harmony,
        timing=timing,
        pitch=pitch,
    )

    # Return copy with normalized data
    return session.model_copy(update={"normalized": normalized})


def ensure_normalized_session(session: SessionRecord) -> SessionRecord:
    """
    Ensure session has a normalized container (may be empty).

    Returns session unchanged if already has normalized field,
    otherwise returns copy with empty NormalizedSessionData.
    """
    if session.normalized is not None:
        return session
    return session.model_copy(update={"normalized": NormalizedSessionData()})


def has_timing_input(session: SessionRecord) -> bool:
    """
    Check if session has complete timing input data.

    Returns True if session.normalized.timing exists with both
    expected_times and performed_times populated.
    """
    if session.normalized is None:
        return False
    if session.normalized.timing is None:
        return False
    t = session.normalized.timing
    return len(t.expected_times) > 0 and len(t.performed_times) > 0


def has_pitch_input(session: SessionRecord) -> bool:
    """
    Check if session has complete pitch input data.

    Returns True if session.normalized.pitch exists with both
    expected_pitch_events and performed_pitch_events populated.
    """
    if session.normalized is None:
        return False
    if session.normalized.pitch is None:
        return False
    p = session.normalized.pitch
    return len(p.expected_pitch_events) > 0 and len(p.performed_pitch_events) > 0


def has_harmony_input(session: SessionRecord) -> bool:
    """
    Check if session has harmony input data.

    Returns True if session.normalized.harmony exists with
    performed_notes populated.
    """
    if session.normalized is None:
        return False
    if session.normalized.harmony is None:
        return False
    h = session.normalized.harmony
    return len(h.performed_notes) > 0


__all__ = [
    "normalize_session",
    "ensure_normalized_session",
    "has_timing_input",
    "has_pitch_input",
    "has_harmony_input",
]
