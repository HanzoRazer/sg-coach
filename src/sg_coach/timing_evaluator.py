"""
Timing Grid Evaluator

Evaluates performed note timing against expected grid timestamps.
Emits TIMING_GRID_DEVIATION findings when timing deviation exceeds threshold.

This module is the coach interpretation layer for timing evaluation.
It does not parse MIDI or audio — it uses already-parsed event data.

Architecture:
    Raw audio/MIDI     = captured by runtime (not here)
    Parsed events      = input to this module
    CoachFinding       = output for coaching
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Sequence

from sg_spec.schemas.adaptive_feedback import DiagnosisCode

from .schemas import CoachFinding, FindingEvidence, Severity


DEFAULT_THRESHOLD_MS = 40.0


@dataclass
class TimingEvent:
    """A single timing event with expected and performed times."""
    index: int
    expected_time_sec: float
    performed_time_sec: float
    offset_ms: float = field(init=False)
    direction: Literal["early", "late", "on_time"] = field(init=False)

    def __post_init__(self):
        self.offset_ms = (self.performed_time_sec - self.expected_time_sec) * 1000
        if self.offset_ms > 0:
            self.direction = "late"
        elif self.offset_ms < 0:
            self.direction = "early"
        else:
            self.direction = "on_time"


@dataclass
class TimingDeviation:
    """A timing deviation that exceeds the threshold."""
    event: TimingEvent
    threshold_ms: float

    @property
    def abs_offset_ms(self) -> float:
        return abs(self.event.offset_ms)


@dataclass
class TimingGridEvaluation:
    """Result of evaluating timing against a grid."""
    tempo_bpm: float
    threshold_ms: float
    events_evaluated: int
    deviations: list[TimingDeviation]
    average_abs_error_ms: float
    max_abs_error_ms: float
    diagnosis_code: Optional[DiagnosisCode] = None
    message: Optional[str] = None

    @property
    def is_clean(self) -> bool:
        """True if no deviations exceed threshold."""
        return len(self.deviations) == 0

    def to_coach_finding(self) -> Optional[CoachFinding]:
        """Convert to CoachFinding if there's a deviation."""
        if self.is_clean:
            return None

        # Determine severity based on max error
        if self.max_abs_error_ms >= self.threshold_ms * 2:
            severity = Severity.primary
        else:
            severity = Severity.secondary

        # Find worst deviation for evidence
        worst = max(self.deviations, key=lambda d: d.abs_offset_ms)

        return CoachFinding(
            type="timing",
            severity=severity,
            evidence=FindingEvidence(
                metric="timing_grid_deviation",
                value=self.max_abs_error_ms,
            ),
            interpretation=self.message or render_timing_message(self, worst),
        )


def evaluate_timing_grid(
    tempo_bpm: float,
    expected_times: Sequence[float],
    performed_times: Sequence[float],
    threshold_ms: float = DEFAULT_THRESHOLD_MS,
) -> TimingGridEvaluation:
    """
    Evaluate performed timing against expected grid.

    Parameters
    ----------
    tempo_bpm:
        Tempo in beats per minute.
    expected_times:
        Sequence of expected event times in seconds.
    performed_times:
        Sequence of performed event times in seconds.
    threshold_ms:
        Deviation threshold in milliseconds. Default 40ms.

    Returns
    -------
    Evaluation result with deviations and aggregate stats.
    """
    if len(expected_times) == 0 or len(performed_times) == 0:
        return TimingGridEvaluation(
            tempo_bpm=tempo_bpm,
            threshold_ms=threshold_ms,
            events_evaluated=0,
            deviations=[],
            average_abs_error_ms=0.0,
            max_abs_error_ms=0.0,
        )

    # Pair events in order (v1 simple matching)
    events: list[TimingEvent] = []
    deviations: list[TimingDeviation] = []
    abs_errors: list[float] = []

    for i, (expected, performed) in enumerate(zip(expected_times, performed_times)):
        event = TimingEvent(
            index=i,
            expected_time_sec=expected,
            performed_time_sec=performed,
        )
        events.append(event)
        abs_errors.append(abs(event.offset_ms))

        if abs(event.offset_ms) > threshold_ms:
            deviations.append(TimingDeviation(event=event, threshold_ms=threshold_ms))

    avg_error = sum(abs_errors) / len(abs_errors) if abs_errors else 0.0
    max_error = max(abs_errors) if abs_errors else 0.0

    diagnosis_code = None
    message = None

    if deviations:
        diagnosis_code = DiagnosisCode.TIMING_GRID_DEVIATION
        worst = max(deviations, key=lambda d: d.abs_offset_ms)
        message = render_timing_message(
            TimingGridEvaluation(
                tempo_bpm=tempo_bpm,
                threshold_ms=threshold_ms,
                events_evaluated=len(events),
                deviations=deviations,
                average_abs_error_ms=avg_error,
                max_abs_error_ms=max_error,
            ),
            worst,
        )

    return TimingGridEvaluation(
        tempo_bpm=tempo_bpm,
        threshold_ms=threshold_ms,
        events_evaluated=len(events),
        deviations=deviations,
        average_abs_error_ms=avg_error,
        max_abs_error_ms=max_error,
        diagnosis_code=diagnosis_code,
        message=message,
    )


def render_timing_message(evaluation: TimingGridEvaluation, worst: TimingDeviation) -> str:
    """
    Render the coach message for a timing deviation.
    """
    direction = worst.event.direction
    offset = abs(worst.event.offset_ms)

    if direction == "late":
        return f"Timing deviation detected: {offset:.1f}ms late (threshold: {evaluation.threshold_ms:.0f}ms). Average error: {evaluation.average_abs_error_ms:.1f}ms."
    elif direction == "early":
        return f"Timing deviation detected: {offset:.1f}ms early (threshold: {evaluation.threshold_ms:.0f}ms). Average error: {evaluation.average_abs_error_ms:.1f}ms."
    else:
        return f"Timing deviation detected: {offset:.1f}ms off (threshold: {evaluation.threshold_ms:.0f}ms). Average error: {evaluation.average_abs_error_ms:.1f}ms."


def render_timing_suggestion(evaluation: TimingGridEvaluation) -> str:
    """
    Render a coaching suggestion based on timing deviation pattern.
    """
    if not evaluation.deviations:
        return "Timing is on target. Ready to increase tempo."

    # Count early vs late
    early_count = sum(1 for d in evaluation.deviations if d.event.direction == "early")
    late_count = sum(1 for d in evaluation.deviations if d.event.direction == "late")

    if early_count > late_count * 2:
        return "You're consistently rushing. Try relaxing and feeling the space between beats."
    elif late_count > early_count * 2:
        return "You're consistently dragging. Try anticipating the beat slightly."
    else:
        return f"Practice at a slower tempo to lock in the grid. Target: {evaluation.threshold_ms:.0f}ms accuracy."


__all__ = [
    "TimingEvent",
    "TimingDeviation",
    "TimingGridEvaluation",
    "evaluate_timing_grid",
    "render_timing_message",
    "render_timing_suggestion",
    "DEFAULT_THRESHOLD_MS",
]
