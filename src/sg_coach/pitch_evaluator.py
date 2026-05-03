"""
Pitch Accuracy Evaluator

Evaluates performed note events against expected note events.
Emits WRONG_NOTE when note identity differs.
Emits PITCH_DEVIATION when pitch differs beyond cents threshold.

This module is the coach interpretation layer for pitch accuracy.
It does not parse audio or MIDI — it uses already-parsed event data.

Architecture:
    Raw audio/MIDI     = captured by runtime (not here)
    Parsed events      = input to this module
    CoachFinding       = output for coaching
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Sequence, TypedDict

from sg_spec.schemas.adaptive_feedback import DiagnosisCode

from .schemas import (
    CoachFinding,
    FindingEvidence,
    Severity,
    FeedbackDomain,
    FeedbackRenderHint,
    FeedbackActionType,
    SuggestedAction,
)


DEFAULT_CENTS_THRESHOLD = 25.0


class ExpectedNote(TypedDict, total=False):
    """Expected note event structure (type hints only)."""
    note: str
    midi: int
    pitch_hz: float
    index: int
    time_sec: float


class PerformedNote(TypedDict, total=False):
    """Performed note event structure (type hints only)."""
    note: str
    midi: int
    pitch_hz: float
    index: int
    time_sec: float


@dataclass
class PitchComparisonResult:
    """Result of comparing a single note pair."""
    index: int
    expected_note: Optional[str]
    performed_note: Optional[str]
    expected_midi: Optional[int]
    performed_midi: Optional[int]
    expected_hz: Optional[float]
    performed_hz: Optional[float]
    identity_match: Optional[bool]
    cents_error: Optional[float]
    direction: Optional[str]


def _normalize_note_string(note: Optional[str]) -> Optional[str]:
    """
    Conservative normalization of note string.

    - Strip whitespace
    - Uppercase first letter
    - Keep octave if present
    - Basic enharmonic normalization only when safe
    """
    if note is None:
        return None

    note = note.strip()
    if not note:
        return None

    # Uppercase first letter (note name)
    note = note[0].upper() + note[1:] if len(note) > 0 else note

    return note


def _notes_match(
    expected: Mapping[str, Any],
    performed: Mapping[str, Any],
) -> Optional[bool]:
    """
    Compare note identity. Returns True if match, False if mismatch, None if unknown.

    Priority:
    1. MIDI number if both available
    2. Normalized note string if MIDI unavailable
    """
    exp_midi = expected.get("midi")
    perf_midi = performed.get("midi")

    # Use MIDI if both available
    if exp_midi is not None and perf_midi is not None:
        return exp_midi == perf_midi

    # Fall back to normalized strings
    exp_note = _normalize_note_string(expected.get("note"))
    perf_note = _normalize_note_string(performed.get("note"))

    if exp_note is not None and perf_note is not None:
        return exp_note == perf_note

    # Cannot determine identity
    return None


def _calculate_cents_error(expected_hz: float, performed_hz: float) -> float:
    """Calculate pitch deviation in cents."""
    if expected_hz <= 0 or performed_hz <= 0:
        return 0.0
    return 1200.0 * math.log2(performed_hz / expected_hz)


def _compare_note_pair(
    expected: Mapping[str, Any],
    performed: Mapping[str, Any],
    index: int,
) -> PitchComparisonResult:
    """Compare a single expected/performed note pair."""
    exp_note = expected.get("note")
    perf_note = performed.get("note")
    exp_midi = expected.get("midi")
    perf_midi = performed.get("midi")
    exp_hz = expected.get("pitch_hz")
    perf_hz = performed.get("pitch_hz")

    identity_match = _notes_match(expected, performed)

    cents_error = None
    direction = None
    if exp_hz is not None and perf_hz is not None:
        cents_error = _calculate_cents_error(exp_hz, perf_hz)
        if cents_error > 0:
            direction = "sharp"
        elif cents_error < 0:
            direction = "flat"
        else:
            direction = "in_tune"

    return PitchComparisonResult(
        index=index,
        expected_note=exp_note,
        performed_note=perf_note,
        expected_midi=exp_midi,
        performed_midi=perf_midi,
        expected_hz=exp_hz,
        performed_hz=perf_hz,
        identity_match=identity_match,
        cents_error=cents_error,
        direction=direction,
    )


def _make_wrong_note_finding(result: PitchComparisonResult) -> CoachFinding:
    """Create a WRONG_NOTE CoachFinding."""
    exp_display = result.expected_note or f"MIDI {result.expected_midi}"
    perf_display = result.performed_note or f"MIDI {result.performed_midi}"
    message = f"Expected {exp_display} but played {perf_display}"

    return CoachFinding(
        # Legacy fields
        type="harmony",
        severity=Severity.secondary,
        interpretation=message,
        # Governance fields
        code=DiagnosisCode.WRONG_NOTE,
        domain=FeedbackDomain.pitch,
        title="Wrong note",
        message=message,
        evidence=FindingEvidence(
            metric="wrong_note",
            expected=exp_display,
            actual=perf_display,
            index=result.index,
        ),
        render_hint=FeedbackRenderHint.inline,
        suggested_actions=[
            SuggestedAction(
                action_type=FeedbackActionType.isolate,
                label="Isolate problem note",
                rationale=f"Practice note {result.index + 1} separately",
            ),
            SuggestedAction(
                action_type=FeedbackActionType.review_reference,
                label="Review expected note",
                rationale=f"The expected note was {exp_display}",
            ),
            SuggestedAction(
                action_type=FeedbackActionType.retry_section,
                label="Retry section",
                rationale="Play the passage again with correct note",
            ),
        ],
        confidence=1.0,
        source_evaluator="pitch_evaluator",
    )


def _make_pitch_deviation_finding(
    result: PitchComparisonResult,
    threshold: float,
) -> CoachFinding:
    """Create a PITCH_DEVIATION CoachFinding."""
    cents = result.cents_error or 0.0
    direction = result.direction or "off"
    message = f"Pitch was {abs(cents):.0f} cents {direction}"

    return CoachFinding(
        # Legacy fields
        type="timing",  # Using timing for pitch timeline display
        severity=Severity.secondary,
        interpretation=message,
        # Governance fields
        code=DiagnosisCode.PITCH_DEVIATION,
        domain=FeedbackDomain.pitch,
        title="Pitch deviation",
        message=message,
        evidence=FindingEvidence(
            metric="pitch_deviation",
            value=cents,
            unit="cents",
            threshold=threshold,
            expected=result.expected_hz,
            actual=result.performed_hz,
            direction=direction,
            index=result.index,
        ),
        render_hint=FeedbackRenderHint.timeline,
        suggested_actions=[
            SuggestedAction(
                action_type=FeedbackActionType.isolate,
                label="Isolate problem note",
                rationale=f"Focus on intonation for note {result.index + 1}",
            ),
            SuggestedAction(
                action_type=FeedbackActionType.review_reference,
                label="Check tuning reference",
                rationale=f"Expected {result.expected_hz:.1f} Hz" if result.expected_hz else "Check reference pitch",
            ),
            SuggestedAction(
                action_type=FeedbackActionType.retry_section,
                label="Retry with focus on pitch",
                rationale="Play again while listening carefully to intonation",
            ),
        ],
        confidence=1.0,
        source_evaluator="pitch_evaluator",
    )


def evaluate_pitch_accuracy(
    expected_notes: Sequence[Mapping[str, Any]],
    performed_notes: Sequence[Mapping[str, Any]],
    cents_threshold: float = DEFAULT_CENTS_THRESHOLD,
) -> List[CoachFinding]:
    """
    Evaluate performed note events against expected note events.

    Parameters
    ----------
    expected_notes:
        Sequence of expected note events. Each event may have:
        note, midi, pitch_hz, index, time_sec
    performed_notes:
        Sequence of performed note events. Same structure.
    cents_threshold:
        Pitch deviation threshold in cents. Default 25.

    Returns
    -------
    List of CoachFindings for WRONG_NOTE and PITCH_DEVIATION.

    Behavior
    --------
    - Pairs notes sequentially by index
    - WRONG_NOTE: when note identity differs
    - PITCH_DEVIATION: when identity matches but pitch differs > threshold
    - Never emits both for same index
    - Skips pairs where comparison is not possible
    """
    findings: List[CoachFinding] = []

    # Track stats for aggregate
    pairs_evaluated = 0
    wrong_notes = 0
    pitch_deviations = 0
    skipped = 0

    # Sequential pairing
    for i, (expected, performed) in enumerate(zip(expected_notes, performed_notes)):
        result = _compare_note_pair(expected, performed, i)
        pairs_evaluated += 1

        # Check for wrong note first
        if result.identity_match is False:
            findings.append(_make_wrong_note_finding(result))
            wrong_notes += 1
            continue  # Don't double-report

        # Check for pitch deviation (only if identity matches or unknown)
        if result.cents_error is not None:
            if abs(result.cents_error) > cents_threshold:
                findings.append(_make_pitch_deviation_finding(result, cents_threshold))
                pitch_deviations += 1
                continue

        # No finding for this pair
        if result.identity_match is None and result.cents_error is None:
            skipped += 1

    # Track length difference
    len_expected = len(expected_notes)
    len_performed = len(performed_notes)
    length_diff = abs(len_expected - len_performed)

    # Add aggregate stats to first finding if any exist
    if findings and len(findings) > 0:
        first_evidence = findings[0].evidence
        if first_evidence.aggregate_stats is None:
            first_evidence.aggregate_stats = {}
        first_evidence.aggregate_stats.update({
            "pairs_evaluated": pairs_evaluated,
            "wrong_notes": wrong_notes,
            "pitch_deviations": pitch_deviations,
            "skipped": skipped,
            "length_diff": length_diff,
        })

    return findings


__all__ = [
    "ExpectedNote",
    "PerformedNote",
    "PitchComparisonResult",
    "evaluate_pitch_accuracy",
    "DEFAULT_CENTS_THRESHOLD",
]
