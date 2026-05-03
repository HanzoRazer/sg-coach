"""
Coach Policy — Rules-first evaluation of practice sessions.

Mode 1: Deterministic, schema-governed evaluation.
No LLM, no free-text generation. Pure signal extraction.

Evaluator Pipeline:
    SessionRecord + optional event data
        → timing evaluators (built-in + timing_evaluator)
        → harmony evaluators (diminished_evaluator)
        → pitch evaluators (pitch_evaluator)
        → technique evaluators (future)
    → CoachEvaluation

Layer 1 Coaching Pipelines:
    - diminished_evaluator: DIM_ORBIT_VIOLATION
    - timing_evaluator: TIMING_GRID_DEVIATION
    - pitch_evaluator: WRONG_NOTE / PITCH_DEVIATION
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .schemas import (
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    SessionRecord,
    Severity,
)
from .exercise_classifier import (
    is_diminished_exercise,
    is_timing_grid_exercise,
    is_pitch_exercise,
    extract_key_from_program,
)
from .diminished_evaluator import build_context, evaluate_notes
from .timing_evaluator import evaluate_timing_grid
from .pitch_evaluator import evaluate_pitch_accuracy

COACH_VERSION = "coach-rules@0.3.0"


def _evaluate_diminished_harmony(
    session: SessionRecord,
    performed_notes: Optional[Sequence[int]] = None,
) -> list[CoachFinding]:
    """
    Evaluate diminished orbit compliance for diminished-navigation exercises.

    Parameters
    ----------
    session:
        The session record containing program_ref.
    performed_notes:
        Optional sequence of pitch classes (0-11) that were performed.
        Required for actual evaluation; if None, returns empty list.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for diminished exercises
    if not is_diminished_exercise(session.program_ref):
        return []

    # Require note data for evaluation
    if performed_notes is None:
        return []

    # Extract key from program name
    key = extract_key_from_program(session.program_ref)
    if key is None:
        return []

    # Run diminished orbit evaluation
    context = build_context(key)
    result = evaluate_notes(context, performed_notes)

    # Convert to CoachFinding if violation found
    finding = result.to_coach_finding()
    return [finding] if finding else []


def _evaluate_timing_grid(
    session: SessionRecord,
    expected_times: Optional[Sequence[float]] = None,
    performed_times: Optional[Sequence[float]] = None,
    threshold_ms: float = 40.0,
) -> list[CoachFinding]:
    """
    Evaluate timing grid compliance for timing-grid exercises.

    Parameters
    ----------
    session:
        The session record containing program_ref and timing.
    expected_times:
        Sequence of expected event times in seconds.
    performed_times:
        Sequence of performed event times in seconds.
    threshold_ms:
        Deviation threshold in milliseconds. Default 40ms.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for timing grid exercises
    if not is_timing_grid_exercise(session.program_ref):
        return []

    # Require timing data for evaluation
    if expected_times is None or performed_times is None:
        return []

    if len(expected_times) == 0 or len(performed_times) == 0:
        return []

    # Run timing grid evaluation
    result = evaluate_timing_grid(
        tempo_bpm=session.timing.bpm,
        expected_times=expected_times,
        performed_times=performed_times,
        threshold_ms=threshold_ms,
    )

    # Convert to CoachFinding if deviation found
    finding = result.to_coach_finding()
    return [finding] if finding else []


def _evaluate_pitch_accuracy(
    session: SessionRecord,
    expected_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    performed_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    cents_threshold: float = 25.0,
) -> list[CoachFinding]:
    """
    Evaluate pitch accuracy for pitch-gated exercises.

    Parameters
    ----------
    session:
        The session record containing program_ref.
    expected_pitch_events:
        Sequence of expected note events with note/midi/pitch_hz fields.
    performed_pitch_events:
        Sequence of performed note events with note/midi/pitch_hz fields.
    cents_threshold:
        Pitch deviation threshold in cents. Default 25.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for pitch exercises
    if not is_pitch_exercise(session.program_ref):
        return []

    # Require both expected and performed data
    if expected_pitch_events is None or performed_pitch_events is None:
        return []

    if len(expected_pitch_events) == 0 or len(performed_pitch_events) == 0:
        return []

    # Run pitch accuracy evaluation
    return evaluate_pitch_accuracy(
        expected_notes=expected_pitch_events,
        performed_notes=performed_pitch_events,
        cents_threshold=cents_threshold,
    )


def evaluate_session(
    session: SessionRecord,
    performed_notes: Optional[Sequence[int]] = None,
    expected_times: Optional[Sequence[float]] = None,
    performed_times: Optional[Sequence[float]] = None,
    timing_threshold_ms: float = 40.0,
    expected_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    performed_pitch_events: Optional[Sequence[Mapping[str, Any]]] = None,
    pitch_cents_threshold: float = 25.0,
) -> CoachEvaluation:
    """
    Evaluate a practice session using deterministic rules.

    Parameters
    ----------
    session:
        SessionRecord containing timing/performance data.
    performed_notes:
        Optional sequence of pitch classes (0-11) for harmony evaluation.
        Required for diminished orbit checks.
    expected_times:
        Optional sequence of expected event times in seconds for timing evaluation.
    performed_times:
        Optional sequence of performed event times in seconds for timing evaluation.
    timing_threshold_ms:
        Deviation threshold for timing evaluation. Default 40ms.
    expected_pitch_events:
        Optional sequence of expected note events for pitch evaluation.
        Each event may have: note, midi, pitch_hz, index, time_sec.
    performed_pitch_events:
        Optional sequence of performed note events for pitch evaluation.
        Same structure as expected_pitch_events.
    pitch_cents_threshold:
        Pitch deviation threshold in cents. Default 25.

    Returns
    -------
    CoachEvaluation with:
    - findings: issues detected from timing/performance/harmony/pitch data
    - strengths/weaknesses: derived from error patterns
    - focus_recommendation: next practice focus area
    - confidence: rule confidence (high for clear signals)

    Pipeline (Layer 1 Coaching)
    ---------------------------
    1. Harmony evaluators:
       - diminished_evaluator: DIM_ORBIT_VIOLATION
    2. Timing evaluators:
       - timing_evaluator: TIMING_GRID_DEVIATION
       - built-in timing rules (aggregate stats)
    3. Pitch evaluators:
       - pitch_evaluator: WRONG_NOTE / PITCH_DEVIATION
    4. Technique evaluators (future)
    """
    findings: list[CoachFinding] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

    # === Layer 1 Coaching Pipelines ===

    # Harmony: diminished orbit evaluation
    findings.extend(_evaluate_diminished_harmony(session, performed_notes))

    # Timing: grid deviation evaluation
    findings.extend(_evaluate_timing_grid(
        session, expected_times, performed_times, timing_threshold_ms
    ))

    # Pitch: note identity and pitch deviation evaluation
    findings.extend(_evaluate_pitch_accuracy(
        session, expected_pitch_events, performed_pitch_events, pitch_cents_threshold
    ))

    # Extract timing stats from performance summary
    perf = session.performance
    timing_stats = perf.timing_error_ms
    mean_error = timing_stats.mean
    max_error = timing_stats.max

    # Rule 1: Timing precision assessment
    if mean_error < 15:
        strengths.append("Excellent timing precision")
    elif mean_error < 30:
        strengths.append("Good timing consistency")
    elif mean_error < 50:
        weaknesses.append("Timing needs attention")
        findings.append(
            CoachFinding(
                type="timing",
                severity=Severity.secondary,
                evidence=FindingEvidence(mean_error_ms=mean_error),
                interpretation=f"Mean timing error of {mean_error:.1f}ms suggests room for improvement",
            )
        )
    else:
        weaknesses.append("Significant timing issues")
        findings.append(
            CoachFinding(
                type="timing",
                severity=Severity.primary,
                evidence=FindingEvidence(mean_error_ms=mean_error),
                interpretation=f"Mean timing error of {mean_error:.1f}ms requires focused practice",
            )
        )

    # Rule 2: Per-step error analysis
    if perf.error_by_step:
        worst_steps = sorted(
            perf.error_by_step.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        for step, error in worst_steps:
            if error > 40:
                findings.append(
                    CoachFinding(
                        type="timing",
                        severity=Severity.secondary,
                        evidence=FindingEvidence(metric="step_error", value=error),
                        interpretation=f"Step {step} has high error ({error:.1f}ms)",
                    )
                )

    # Rule 3: Consistency check (spread between mean and max)
    spread = max_error - mean_error
    if spread < 20:
        strengths.append("Consistent performance across session")
    elif spread > 50:
        weaknesses.append("Inconsistent timing throughout session")

    # Rule 4: Note accuracy
    if perf.notes_expected > 0:
        accuracy = perf.notes_played / perf.notes_expected
        if accuracy >= 0.95:
            strengths.append("High note accuracy")
        elif accuracy < 0.8:
            weaknesses.append("Many missed notes")
            findings.append(
                CoachFinding(
                    type="technique",
                    severity=Severity.secondary,
                    evidence=FindingEvidence(metric="note_accuracy", value=accuracy),
                    interpretation=f"Only {accuracy*100:.0f}% of expected notes were played",
                )
            )

    # Determine focus recommendation
    if weaknesses and "timing" in " ".join(weaknesses).lower():
        focus = FocusRecommendation(
            concept="timing_precision",
            reason="Focus on steady tempo with metronome at slower BPM",
        )
    elif weaknesses and "missed" in " ".join(weaknesses).lower():
        focus = FocusRecommendation(
            concept="note_accuracy",
            reason="Practice at slower tempo to improve note hitting",
        )
    elif not strengths:
        focus = FocusRecommendation(
            concept="fundamentals",
            reason="Build foundation with basic exercises",
        )
    else:
        focus = FocusRecommendation(
            concept="advancement",
            reason="Ready to increase difficulty or add complexity",
        )

    # Calculate confidence based on data quality
    confidence = 0.9 if perf.bars_played > 0 else 0.5

    return CoachEvaluation(
        session_id=session.session_id,
        coach_version=COACH_VERSION,
        findings=findings,
        strengths=strengths,
        weaknesses=weaknesses,
        focus_recommendation=focus,
        confidence=confidence,
    )
