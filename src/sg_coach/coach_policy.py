"""
Coach Policy — Rules-first evaluation of practice sessions.

Mode 1: Deterministic, schema-governed evaluation.
No LLM, no free-text generation. Pure signal extraction.

Evaluator Pipeline:
    SessionRecord (with normalized inputs)
        → harmony evaluators (diminished_evaluator)
        → timing evaluators (timing_evaluator)
        → pitch evaluators (pitch_evaluator)
        → technique evaluators (future)
    → CoachEvaluation

Layer 1 Coaching Pipelines:
    - diminished_evaluator: DIM_ORBIT_VIOLATION
    - timing_evaluator: TIMING_GRID_DEVIATION
    - pitch_evaluator: WRONG_NOTE / PITCH_DEVIATION

Sprint 3: Evaluators read from session.normalized.
Legacy params are preserved for backward compatibility.
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
from .session_normalizer import normalize_session
from .exercise_classifier import (
    is_diminished_exercise,
    is_timing_grid_exercise,
    is_pitch_exercise,
    extract_key_from_program,
)
from .diminished_evaluator import build_context, evaluate_notes
from .timing_evaluator import evaluate_timing_grid
from .pitch_evaluator import evaluate_pitch_accuracy

COACH_VERSION = "coach-rules@0.4.0"


def _evaluate_diminished_harmony(session: SessionRecord) -> list[CoachFinding]:
    """
    Evaluate diminished orbit compliance for diminished-navigation exercises.

    Reads from session.normalized.harmony:
    - key: Music key for orbit computation
    - performed_notes: Pitch classes (0-11) that were performed
    - expected_orbit: Optional explicit orbit (computed from key if missing)

    Parameters
    ----------
    session:
        SessionRecord with normalized.harmony input.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for diminished exercises
    if not is_diminished_exercise(session.program_ref):
        return []

    # Require normalized harmony input
    if session.normalized is None or session.normalized.harmony is None:
        return []

    harmony = session.normalized.harmony
    if not harmony.performed_notes:
        return []

    # Get key: prefer harmony.key, fallback to session.key, then extract from program
    key = harmony.key or session.key or extract_key_from_program(session.program_ref)
    if key is None:
        return []

    # Run diminished orbit evaluation
    context = build_context(key)
    result = evaluate_notes(context, harmony.performed_notes)

    # Convert to CoachFinding if violation found
    finding = result.to_coach_finding()
    return [finding] if finding else []


def _evaluate_timing_grid(session: SessionRecord) -> list[CoachFinding]:
    """
    Evaluate timing grid compliance for timing-grid exercises.

    Reads from session.normalized.timing:
    - expected_times: Expected event times in seconds
    - performed_times: Performed event times in seconds
    - threshold_ms: Deviation threshold in milliseconds

    Parameters
    ----------
    session:
        SessionRecord with normalized.timing input.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for timing grid exercises
    if not is_timing_grid_exercise(session.program_ref):
        return []

    # Require normalized timing input
    if session.normalized is None or session.normalized.timing is None:
        return []

    timing = session.normalized.timing
    if len(timing.expected_times) == 0 or len(timing.performed_times) == 0:
        return []

    # Run timing grid evaluation
    result = evaluate_timing_grid(
        tempo_bpm=session.timing.bpm,
        expected_times=timing.expected_times,
        performed_times=timing.performed_times,
        threshold_ms=timing.threshold_ms,
    )

    # Convert to CoachFinding if deviation found
    finding = result.to_coach_finding()
    return [finding] if finding else []


def _evaluate_pitch_accuracy(session: SessionRecord) -> list[CoachFinding]:
    """
    Evaluate pitch accuracy for pitch-gated exercises.

    Reads from session.normalized.pitch:
    - expected_pitch_events: Expected note events with note/midi/pitch_hz fields
    - performed_pitch_events: Performed note events
    - cents_threshold: Pitch deviation threshold in cents

    Parameters
    ----------
    session:
        SessionRecord with normalized.pitch input.

    Returns
    -------
    List of CoachFindings (empty if clean or not applicable).
    """
    # Gate: only run for pitch exercises
    if not is_pitch_exercise(session.program_ref):
        return []

    # Require normalized pitch input
    if session.normalized is None or session.normalized.pitch is None:
        return []

    pitch = session.normalized.pitch
    if len(pitch.expected_pitch_events) == 0 or len(pitch.performed_pitch_events) == 0:
        return []

    # Run pitch accuracy evaluation
    return evaluate_pitch_accuracy(
        expected_notes=pitch.expected_pitch_events,
        performed_notes=pitch.performed_pitch_events,
        cents_threshold=pitch.cents_threshold,
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

    Preferred usage (Sprint 3):
        evaluate_session(session_with_normalized_inputs)

    Legacy usage (backward compatible):
        evaluate_session(session, expected_times=..., performed_times=...)

    Parameters
    ----------
    session:
        SessionRecord containing timing/performance data.
        Prefer using session.normalized for evaluator inputs.
    performed_notes:
        [DEPRECATED] Pitch classes (0-11) for harmony evaluation.
        Prefer session.normalized.harmony.performed_notes.
    expected_times:
        [DEPRECATED] Expected event times in seconds for timing evaluation.
        Prefer session.normalized.timing.expected_times.
    performed_times:
        [DEPRECATED] Performed event times in seconds for timing evaluation.
        Prefer session.normalized.timing.performed_times.
    timing_threshold_ms:
        [DEPRECATED] Deviation threshold for timing evaluation. Default 40ms.
        Prefer session.normalized.timing.threshold_ms.
    expected_pitch_events:
        [DEPRECATED] Expected note events for pitch evaluation.
        Prefer session.normalized.pitch.expected_pitch_events.
    performed_pitch_events:
        [DEPRECATED] Performed note events for pitch evaluation.
        Prefer session.normalized.pitch.performed_pitch_events.
    pitch_cents_threshold:
        [DEPRECATED] Pitch deviation threshold in cents. Default 25.
        Prefer session.normalized.pitch.cents_threshold.

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

    Precedence
    ----------
    Existing session.normalized wins over legacy params.
    """
    # Sprint 3: Normalize session from legacy params
    # Existing normalized data wins over legacy params
    session = normalize_session(
        session,
        performed_notes=performed_notes,
        expected_times=expected_times,
        performed_times=performed_times,
        timing_threshold_ms=timing_threshold_ms,
        expected_pitch_events=expected_pitch_events,
        performed_pitch_events=performed_pitch_events,
        pitch_cents_threshold=pitch_cents_threshold,
    )

    findings: list[CoachFinding] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

    # === Layer 1 Coaching Pipelines ===

    # Harmony: diminished orbit evaluation
    findings.extend(_evaluate_diminished_harmony(session))

    # Timing: grid deviation evaluation
    findings.extend(_evaluate_timing_grid(session))

    # Pitch: note identity and pitch deviation evaluation
    findings.extend(_evaluate_pitch_accuracy(session))

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
