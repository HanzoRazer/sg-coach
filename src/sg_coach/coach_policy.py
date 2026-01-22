"""
Coach Policy — Rules-first evaluation of practice sessions.

Mode 1: Deterministic, schema-governed evaluation.
No LLM, no free-text generation. Pure signal extraction.
"""
from __future__ import annotations

from .schemas import (
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    SessionRecord,
    Severity,
)

COACH_VERSION = "coach-rules@0.1.0"


def evaluate_session(session: SessionRecord) -> CoachEvaluation:
    """
    Evaluate a practice session using deterministic rules.

    Returns a CoachEvaluation with:
    - findings: issues detected from timing/performance data
    - strengths/weaknesses: derived from error patterns
    - focus_recommendation: next practice focus area
    - confidence: rule confidence (high for clear signals)
    """
    findings: list[CoachFinding] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

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
