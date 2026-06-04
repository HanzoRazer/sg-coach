"""
Runtime Review Builder — Human-readable practice attempt summaries.

Sprint 27: Runtime Evidence Review Report.

Provides:
- build_runtime_evidence_summary(): Summarize evidence attached to runtime session
- build_runtime_outcome_summary(): Summarize outcome and progression
- build_runtime_review_report(): Build complete review report

Core rules:
- Reports are derived artifacts, not canonical state
- Reports are deterministic and reproducible
- Missing evidence degrades gracefully
- No state mutation
"""
from __future__ import annotations

from typing import Optional

from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.runtime_flow import (
    RuntimePracticeSession,
    RuntimeSessionResult,
)
from sg_spec.schemas.runtime_review import (
    RUNTIME_REVIEW_VERSION,
    RuntimeReviewStatus,
    RuntimeEvidenceSummary,
    RuntimeOutcomeSummary,
    RuntimeReviewReport,
    _rebuild_models,
)

_rebuild_models()


RUNTIME_REVIEW_BUILDER_VERSION = "0.1.0"


def build_runtime_evidence_summary(
    runtime_session: RuntimePracticeSession,
) -> RuntimeEvidenceSummary:
    """
    Build evidence summary from runtime session.

    Parameters
    ----------
    runtime_session:
        The runtime session to summarize.

    Returns
    -------
    RuntimeEvidenceSummary with evidence availability and counts.

    Notes
    -----
    Missing evidence degrades gracefully — counts remain 0.
    """
    has_session_record = runtime_session.session_record is not None
    has_evaluation = runtime_session.evaluation is not None

    finding_count = 0
    recommendation_count = 0

    if has_evaluation and runtime_session.evaluation is not None:
        finding_count = len(runtime_session.evaluation.findings)

        if runtime_session.evaluation.recommendations:
            recommendation_count = sum(
                len(rec_set.actions)
                for rec_set in runtime_session.evaluation.recommendations
            )

    assignment_count = 1 if runtime_session.assignment is not None else 0

    return RuntimeEvidenceSummary(
        has_session_record=has_session_record,
        has_evaluation=has_evaluation,
        finding_count=finding_count,
        recommendation_count=recommendation_count,
        assignment_count=assignment_count,
    )


def build_runtime_outcome_summary(
    result: Optional[RuntimeSessionResult],
) -> RuntimeOutcomeSummary:
    """
    Build outcome summary from runtime session result.

    Parameters
    ----------
    result:
        The runtime session result, or None for evidence-only reviews.

    Returns
    -------
    RuntimeOutcomeSummary with outcome and progression information.

    Notes
    -----
    If result is None, returns defaults (no outcome, no updates).
    """
    if result is None:
        return RuntimeOutcomeSummary()

    next_curriculum_content_id: Optional[str] = None

    if result.integration_result is not None:
        if result.integration_result.curriculum_recommendation is not None:
            next_curriculum_content_id = (
                result.integration_result.curriculum_recommendation.content_id
            )

    outcome = None
    if result.outcome_event is not None:
        outcome = result.outcome_event.outcome

    return RuntimeOutcomeSummary(
        outcome=outcome,
        queue_updated=result.queue_updated,
        curriculum_advanced=result.curriculum_advanced,
        next_curriculum_content_id=next_curriculum_content_id,
        reasons=list(result.reasons) if result.reasons else [],
    )


def _resolve_status(evidence_summary: RuntimeEvidenceSummary) -> RuntimeReviewStatus:
    """
    Determine review status from evidence summary.

    Rules:
    - complete: has both session_record AND evaluation
    - partial: has some evidence but not all
    - missing_evidence: has neither session_record nor evaluation
    """
    has_both = evidence_summary.has_session_record and evidence_summary.has_evaluation
    has_none = (
        not evidence_summary.has_session_record and not evidence_summary.has_evaluation
    )

    if has_both:
        return RuntimeReviewStatus.complete
    elif has_none:
        return RuntimeReviewStatus.missing_evidence
    else:
        return RuntimeReviewStatus.partial


def _extract_diagnosis_code(
    runtime_session: RuntimePracticeSession,
) -> Optional[DiagnosisCode]:
    """
    Extract diagnosis code from runtime session assignment.

    Attempts to parse string to DiagnosisCode enum.
    Returns None if invalid or missing.
    """
    if runtime_session.assignment is None:
        return None

    raw_code = runtime_session.assignment.diagnosis_code
    if raw_code is None:
        return None

    if isinstance(raw_code, DiagnosisCode):
        return raw_code

    try:
        return DiagnosisCode(raw_code)
    except ValueError:
        return None


def build_runtime_review_report(
    *,
    runtime_session: RuntimePracticeSession,
    runtime_result: Optional[RuntimeSessionResult] = None,
) -> RuntimeReviewReport:
    """
    Build complete runtime review report.

    Parameters
    ----------
    runtime_session:
        The runtime session to review.
    runtime_result:
        Optional result from session completion.

    Returns
    -------
    RuntimeReviewReport with evidence and outcome summaries.

    Notes
    -----
    This function is pure — no state mutation.
    Reports are self-contained with embedded runtime session.
    """
    evidence_summary = build_runtime_evidence_summary(runtime_session)
    outcome_summary = build_runtime_outcome_summary(runtime_result)
    status = _resolve_status(evidence_summary)

    return RuntimeReviewReport(
        runtime_session_id=runtime_session.runtime_session_id,
        status=status,
        student_id=runtime_session.student_id,
        assignment_id=runtime_session.assignment_id,
        queue_id=runtime_session.queue_id,
        diagnosis_code=_extract_diagnosis_code(runtime_session),
        runtime_session=runtime_session,
        evidence_summary=evidence_summary,
        outcome_summary=outcome_summary,
    )


__all__ = [
    "RUNTIME_REVIEW_BUILDER_VERSION",
    "build_runtime_evidence_summary",
    "build_runtime_outcome_summary",
    "build_runtime_review_report",
]
