"""
Coach Policy v1 (Mode 1: rules-first deterministic).

Pure function: SessionRecord -> CoachEvaluation.
All text is templated; no AI phrasing.
"""
from __future__ import annotations

from uuid import uuid4

from .schemas import (
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    SessionRecord,
    Severity,
)


COACH_VERSION = "coach-rules@0.1.0"
STEP_ERROR_THRESHOLD_MS = 35.0


def evaluate_session(session: SessionRecord) -> CoachEvaluation:
    """
    Deterministic Mode-1 evaluation of a session.

    1. Analyze timing errors by step
    2. Classify severity
    3. Produce structured findings with evidence
    4. Return CoachEvaluation
    """
    findings: list[CoachFinding] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

    # Find worst step(s)
    error_by_step = session.performance.error_by_step
    if error_by_step:
        sorted_steps = sorted(
            error_by_step.items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )
        worst_step, worst_error = sorted_steps[0]
        worst_step_int = int(worst_step)

        # Primary finding: worst step
        if abs(worst_error) >= STEP_ERROR_THRESHOLD_MS:
            findings.append(
                CoachFinding(
                    type="timing",
                    severity=Severity.primary,
                    evidence=FindingEvidence(
                        step=worst_step_int,
                        mean_error_ms=worst_error,
                    ),
                    interpretation=f"Step {worst_step} shows timing drift ({worst_error:+.1f} ms).",
                )
            )
            weaknesses.append(f"Timing on step {worst_step}")
        else:
            strengths.append("Consistent timing across all steps")

        # Secondary findings for other steps above threshold
        for step_str, err in sorted_steps[1:]:
            if abs(err) >= STEP_ERROR_THRESHOLD_MS:
                findings.append(
                    CoachFinding(
                        type="timing",
                        severity=Severity.secondary,
                        evidence=FindingEvidence(
                            step=int(step_str),
                            mean_error_ms=err,
                        ),
                        interpretation=f"Step {step_str} also shows drift ({err:+.1f} ms).",
                    )
                )
    else:
        # No per-step data: use aggregate
        if session.performance.timing_error_ms.mean >= STEP_ERROR_THRESHOLD_MS:
            findings.append(
                CoachFinding(
                    type="timing",
                    severity=Severity.primary,
                    evidence=FindingEvidence(
                        mean_error_ms=session.performance.timing_error_ms.mean,
                    ),
                    interpretation="Overall timing shows drift.",
                )
            )
            weaknesses.append("Overall timing consistency")
        else:
            strengths.append("Solid timing")

    # Dropped notes finding
    if session.performance.notes_dropped > 0:
        ratio = session.performance.notes_dropped / max(1, session.performance.notes_expected)
        sev = Severity.primary if ratio > 0.1 else Severity.secondary
        findings.append(
            CoachFinding(
                type="consistency",
                severity=sev,
                evidence=FindingEvidence(
                    metric="notes_dropped",
                    value=session.performance.notes_dropped,
                ),
                interpretation=f"{session.performance.notes_dropped} notes dropped ({ratio * 100:.0f}%).",
            )
        )
        weaknesses.append("Note consistency")

    # Focus recommendation
    if findings:
        top = findings[0]
        focus_concept = f"{top.type}:step_{top.evidence.step}" if top.evidence.step is not None else top.type
        focus = FocusRecommendation(
            concept=focus_concept,
            reason=top.interpretation,
        )
    else:
        focus = FocusRecommendation(
            concept="maintain",
            reason="Keep practicing at current level.",
        )

    # Confidence: higher when more data
    confidence = min(1.0, 0.5 + 0.1 * len(error_by_step))

    return CoachEvaluation(
        session_id=session.session_id,
        coach_version=COACH_VERSION,
        findings=findings,
        strengths=strengths,
        weaknesses=weaknesses,
        focus_recommendation=focus,
        confidence=confidence,
    )


__all__ = ["evaluate_session", "COACH_VERSION"]
