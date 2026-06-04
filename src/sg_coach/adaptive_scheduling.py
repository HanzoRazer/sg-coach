"""
Adaptive Scheduling Engine — Evidence-Driven Queue Evolution.

Sprint 30: Evidence-Driven Adaptive Scheduling.

Provides:
- build_adaptive_scheduling_recommendations: Generate recommendations from ledger
- build_adaptive_scheduling_plan: Build complete scheduling plan
- apply_adaptive_recommendations_to_queue: Apply recommendations to queue

Core rules:
- All recommendations are evidence-backed
- Scheduling remains deterministic and explainable
- Recommendations are advisory; queue mutation is caller-controlled
- No hidden weights or opaque scoring
"""
from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence

from sg_spec.schemas.adaptive_scheduling import (
    AdaptiveSchedulingPlan,
    AdaptiveSchedulingRecommendation,
    SchedulingPriorityAdjustment,
    SchedulingRecommendationReason,
)
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceLedger,
    PedagogicalEvidenceSource,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueuePriority,
    ScheduledPracticeAssignment,
)


ADAPTIVE_SCHEDULING_VERSION = "0.1.0"

REPEATED_OUTCOME_THRESHOLD = 2
RECURRING_DIAGNOSIS_THRESHOLD = 3
ABANDONMENT_THRESHOLD = 1


def _generate_recommendation_id() -> str:
    """Generate unique recommendation ID."""
    return f"asr_{secrets.token_hex(6)}"


def _detect_worsening_trends(
    entries: list[PedagogicalEvidenceEntry],
) -> dict[DiagnosisCode | None, list[PedagogicalEvidenceEntry]]:
    """Detect worsening trends from longitudinal review entries."""
    worsening: dict[DiagnosisCode | None, list[PedagogicalEvidenceEntry]] = defaultdict(list)

    for entry in entries:
        if entry.source != PedagogicalEvidenceSource.longitudinal_review:
            continue

        trend = entry.metadata.get("trend")
        if trend == "worsening":
            worsening[entry.diagnosis_code].append(entry)

    return dict(worsening)


def _detect_improving_trends(
    entries: list[PedagogicalEvidenceEntry],
) -> dict[DiagnosisCode | None, list[PedagogicalEvidenceEntry]]:
    """Detect improving trends from longitudinal review entries."""
    improving: dict[DiagnosisCode | None, list[PedagogicalEvidenceEntry]] = defaultdict(list)

    for entry in entries:
        if entry.source != PedagogicalEvidenceSource.longitudinal_review:
            continue

        trend = entry.metadata.get("trend")
        if trend == "improving":
            improving[entry.diagnosis_code].append(entry)

    return dict(improving)


def _detect_repeated_outcomes(
    entries: list[PedagogicalEvidenceEntry],
) -> dict[tuple[DiagnosisCode | None, str | None], list[PedagogicalEvidenceEntry]]:
    """Detect repeated outcomes from assignment outcome entries."""
    repeated: dict[tuple[DiagnosisCode | None, str | None], list[PedagogicalEvidenceEntry]] = (
        defaultdict(list)
    )

    for entry in entries:
        if entry.source != PedagogicalEvidenceSource.assignment_outcome:
            continue

        outcome = entry.metadata.get("outcome")
        if outcome == "repeated":
            key = (entry.diagnosis_code, entry.assignment_id)
            repeated[key].append(entry)

    return dict(repeated)


def _detect_abandonment_patterns(
    entries: list[PedagogicalEvidenceEntry],
) -> dict[tuple[DiagnosisCode | None, str | None], list[PedagogicalEvidenceEntry]]:
    """Detect abandonment patterns from entries."""
    abandoned: dict[tuple[DiagnosisCode | None, str | None], list[PedagogicalEvidenceEntry]] = (
        defaultdict(list)
    )

    for entry in entries:
        is_abandoned = False

        if entry.source == PedagogicalEvidenceSource.assignment_outcome:
            if entry.metadata.get("outcome") == "abandoned":
                is_abandoned = True
        elif entry.source == PedagogicalEvidenceSource.queue_event:
            if entry.metadata.get("event_type") == "assignment_abandoned":
                is_abandoned = True

        if is_abandoned:
            key = (entry.diagnosis_code, entry.assignment_id)
            abandoned[key].append(entry)

    return dict(abandoned)


def _count_diagnosis_frequency(
    entries: list[PedagogicalEvidenceEntry],
) -> dict[DiagnosisCode, list[PedagogicalEvidenceEntry]]:
    """Count how often each diagnosis code appears."""
    counts: dict[DiagnosisCode, list[PedagogicalEvidenceEntry]] = defaultdict(list)

    for entry in entries:
        if entry.diagnosis_code is not None:
            counts[entry.diagnosis_code].append(entry)

    return dict(counts)


def _build_increase_priority_recommendation(
    *,
    diagnosis_code: DiagnosisCode | None,
    assignment_id: str | None,
    reasons: list[SchedulingRecommendationReason],
    evidence_entries: list[PedagogicalEvidenceEntry],
    rationale: str,
) -> AdaptiveSchedulingRecommendation | None:
    """Build an increase-priority recommendation."""
    if diagnosis_code is None and assignment_id is None:
        return None

    return AdaptiveSchedulingRecommendation(
        recommendation_id=_generate_recommendation_id(),
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        priority_adjustment=SchedulingPriorityAdjustment.increase,
        recommended_priority=PracticeQueuePriority.high,
        recommended_repetition_count=2,
        reasons=reasons,
        evidence_ids=[e.evidence_id for e in evidence_entries],
        rationale=rationale,
    )


def _build_decrease_priority_recommendation(
    *,
    diagnosis_code: DiagnosisCode | None,
    assignment_id: str | None,
    reasons: list[SchedulingRecommendationReason],
    evidence_entries: list[PedagogicalEvidenceEntry],
    rationale: str,
) -> AdaptiveSchedulingRecommendation | None:
    """Build a decrease-priority recommendation."""
    if diagnosis_code is None and assignment_id is None:
        return None

    return AdaptiveSchedulingRecommendation(
        recommendation_id=_generate_recommendation_id(),
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        priority_adjustment=SchedulingPriorityAdjustment.decrease,
        recommended_priority=PracticeQueuePriority.low,
        recommended_delay_days=3,
        reasons=reasons,
        evidence_ids=[e.evidence_id for e in evidence_entries],
        rationale=rationale,
    )


def _priority_sort_key(priority: PracticeQueuePriority | None) -> int:
    """Sort key for priority (higher priority = lower number = first)."""
    order = {
        PracticeQueuePriority.critical: 0,
        PracticeQueuePriority.high: 1,
        PracticeQueuePriority.normal: 2,
        PracticeQueuePriority.low: 3,
        None: 4,
    }
    return order.get(priority, 4)


def _sort_recommendations(
    recommendations: list[AdaptiveSchedulingRecommendation],
) -> list[AdaptiveSchedulingRecommendation]:
    """Sort recommendations deterministically."""
    return sorted(
        recommendations,
        key=lambda r: (
            _priority_sort_key(r.recommended_priority),
            -len(r.evidence_ids),
            r.diagnosis_code.value if r.diagnosis_code else "",
        ),
    )


def build_adaptive_scheduling_recommendations(
    *,
    ledger: PedagogicalEvidenceLedger,
    queue: PracticeQueue | None = None,
) -> list[AdaptiveSchedulingRecommendation]:
    """
    Build adaptive scheduling recommendations from ledger evidence.

    Analyzes evidence patterns and generates deterministic scheduling
    recommendations based on:
    - Worsening longitudinal trends
    - Improving longitudinal trends
    - Repeated outcomes
    - Abandonment patterns
    - Recurring diagnosis frequency

    Parameters
    ----------
    ledger:
        Pedagogical evidence ledger to analyze.
    queue:
        Optional practice queue for context (not currently used).

    Returns
    -------
    List of adaptive scheduling recommendations.
    """
    entries = ledger.entries
    recommendations: list[AdaptiveSchedulingRecommendation] = []
    processed_keys: set[tuple[DiagnosisCode | None, str | None]] = set()

    worsening_trends = _detect_worsening_trends(entries)
    for diagnosis_code, trend_entries in worsening_trends.items():
        key = (diagnosis_code, None)
        if key in processed_keys:
            continue

        code_str = diagnosis_code.value if diagnosis_code else "unknown"
        rationale = f"Worsening {code_str.replace('_', ' ')} trend suggests higher scheduling priority."

        rec = _build_increase_priority_recommendation(
            diagnosis_code=diagnosis_code,
            assignment_id=None,
            reasons=[SchedulingRecommendationReason.worsening_trend],
            evidence_entries=trend_entries,
            rationale=rationale,
        )
        if rec:
            recommendations.append(rec)
            processed_keys.add(key)

    abandonment_patterns = _detect_abandonment_patterns(entries)
    for (diagnosis_code, assignment_id), abandon_entries in abandonment_patterns.items():
        if len(abandon_entries) < ABANDONMENT_THRESHOLD:
            continue

        key = (diagnosis_code, assignment_id)
        if key in processed_keys:
            continue

        if diagnosis_code:
            code_str = diagnosis_code.value.replace("_", " ")
            rationale = f"Abandonment pattern for {code_str} requires attention."
        elif assignment_id:
            rationale = f"Abandonment pattern for assignment {assignment_id} requires attention."
        else:
            continue

        rec = _build_increase_priority_recommendation(
            diagnosis_code=diagnosis_code,
            assignment_id=assignment_id,
            reasons=[SchedulingRecommendationReason.abandonment_pattern],
            evidence_entries=abandon_entries,
            rationale=rationale,
        )
        if rec:
            recommendations.append(rec)
            processed_keys.add(key)

    repeated_outcomes = _detect_repeated_outcomes(entries)
    for (diagnosis_code, assignment_id), repeat_entries in repeated_outcomes.items():
        if len(repeat_entries) < REPEATED_OUTCOME_THRESHOLD:
            continue

        key = (diagnosis_code, assignment_id)
        if key in processed_keys:
            continue

        if diagnosis_code:
            code_str = diagnosis_code.value.replace("_", " ")
            rationale = f"Repeated outcomes for {code_str} justify increased repetition."
        elif assignment_id:
            rationale = f"Repeated outcomes for assignment {assignment_id} justify increased repetition."
        else:
            continue

        rec = _build_increase_priority_recommendation(
            diagnosis_code=diagnosis_code,
            assignment_id=assignment_id,
            reasons=[SchedulingRecommendationReason.repeated_outcomes],
            evidence_entries=repeat_entries,
            rationale=rationale,
        )
        if rec:
            recommendations.append(rec)
            processed_keys.add(key)

    diagnosis_frequency = _count_diagnosis_frequency(entries)
    for diagnosis_code, freq_entries in diagnosis_frequency.items():
        if len(freq_entries) < RECURRING_DIAGNOSIS_THRESHOLD:
            continue

        key = (diagnosis_code, None)
        if key in processed_keys:
            continue

        code_str = diagnosis_code.value.replace("_", " ")
        rationale = f"Recurring {code_str} issues justify increased repetition."

        rec = _build_increase_priority_recommendation(
            diagnosis_code=diagnosis_code,
            assignment_id=None,
            reasons=[SchedulingRecommendationReason.recurring_issue],
            evidence_entries=freq_entries,
            rationale=rationale,
        )
        if rec:
            recommendations.append(rec)
            processed_keys.add(key)

    improving_trends = _detect_improving_trends(entries)
    for diagnosis_code, trend_entries in improving_trends.items():
        key = (diagnosis_code, None)
        if key in processed_keys:
            continue

        code_str = diagnosis_code.value if diagnosis_code else "unknown"
        rationale = f"Improving {code_str.replace('_', ' ')} consistency supports reduced repetition intensity."

        rec = _build_decrease_priority_recommendation(
            diagnosis_code=diagnosis_code,
            assignment_id=None,
            reasons=[SchedulingRecommendationReason.improving_trend],
            evidence_entries=trend_entries,
            rationale=rationale,
        )
        if rec:
            recommendations.append(rec)
            processed_keys.add(key)

    return _sort_recommendations(recommendations)


def build_adaptive_scheduling_plan(
    *,
    ledger: PedagogicalEvidenceLedger,
    queue: PracticeQueue | None = None,
    student_id: str | None = None,
) -> AdaptiveSchedulingPlan:
    """
    Build complete adaptive scheduling plan from ledger evidence.

    Parameters
    ----------
    ledger:
        Pedagogical evidence ledger to analyze.
    queue:
        Optional practice queue for context.
    student_id:
        Optional student ID for the plan.

    Returns
    -------
    Complete adaptive scheduling plan.
    """
    recommendations = build_adaptive_scheduling_recommendations(
        ledger=ledger,
        queue=queue,
    )

    return AdaptiveSchedulingPlan(
        student_id=student_id or ledger.student_id,
        generated_at=datetime.now(timezone.utc),
        recommendations=recommendations,
        source_evidence_count=len(ledger.entries),
    )


def apply_adaptive_recommendations_to_queue(
    *,
    queue: PracticeQueue,
    recommendations: Sequence[AdaptiveSchedulingRecommendation],
) -> PracticeQueue:
    """
    Apply adaptive recommendations to a queue immutably.

    Updates assignment priority and stores adaptive metadata.
    Does not reorder assignments or change deferred_until.

    Parameters
    ----------
    queue:
        Practice queue to update.
    recommendations:
        Sequence of recommendations to apply.

    Returns
    -------
    New PracticeQueue with recommendations applied.
    """
    rec_by_assignment: dict[str, AdaptiveSchedulingRecommendation] = {}
    rec_by_diagnosis: dict[DiagnosisCode, AdaptiveSchedulingRecommendation] = {}

    for rec in recommendations:
        if rec.assignment_id:
            rec_by_assignment[rec.assignment_id] = rec
        if rec.diagnosis_code:
            rec_by_diagnosis[rec.diagnosis_code] = rec

    updated_assignments: list[ScheduledPracticeAssignment] = []

    for assignment in queue.assignments:
        rec: AdaptiveSchedulingRecommendation | None = None

        if assignment.assignment_id in rec_by_assignment:
            rec = rec_by_assignment[assignment.assignment_id]
        elif assignment.diagnosis_code and assignment.diagnosis_code in rec_by_diagnosis:
            rec = rec_by_diagnosis[assignment.diagnosis_code]

        if rec is None:
            updated_assignments.append(assignment)
            continue

        new_priority = assignment.priority
        if rec.recommended_priority is not None:
            new_priority = rec.recommended_priority

        new_metadata = dict(assignment.metadata)
        new_metadata["adaptive_scheduling"] = {
            "recommendation_id": rec.recommendation_id,
            "priority_adjustment": rec.priority_adjustment.value,
            "recommended_repetition_count": rec.recommended_repetition_count,
            "recommended_delay_days": rec.recommended_delay_days,
            "evidence_ids": rec.evidence_ids,
        }

        updated_assignment = ScheduledPracticeAssignment(
            scheduled_id=assignment.scheduled_id,
            queue_id=assignment.queue_id,
            assignment_id=assignment.assignment_id,
            student_id=assignment.student_id,
            diagnosis_code=assignment.diagnosis_code,
            title=assignment.title,
            status=assignment.status,
            priority=new_priority,
            scheduled_order=assignment.scheduled_order,
            estimated_minutes=assignment.estimated_minutes,
            scheduled_for=assignment.scheduled_for,
            created_at=assignment.created_at,
            completed_at=assignment.completed_at,
            deferred_until=assignment.deferred_until,
            metadata=new_metadata,
            version=assignment.version,
        )
        updated_assignments.append(updated_assignment)

    return PracticeQueue(
        id=queue.id,
        student_id=queue.student_id,
        assignments=updated_assignments,
        generated_at=queue.generated_at,
        version=queue.version,
    )


__all__ = [
    "ADAPTIVE_SCHEDULING_VERSION",
    "REPEATED_OUTCOME_THRESHOLD",
    "RECURRING_DIAGNOSIS_THRESHOLD",
    "ABANDONMENT_THRESHOLD",
    "build_adaptive_scheduling_recommendations",
    "build_adaptive_scheduling_plan",
    "apply_adaptive_recommendations_to_queue",
]
