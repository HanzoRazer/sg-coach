"""
Teacher Scheduling Mediation — Human-in-the-loop adaptive governance.

Sprint 31: Teacher-Adaptive Scheduling Mediation.
Sprint 32: Teacher-Governed Adaptive Scheduling.

Provides:
- create_teacher_scheduling_mediation(): Create mediation from recommendation
- effective_recommendation_from_mediation(): Get effective recommendation after mediation
- effective_scheduling_decision_from_mediation(): Get governance-oriented decision wrapper
- apply_mediation_to_queue(): Apply mediated recommendation to queue

Core rules:
- Mediations are append-only and immutable
- Teacher authority is final over adaptive recommendations
- All mediations preserve full audit trail
- Queue mutation remains caller-controlled
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional, Sequence

from sg_spec.schemas.adaptive_scheduling import (
    AdaptiveSchedulingRecommendation,
    SchedulingPriorityAdjustment,
)
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueuePriority,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.teacher_scheduling_mediation import (
    EffectiveSchedulingDecision,
    MediationAction,
    TeacherSchedulingMediation,
    TeacherSchedulingOverride,
)


TEACHER_SCHEDULING_MEDIATION_VERSION = "0.1.0"


def _generate_mediation_id() -> str:
    """Generate unique mediation ID."""
    return f"tsm_{secrets.token_hex(6)}"


def create_teacher_scheduling_mediation(
    *,
    recommendation: AdaptiveSchedulingRecommendation,
    teacher_id: str,
    action: MediationAction,
    student_id: Optional[str] = None,
    override: Optional[TeacherSchedulingOverride] = None,
    rationale: Optional[str] = None,
    prior_mediation_id: Optional[str] = None,
    teacher_review_id: Optional[str] = None,
    mediation_id: Optional[str] = None,
) -> TeacherSchedulingMediation:
    """
    Create a teacher scheduling mediation from a recommendation.

    Parameters
    ----------
    recommendation:
        The adaptive scheduling recommendation being mediated.
    teacher_id:
        ID of the teacher making the mediation decision.
    action:
        The mediation action (approve, approve_modified, reject, defer).
    student_id:
        Optional student ID (defaults to recommendation context).
    override:
        Teacher's modifications for approve_modified action.
    rationale:
        Teacher's rationale for the decision.
    prior_mediation_id:
        ID of prior mediation if this revises a decision.
    teacher_review_id:
        Related teacher review ID if applicable.
    mediation_id:
        Optional explicit mediation ID.

    Returns
    -------
    TeacherSchedulingMediation record.
    """
    return TeacherSchedulingMediation(
        id=mediation_id or _generate_mediation_id(),
        recommendation_id=recommendation.recommendation_id,
        teacher_id=teacher_id,
        student_id=student_id,
        diagnosis_code=recommendation.diagnosis_code,
        assignment_id=recommendation.assignment_id,
        action=action,
        override=override,
        rationale=rationale,
        prior_mediation_id=prior_mediation_id,
        teacher_review_id=teacher_review_id,
        metadata={
            "original_priority_adjustment": recommendation.priority_adjustment.value,
            "original_recommended_priority": (
                recommendation.recommended_priority.value
                if recommendation.recommended_priority
                else None
            ),
            "original_recommended_repetition_count": recommendation.recommended_repetition_count,
            "original_recommended_delay_days": recommendation.recommended_delay_days,
        },
    )


def effective_recommendation_from_mediation(
    *,
    mediation: TeacherSchedulingMediation,
    original_recommendation: AdaptiveSchedulingRecommendation,
) -> Optional[AdaptiveSchedulingRecommendation]:
    """
    Get the effective recommendation after teacher mediation.

    For approve: returns original unchanged.
    For approve_modified: returns recommendation with teacher overrides applied.
    For reject/defer: returns None (no recommendation to apply).

    Parameters
    ----------
    mediation:
        The teacher's mediation decision.
    original_recommendation:
        The original adaptive scheduling recommendation.

    Returns
    -------
    Effective recommendation to apply, or None if rejected/deferred.
    """
    if mediation.action == MediationAction.reject:
        return None

    if mediation.action == MediationAction.defer:
        return None

    if mediation.action == MediationAction.approve:
        return AdaptiveSchedulingRecommendation(
            recommendation_id=original_recommendation.recommendation_id,
            assignment_id=original_recommendation.assignment_id,
            diagnosis_code=original_recommendation.diagnosis_code,
            priority_adjustment=original_recommendation.priority_adjustment,
            recommended_priority=original_recommendation.recommended_priority,
            recommended_repetition_count=original_recommendation.recommended_repetition_count,
            recommended_delay_days=original_recommendation.recommended_delay_days,
            reasons=original_recommendation.reasons,
            evidence_ids=original_recommendation.evidence_ids,
            rationale=original_recommendation.rationale,
            metadata={
                **original_recommendation.metadata,
                "mediation_id": mediation.id,
                "mediation_action": mediation.action.value,
            },
        )

    if mediation.action == MediationAction.approve_modified:
        if mediation.override is None:
            return None

        new_priority = (
            mediation.override.recommended_priority
            if mediation.override.recommended_priority is not None
            else original_recommendation.recommended_priority
        )
        new_repetition = (
            mediation.override.recommended_repetition_count
            if mediation.override.recommended_repetition_count is not None
            else original_recommendation.recommended_repetition_count
        )
        new_delay = (
            mediation.override.recommended_delay_days
            if mediation.override.recommended_delay_days is not None
            else original_recommendation.recommended_delay_days
        )

        return AdaptiveSchedulingRecommendation(
            recommendation_id=original_recommendation.recommendation_id,
            assignment_id=original_recommendation.assignment_id,
            diagnosis_code=original_recommendation.diagnosis_code,
            priority_adjustment=original_recommendation.priority_adjustment,
            recommended_priority=new_priority,
            recommended_repetition_count=new_repetition,
            recommended_delay_days=new_delay,
            reasons=original_recommendation.reasons,
            evidence_ids=original_recommendation.evidence_ids,
            rationale=original_recommendation.rationale,
            metadata={
                **original_recommendation.metadata,
                "mediation_id": mediation.id,
                "mediation_action": mediation.action.value,
                "teacher_override": {
                    "recommended_priority": (
                        mediation.override.recommended_priority.value
                        if mediation.override.recommended_priority
                        else None
                    ),
                    "recommended_repetition_count": mediation.override.recommended_repetition_count,
                    "recommended_delay_days": mediation.override.recommended_delay_days,
                },
            },
        )

    return None


def effective_scheduling_decision_from_mediation(
    *,
    recommendation: AdaptiveSchedulingRecommendation,
    mediation: TeacherSchedulingMediation,
) -> EffectiveSchedulingDecision:
    """
    Build a governance-oriented effective scheduling decision from mediation.

    This provides explicit governance flags (approved, rejected, deferred)
    for audit and traceability purposes.

    Parameters
    ----------
    recommendation:
        The original adaptive scheduling recommendation.
    mediation:
        The teacher's mediation decision.

    Returns
    -------
    EffectiveSchedulingDecision with governance state and effective values.
    """
    approved = mediation.action in {MediationAction.approve, MediationAction.approve_modified}
    rejected = mediation.action == MediationAction.reject
    deferred = mediation.action == MediationAction.defer

    effective_priority: Optional[PracticeQueuePriority] = None
    effective_repetition_count: Optional[int] = None
    effective_delay_days: Optional[int] = None

    if approved:
        if mediation.action == MediationAction.approve_modified and mediation.override:
            effective_priority = (
                mediation.override.recommended_priority
                if mediation.override.recommended_priority is not None
                else recommendation.recommended_priority
            )
            effective_repetition_count = (
                mediation.override.recommended_repetition_count
                if mediation.override.recommended_repetition_count is not None
                else recommendation.recommended_repetition_count
            )
            effective_delay_days = (
                mediation.override.recommended_delay_days
                if mediation.override.recommended_delay_days is not None
                else recommendation.recommended_delay_days
            )
        else:
            effective_priority = recommendation.recommended_priority
            effective_repetition_count = recommendation.recommended_repetition_count
            effective_delay_days = recommendation.recommended_delay_days

    return EffectiveSchedulingDecision(
        recommendation_id=recommendation.recommendation_id,
        mediation_id=mediation.id,
        approved=approved,
        rejected=rejected,
        deferred=deferred,
        effective_priority=effective_priority,
        effective_repetition_count=effective_repetition_count,
        effective_delay_days=effective_delay_days,
        evidence_ids=list(recommendation.evidence_ids),
        rationale=mediation.rationale,
    )


def apply_mediation_to_queue(
    *,
    queue: PracticeQueue,
    mediation: TeacherSchedulingMediation,
    original_recommendation: AdaptiveSchedulingRecommendation,
) -> PracticeQueue:
    """
    Apply a mediated recommendation to a queue.

    For approved mediations, applies the effective recommendation.
    For rejected/deferred mediations, adds mediation metadata but no priority change.

    Parameters
    ----------
    queue:
        Practice queue to update.
    mediation:
        The teacher's mediation decision.
    original_recommendation:
        The original adaptive scheduling recommendation.

    Returns
    -------
    New PracticeQueue with mediation applied.
    """
    effective_rec = effective_recommendation_from_mediation(
        mediation=mediation,
        original_recommendation=original_recommendation,
    )

    updated_assignments: list[ScheduledPracticeAssignment] = []

    for assignment in queue.assignments:
        matches = False

        if original_recommendation.assignment_id:
            if assignment.assignment_id == original_recommendation.assignment_id:
                matches = True
        elif original_recommendation.diagnosis_code:
            if assignment.diagnosis_code == original_recommendation.diagnosis_code:
                matches = True

        if not matches:
            updated_assignments.append(assignment)
            continue

        new_priority = assignment.priority
        if effective_rec is not None and effective_rec.recommended_priority is not None:
            new_priority = effective_rec.recommended_priority

        mediation_metadata = {
            "mediation_id": mediation.id,
            "mediation_action": mediation.action.value,
            "teacher_id": mediation.teacher_id,
            "recommendation_id": mediation.recommendation_id,
        }
        if mediation.rationale:
            mediation_metadata["rationale"] = mediation.rationale
        if effective_rec is not None:
            mediation_metadata["effective_priority"] = (
                effective_rec.recommended_priority.value
                if effective_rec.recommended_priority
                else None
            )
            mediation_metadata["effective_repetition_count"] = effective_rec.recommended_repetition_count
            mediation_metadata["effective_delay_days"] = effective_rec.recommended_delay_days

        new_metadata = dict(assignment.metadata)
        new_metadata["teacher_scheduling_mediation"] = mediation_metadata

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
    "TEACHER_SCHEDULING_MEDIATION_VERSION",
    "create_teacher_scheduling_mediation",
    "effective_recommendation_from_mediation",
    "effective_scheduling_decision_from_mediation",
    "apply_mediation_to_queue",
]
