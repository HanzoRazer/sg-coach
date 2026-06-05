"""
Longitudinal Review Builder — Historical progress synthesis.

Sprint 28: Longitudinal Progress Review.

Provides:
- build_diagnosis_trend_summary(): Aggregate diagnosis trends over time
- build_outcome_trajectory_summary(): Aggregate outcomes across sessions
- build_longitudinal_progress_review(): Build complete longitudinal review

Core rules:
- Consumes RuntimeReviewReport as canonical evidence
- All analysis is deterministic
- No hidden scoring models
- Trends based on first-half vs second-half split
- Session-level recurrence, not assignment volume
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional, Sequence

from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.longitudinal_review import (
    LONGITUDINAL_REVIEW_VERSION,
    LongitudinalTrend,
    DiagnosisTrendSummary,
    OutcomeTrajectorySummary,
    LongitudinalProgressReview,
)
from sg_spec.schemas.runtime_review import RuntimeReviewReport
from sg_spec.schemas.user_feedback import PracticeOutcome


LONGITUDINAL_REVIEW_BUILDER_VERSION = "0.1.0"

MAX_NOTES = 5
TOP_N_ITEMS = 3


def _extract_diagnosis_codes_from_report(report: RuntimeReviewReport) -> set[DiagnosisCode]:
    """
    Extract unique diagnosis codes from a RuntimeReviewReport.

    Sources (in order of preference):
    - report.runtime_session.evaluation.findings
    - Falls back to empty set if no evaluation

    Returns at most one occurrence per DiagnosisCode per report.
    """
    codes: set[DiagnosisCode] = set()

    if report.runtime_session.evaluation is not None:
        for finding in report.runtime_session.evaluation.findings:
            if finding.code is not None:
                codes.add(finding.code)

    return codes


def _sort_reports_by_time(reports: Sequence[RuntimeReviewReport]) -> list[RuntimeReviewReport]:
    """Sort reports by generated_at timestamp ascending."""
    return sorted(reports, key=lambda r: r.generated_at)


def _split_historical_recent(
    reports: Sequence[RuntimeReviewReport],
) -> tuple[list[RuntimeReviewReport], list[RuntimeReviewReport]]:
    """
    Split reports into historical (first half) and recent (second half).

    Rules:
    - Sort by timestamp ascending
    - historical = first floor(n / 2)
    - recent = remaining reports
    """
    sorted_reports = _sort_reports_by_time(reports)
    n = len(sorted_reports)
    split_point = n // 2

    historical = sorted_reports[:split_point]
    recent = sorted_reports[split_point:]

    return historical, recent


def _compute_trend(
    historical_count: int,
    recent_count: int,
    total_reports: int,
) -> LongitudinalTrend:
    """
    Compute trend based on historical vs recent occurrence counts.

    Rules:
    - < 2 reports → insufficient_data
    - recent < historical → improving
    - recent == historical → stable
    - recent > historical → worsening
    """
    if total_reports < 2:
        return LongitudinalTrend.insufficient_data

    if recent_count < historical_count:
        return LongitudinalTrend.improving
    elif recent_count == historical_count:
        return LongitudinalTrend.stable
    else:
        return LongitudinalTrend.worsening


def _compute_improvement_ratio(
    historical_count: int,
    recent_count: int,
) -> Optional[float]:
    """
    Compute improvement ratio.

    Formula: max(0, historical - recent) / historical
    Returns None if historical_count == 0
    """
    if historical_count == 0:
        return None

    return max(0, historical_count - recent_count) / historical_count


def build_diagnosis_trend_summary(
    reports: Sequence[RuntimeReviewReport],
) -> list[DiagnosisTrendSummary]:
    """
    Build diagnosis trend summaries from runtime review reports.

    Parameters
    ----------
    reports:
        Sequence of RuntimeReviewReport to analyze.

    Returns
    -------
    List of DiagnosisTrendSummary, one per unique DiagnosisCode found.

    Notes
    -----
    - Counts each DiagnosisCode at most once per report (session-level)
    - Splits reports into historical (first half) and recent (second half)
    - Computes deterministic trends based on occurrence counts
    """
    if not reports:
        return []

    sorted_reports = _sort_reports_by_time(reports)
    historical, recent = _split_historical_recent(reports)

    diagnosis_data: dict[DiagnosisCode, dict] = defaultdict(lambda: {
        "total": 0,
        "historical": 0,
        "recent": 0,
        "first_at": None,
        "latest_at": None,
    })

    historical_set = set(id(r) for r in historical)

    for report in sorted_reports:
        codes = _extract_diagnosis_codes_from_report(report)
        is_historical = id(report) in historical_set

        for code in codes:
            data = diagnosis_data[code]
            data["total"] += 1

            if is_historical:
                data["historical"] += 1
            else:
                data["recent"] += 1

            if data["first_at"] is None:
                data["first_at"] = report.generated_at
            data["latest_at"] = report.generated_at

    summaries = []
    for code, data in diagnosis_data.items():
        trend = _compute_trend(
            data["historical"],
            data["recent"],
            len(reports),
        )
        improvement_ratio = _compute_improvement_ratio(
            data["historical"],
            data["recent"],
        )

        summaries.append(DiagnosisTrendSummary(
            diagnosis_code=code,
            total_occurrences=data["total"],
            first_occurrence_at=data["first_at"],
            latest_occurrence_at=data["latest_at"],
            recent_occurrence_count=data["recent"],
            historical_occurrence_count=data["historical"],
            trend=trend,
            improvement_ratio=improvement_ratio,
        ))

    return summaries


def build_outcome_trajectory_summary(
    reports: Sequence[RuntimeReviewReport],
) -> OutcomeTrajectorySummary:
    """
    Build outcome trajectory summary from runtime review reports.

    Parameters
    ----------
    reports:
        Sequence of RuntimeReviewReport to analyze.

    Returns
    -------
    OutcomeTrajectorySummary with aggregated outcome counts and ratios.

    Notes
    -----
    - total = completed + improved + repeated + worsened + abandoned
    - completion_ratio = (completed + improved) / total
    - improvement_ratio = improved / total
    - Ratios are None if total == 0
    """
    counts = {
        "completed": 0,
        "improved": 0,
        "repeated": 0,
        "worsened": 0,
        "abandoned": 0,
    }

    for report in reports:
        outcome = report.outcome_summary.outcome
        if outcome == PracticeOutcome.completed:
            counts["completed"] += 1
        elif outcome == PracticeOutcome.improved:
            counts["improved"] += 1
        elif outcome == PracticeOutcome.repeated:
            counts["repeated"] += 1
        elif outcome == PracticeOutcome.worsened:
            counts["worsened"] += 1
        elif outcome == PracticeOutcome.abandoned:
            counts["abandoned"] += 1

    total = sum(counts.values())

    completion_ratio: Optional[float] = None
    improvement_ratio: Optional[float] = None

    if total > 0:
        completion_ratio = (counts["completed"] + counts["improved"]) / total
        improvement_ratio = counts["improved"] / total

    return OutcomeTrajectorySummary(
        total_completed=counts["completed"],
        total_improved=counts["improved"],
        total_repeated=counts["repeated"],
        total_worsened=counts["worsened"],
        total_abandoned=counts["abandoned"],
        completion_ratio=completion_ratio,
        improvement_ratio=improvement_ratio,
    )


def _identify_strongest_improvements(
    trends: list[DiagnosisTrendSummary],
) -> list[str]:
    """
    Identify top N strongest improvements.

    Ordering:
    1. improvement_ratio descending
    2. total_occurrences descending
    3. DiagnosisCode.value alphabetical

    Returns DiagnosisCode.value strings, limited to TOP_N_ITEMS.
    """
    improving = [t for t in trends if t.trend == LongitudinalTrend.improving]

    def sort_key(t: DiagnosisTrendSummary) -> tuple:
        ratio = t.improvement_ratio if t.improvement_ratio is not None else 0.0
        return (-ratio, -t.total_occurrences, t.diagnosis_code.value)

    sorted_improving = sorted(improving, key=sort_key)

    return [t.diagnosis_code.value for t in sorted_improving[:TOP_N_ITEMS]]


def _identify_recurring_challenges(
    trends: list[DiagnosisTrendSummary],
) -> list[str]:
    """
    Identify top N recurring challenges.

    Ordering:
    1. worsening before stable
    2. total_occurrences descending
    3. DiagnosisCode.value alphabetical

    Returns DiagnosisCode.value strings, limited to TOP_N_ITEMS.
    """
    challenges = [
        t for t in trends
        if t.trend in (LongitudinalTrend.worsening, LongitudinalTrend.stable)
    ]

    def sort_key(t: DiagnosisTrendSummary) -> tuple:
        trend_priority = 0 if t.trend == LongitudinalTrend.worsening else 1
        return (trend_priority, -t.total_occurrences, t.diagnosis_code.value)

    sorted_challenges = sorted(challenges, key=sort_key)

    return [t.diagnosis_code.value for t in sorted_challenges[:TOP_N_ITEMS]]


def _generate_notes(
    trends: list[DiagnosisTrendSummary],
    review_count: int,
) -> list[str]:
    """
    Generate deterministic notes based on trends.

    Templates:
    - "{diagnosis} is improving over recent sessions."
    - "{diagnosis} remains recurring."
    - "{diagnosis} appears to be worsening."
    - "Insufficient evidence for stable trend analysis."

    Limited to MAX_NOTES.
    """
    notes: list[str] = []

    if review_count < 2:
        notes.append("Insufficient evidence for stable trend analysis.")
        return notes

    improving = [t for t in trends if t.trend == LongitudinalTrend.improving]
    for t in improving[:2]:
        label = t.diagnosis_code.value.replace("_", " ")
        notes.append(f"{label.capitalize()} is improving over recent sessions.")
        if len(notes) >= MAX_NOTES:
            return notes

    worsening = [t for t in trends if t.trend == LongitudinalTrend.worsening]
    for t in worsening[:2]:
        label = t.diagnosis_code.value.replace("_", " ")
        notes.append(f"{label.capitalize()} appears to be worsening.")
        if len(notes) >= MAX_NOTES:
            return notes

    stable = [t for t in trends if t.trend == LongitudinalTrend.stable]
    for t in stable[:1]:
        label = t.diagnosis_code.value.replace("_", " ")
        notes.append(f"{label.capitalize()} remains recurring.")
        if len(notes) >= MAX_NOTES:
            return notes

    return notes


def build_longitudinal_progress_review(
    *,
    reports: Sequence[RuntimeReviewReport],
    student_id: Optional[str] = None,
) -> LongitudinalProgressReview:
    """
    Build complete longitudinal progress review.

    Parameters
    ----------
    reports:
        Sequence of RuntimeReviewReport to analyze.
    student_id:
        Optional student identifier.

    Returns
    -------
    LongitudinalProgressReview with trends, trajectory, and notes.

    Notes
    -----
    - All analysis is deterministic
    - Trends based on first-half vs second-half temporal split
    - No AI/LLM text generation
    """
    diagnosis_trends = build_diagnosis_trend_summary(reports)
    outcome_trajectory = build_outcome_trajectory_summary(reports)

    strongest_improvements = _identify_strongest_improvements(diagnosis_trends)
    recurring_challenges = _identify_recurring_challenges(diagnosis_trends)

    evidence_review_ids = [r.runtime_session_id for r in reports]

    notes = _generate_notes(diagnosis_trends, len(reports))

    return LongitudinalProgressReview(
        student_id=student_id,
        review_count=len(reports),
        diagnosis_trends=diagnosis_trends,
        outcome_trajectory=outcome_trajectory,
        strongest_improvements=strongest_improvements,
        recurring_challenges=recurring_challenges,
        evidence_review_ids=evidence_review_ids,
        notes=notes,
    )


__all__ = [
    "LONGITUDINAL_REVIEW_BUILDER_VERSION",
    "build_diagnosis_trend_summary",
    "build_outcome_trajectory_summary",
    "build_longitudinal_progress_review",
]
