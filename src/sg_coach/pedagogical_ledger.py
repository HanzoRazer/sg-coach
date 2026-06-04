"""
Pedagogical Evidence Ledger Builder — Canonical audit timeline.

Sprint 29: Pedagogical Evidence Ledger.

Provides:
- ledger_entries_from_runtime_review(): Convert runtime review to ledger entries
- ledger_entries_from_longitudinal_review(): Convert longitudinal review to ledger entries
- ledger_entry_from_queue_event(): Convert queue event to ledger entry
- ledger_entries_from_teacher_review(): Convert teacher review to ledger entries
- ledger_entry_from_assignment_outcome(): Convert assignment outcome to ledger entry
- ledger_entry_from_practice_assignment(): Convert practice assignment to ledger entry
- ledger_entry_from_curriculum_recommendation(): Convert curriculum recommendation to entry
- build_pedagogical_evidence_ledger(): Build complete ledger from sources
- build_pedagogical_evidence_summary(): Build summary from ledger

Core rules:
- Ledger entries are append-only
- Ledger stores evidence, not conclusions
- Evidence provenance must remain inspectable
- Ledger aggregation must remain deterministic
- Historical evidence must never be mutated
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional, Sequence

from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.curriculum_progression import CurriculumRecommendation
from sg_spec.schemas.longitudinal_review import (
    LongitudinalProgressReview,
    LongitudinalTrend,
)
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceLedger,
    PedagogicalEvidenceSource,
    PedagogicalEvidenceSeverity,
    PedagogicalEvidenceSummary,
)
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.practice_queue import PracticeQueueEvent, PracticeQueueEventType
from sg_spec.schemas.runtime_review import RuntimeReviewReport
from sg_spec.schemas.teacher_review import (
    TeacherAnnotationType,
    TeacherReview,
)
from sg_spec.schemas.teacher_scheduling_mediation import (
    MediationAction,
    TeacherSchedulingMediation,
)
from sg_spec.schemas.user_feedback import PracticeOutcome


PEDAGOGICAL_LEDGER_BUILDER_VERSION = "0.1.0"


def _generate_evidence_id() -> str:
    """Generate evidence ID with ped_ prefix."""
    return f"ped_{secrets.token_hex(6)}"


def _severity_from_queue_event(event_type: PracticeQueueEventType) -> PedagogicalEvidenceSeverity:
    """Map queue event type to severity."""
    if event_type == PracticeQueueEventType.assignment_abandoned:
        return PedagogicalEvidenceSeverity.critical
    elif event_type == PracticeQueueEventType.assignment_deferred:
        return PedagogicalEvidenceSeverity.warning
    else:
        return PedagogicalEvidenceSeverity.informational


def _severity_from_outcome(outcome: PracticeOutcome) -> PedagogicalEvidenceSeverity:
    """Map practice outcome to severity."""
    if outcome == PracticeOutcome.abandoned:
        return PedagogicalEvidenceSeverity.critical
    elif outcome in (PracticeOutcome.worsened, PracticeOutcome.repeated):
        return PedagogicalEvidenceSeverity.warning
    else:
        return PedagogicalEvidenceSeverity.informational


def _severity_from_longitudinal_trend(trend: LongitudinalTrend) -> PedagogicalEvidenceSeverity:
    """Map longitudinal trend to severity."""
    if trend == LongitudinalTrend.worsening:
        return PedagogicalEvidenceSeverity.critical
    elif trend == LongitudinalTrend.stable:
        return PedagogicalEvidenceSeverity.warning
    else:
        return PedagogicalEvidenceSeverity.informational


def _severity_from_annotation_type(annotation_type: TeacherAnnotationType) -> PedagogicalEvidenceSeverity:
    """Map teacher annotation type to severity."""
    if annotation_type == TeacherAnnotationType.warning:
        return PedagogicalEvidenceSeverity.warning
    else:
        return PedagogicalEvidenceSeverity.informational


def _severity_from_mediation_action(action: MediationAction) -> PedagogicalEvidenceSeverity:
    """Map mediation action to severity."""
    if action == MediationAction.reject:
        return PedagogicalEvidenceSeverity.critical
    elif action in {MediationAction.approve_modified, MediationAction.defer}:
        return PedagogicalEvidenceSeverity.warning
    else:
        return PedagogicalEvidenceSeverity.informational


def ledger_entries_from_runtime_review(
    report: RuntimeReviewReport,
) -> list[PedagogicalEvidenceEntry]:
    """
    Convert RuntimeReviewReport to ledger entries.

    Creates one entry per diagnosis finding in the evaluation.
    """
    entries: list[PedagogicalEvidenceEntry] = []

    if report.runtime_session.evaluation is None:
        return entries

    for finding in report.runtime_session.evaluation.findings:
        if finding.code is None:
            continue

        provenance = [f"runtime_review:{report.runtime_session_id}"]
        if finding.id:
            provenance.append(f"finding:{finding.id}")

        entry = PedagogicalEvidenceEntry(
            evidence_id=_generate_evidence_id(),
            student_id=report.student_id,
            source=PedagogicalEvidenceSource.runtime_review,
            timestamp=report.generated_at,
            diagnosis_code=finding.code,
            assignment_id=report.assignment_id,
            queue_id=report.queue_id,
            runtime_session_id=report.runtime_session_id,
            severity=PedagogicalEvidenceSeverity.informational,
            title=f"Runtime finding: {finding.code.value}",
            summary=f"{finding.code.value} observed during runtime session {report.runtime_session_id}.",
            metadata={
                "finding_severity": finding.severity.value if finding.severity else None,
                "finding_message": finding.message,
            },
            provenance=provenance,
        )
        entries.append(entry)

    return entries


def ledger_entries_from_longitudinal_review(
    review: LongitudinalProgressReview,
) -> list[PedagogicalEvidenceEntry]:
    """
    Convert LongitudinalProgressReview to ledger entries.

    Creates one entry per diagnosis trend summary, plus one for outcome trajectory.
    """
    entries: list[PedagogicalEvidenceEntry] = []

    base_provenance = []
    for review_id in review.evidence_review_ids:
        base_provenance.append(f"runtime_review:{review_id}")

    for trend in review.diagnosis_trends:
        provenance = list(base_provenance)

        entry = PedagogicalEvidenceEntry(
            evidence_id=_generate_evidence_id(),
            student_id=review.student_id,
            source=PedagogicalEvidenceSource.longitudinal_review,
            timestamp=review.generated_at,
            diagnosis_code=trend.diagnosis_code,
            severity=_severity_from_longitudinal_trend(trend.trend),
            title=f"Longitudinal trend: {trend.diagnosis_code.value}",
            summary=f"{trend.diagnosis_code.value} trend is {trend.trend.value} across reviewed sessions.",
            metadata={
                "trend": trend.trend.value,
                "total_occurrences": trend.total_occurrences,
                "historical_occurrence_count": trend.historical_occurrence_count,
                "recent_occurrence_count": trend.recent_occurrence_count,
                "improvement_ratio": trend.improvement_ratio,
            },
            provenance=provenance,
        )
        entries.append(entry)

    if review.outcome_trajectory is not None:
        trajectory = review.outcome_trajectory
        entry = PedagogicalEvidenceEntry(
            evidence_id=_generate_evidence_id(),
            student_id=review.student_id,
            source=PedagogicalEvidenceSource.longitudinal_review,
            timestamp=review.generated_at,
            severity=PedagogicalEvidenceSeverity.informational,
            title="Outcome trajectory summary",
            summary=f"Outcome trajectory across {review.review_count} sessions.",
            metadata={
                "total_completed": trajectory.total_completed,
                "total_improved": trajectory.total_improved,
                "total_repeated": trajectory.total_repeated,
                "total_worsened": trajectory.total_worsened,
                "total_abandoned": trajectory.total_abandoned,
                "completion_ratio": trajectory.completion_ratio,
                "improvement_ratio": trajectory.improvement_ratio,
            },
            provenance=list(base_provenance),
        )
        entries.append(entry)

    return entries


def ledger_entry_from_queue_event(
    event: PracticeQueueEvent,
) -> PedagogicalEvidenceEntry:
    """Convert PracticeQueueEvent to ledger entry."""
    return PedagogicalEvidenceEntry(
        evidence_id=_generate_evidence_id(),
        source=PedagogicalEvidenceSource.queue_event,
        timestamp=event.timestamp,
        assignment_id=event.assignment_id,
        queue_id=event.queue_id,
        severity=_severity_from_queue_event(event.event_type),
        title=f"Queue event: {event.event_type.value}",
        summary=f"Assignment {event.assignment_id} received queue event {event.event_type.value}.",
        metadata=dict(event.metadata) if event.metadata else {},
        provenance=[f"queue_event:{event.id}"],
    )


def ledger_entries_from_teacher_review(
    review: TeacherReview,
) -> list[PedagogicalEvidenceEntry]:
    """
    Convert TeacherReview to ledger entries.

    Creates one entry per annotation and one per recommendation.
    """
    entries: list[PedagogicalEvidenceEntry] = []

    base_provenance = []
    if review.id:
        base_provenance.append(f"teacher_review:{review.id}")

    for annotation in review.annotations:
        provenance = list(base_provenance)
        if annotation.id:
            provenance.append(f"annotation:{annotation.id}")

        entry = PedagogicalEvidenceEntry(
            evidence_id=_generate_evidence_id(),
            student_id=review.student_id or annotation.student_id,
            source=PedagogicalEvidenceSource.teacher_review,
            timestamp=annotation.timestamp,
            assignment_id=annotation.assignment_id,
            teacher_review_id=review.id,
            severity=_severity_from_annotation_type(annotation.annotation_type),
            title=f"Teacher annotation: {annotation.annotation_type.value}",
            summary=annotation.text[:200] if len(annotation.text) > 200 else annotation.text,
            metadata={
                "annotation_type": annotation.annotation_type.value,
                "teacher_id": annotation.teacher_id or review.teacher_id,
                "finding_id": annotation.finding_id,
                "session_id": annotation.session_id,
            },
            provenance=provenance,
        )
        entries.append(entry)

    for recommendation in review.recommendations:
        provenance = list(base_provenance)
        if recommendation.id:
            provenance.append(f"recommendation:{recommendation.id}")

        entry = PedagogicalEvidenceEntry(
            evidence_id=_generate_evidence_id(),
            student_id=review.student_id or recommendation.student_id,
            source=PedagogicalEvidenceSource.teacher_review,
            timestamp=recommendation.timestamp,
            teacher_review_id=review.id,
            severity=PedagogicalEvidenceSeverity.informational,
            title=f"Teacher recommendation: {recommendation.recommendation_type.value}",
            summary=recommendation.text[:200] if len(recommendation.text) > 200 else recommendation.text,
            metadata={
                "recommendation_type": recommendation.recommendation_type.value,
                "teacher_id": recommendation.teacher_id or review.teacher_id,
            },
            provenance=provenance,
        )
        entries.append(entry)

    return entries


def ledger_entry_from_assignment_outcome(
    event: AssignmentOutcomeEvent,
) -> PedagogicalEvidenceEntry:
    """Convert AssignmentOutcomeEvent to ledger entry."""
    provenance = []
    if event.id:
        provenance.append(f"assignment_outcome:{event.id}")

    return PedagogicalEvidenceEntry(
        evidence_id=_generate_evidence_id(),
        student_id=event.user_id,
        source=PedagogicalEvidenceSource.assignment_outcome,
        timestamp=event.timestamp,
        assignment_id=event.assignment_id,
        severity=_severity_from_outcome(event.outcome),
        title=f"Assignment outcome: {event.outcome.value}",
        summary=f"Assignment {event.assignment_id} recorded outcome {event.outcome.value}.",
        metadata={
            "outcome": event.outcome.value,
            "confidence": event.confidence,
            "comment": event.comment,
            "session_id": event.session_id,
        },
        provenance=provenance,
    )


def ledger_entry_from_practice_assignment(
    assignment: AssembledPracticeAssignment,
    *,
    timestamp: Optional[datetime] = None,
) -> PedagogicalEvidenceEntry:
    """Convert AssembledPracticeAssignment to ledger entry."""
    ts = timestamp or datetime.now(timezone.utc)

    provenance = []
    if assignment.id:
        provenance.append(f"practice_assignment:{assignment.id}")

    diagnosis_label = (
        assignment.diagnosis_code.value
        if assignment.diagnosis_code
        else "unspecified focus"
    )

    return PedagogicalEvidenceEntry(
        evidence_id=_generate_evidence_id(),
        source=PedagogicalEvidenceSource.practice_assignment,
        timestamp=ts,
        diagnosis_code=assignment.diagnosis_code,
        assignment_id=assignment.id,
        severity=PedagogicalEvidenceSeverity.informational,
        title=f"Practice assignment: {assignment.title}",
        summary=f"Assignment {assignment.id or 'unknown'} created for {diagnosis_label}.",
        metadata={
            "assignment_type": assignment.assignment_type.value,
            "status": assignment.status.value,
            "priority": assignment.priority,
            "action_type": assignment.action_type.value if assignment.action_type else None,
        },
        provenance=provenance,
    )


def ledger_entry_from_curriculum_recommendation(
    recommendation: CurriculumRecommendation,
    *,
    timestamp: Optional[datetime] = None,
    student_id: Optional[str] = None,
) -> PedagogicalEvidenceEntry:
    """Convert CurriculumRecommendation to ledger entry."""
    ts = timestamp or datetime.now(timezone.utc)

    provenance_key = f"curriculum_recommendation:{recommendation.diagnosis_code}:{recommendation.content_id}"

    diagnosis_code = None
    try:
        diagnosis_code = DiagnosisCode(recommendation.diagnosis_code)
    except ValueError:
        pass

    return PedagogicalEvidenceEntry(
        evidence_id=_generate_evidence_id(),
        student_id=student_id,
        source=PedagogicalEvidenceSource.curriculum_progression,
        timestamp=ts,
        diagnosis_code=diagnosis_code,
        severity=PedagogicalEvidenceSeverity.informational,
        title=f"Curriculum recommendation: {recommendation.content_id}",
        summary=f"Recommended curriculum content {recommendation.content_id} for {recommendation.diagnosis_code}.",
        metadata={
            "content_id": recommendation.content_id,
            "progression_level": recommendation.progression_level.value,
            "reason": recommendation.reason,
            "prerequisite_satisfied": recommendation.prerequisite_satisfied,
            "recommended_next": recommendation.recommended_next,
        },
        provenance=[provenance_key],
    )


def ledger_entry_from_teacher_scheduling_mediation(
    mediation: TeacherSchedulingMediation,
) -> PedagogicalEvidenceEntry:
    """Convert TeacherSchedulingMediation to ledger entry."""
    provenance = [f"teacher_scheduling_mediation:{mediation.id}"]
    if mediation.recommendation_id:
        provenance.append(f"recommendation:{mediation.recommendation_id}")
    if mediation.prior_mediation_id:
        provenance.append(f"prior_mediation:{mediation.prior_mediation_id}")

    action_summary = {
        MediationAction.approve: "approved",
        MediationAction.approve_modified: "approved with modifications",
        MediationAction.reject: "rejected",
        MediationAction.defer: "deferred",
    }.get(mediation.action, mediation.action.value)

    summary_parts = [
        f"Recommendation {mediation.recommendation_id} {action_summary}",
        f"by teacher {mediation.teacher_id}.",
    ]
    if mediation.rationale:
        summary_parts.append(f"Rationale: {mediation.rationale[:100]}")

    metadata: dict = {
        "action": mediation.action.value,
        "teacher_id": mediation.teacher_id,
        "recommendation_id": mediation.recommendation_id,
    }
    if mediation.override:
        metadata["override"] = {
            "recommended_priority": (
                mediation.override.recommended_priority.value
                if mediation.override.recommended_priority
                else None
            ),
            "recommended_repetition_count": mediation.override.recommended_repetition_count,
            "recommended_delay_days": mediation.override.recommended_delay_days,
        }
    if mediation.prior_mediation_id:
        metadata["prior_mediation_id"] = mediation.prior_mediation_id

    return PedagogicalEvidenceEntry(
        evidence_id=_generate_evidence_id(),
        student_id=mediation.student_id,
        source=PedagogicalEvidenceSource.teacher_scheduling_mediation,
        timestamp=mediation.created_at,
        diagnosis_code=mediation.diagnosis_code,
        assignment_id=mediation.assignment_id,
        teacher_review_id=mediation.teacher_review_id,
        severity=_severity_from_mediation_action(mediation.action),
        title=f"Scheduling mediation: {mediation.action.value}",
        summary=" ".join(summary_parts),
        metadata=metadata,
        provenance=provenance,
    )


def build_pedagogical_evidence_ledger(
    *,
    runtime_reviews: Sequence[RuntimeReviewReport] = (),
    longitudinal_reviews: Sequence[LongitudinalProgressReview] = (),
    queue_events: Sequence[PracticeQueueEvent] = (),
    teacher_reviews: Sequence[TeacherReview] = (),
    assignment_outcomes: Sequence[AssignmentOutcomeEvent] = (),
    practice_assignments: Sequence[AssembledPracticeAssignment] = (),
    curriculum_recommendations: Sequence[CurriculumRecommendation] = (),
    teacher_scheduling_mediations: Sequence[TeacherSchedulingMediation] = (),
    student_id: Optional[str] = None,
) -> PedagogicalEvidenceLedger:
    """
    Build pedagogical evidence ledger from multiple sources.

    Normalizes all evidence into entries, merges into timeline,
    and sorts by timestamp ascending.
    """
    entries: list[PedagogicalEvidenceEntry] = []

    for report in runtime_reviews:
        entries.extend(ledger_entries_from_runtime_review(report))

    for review in longitudinal_reviews:
        entries.extend(ledger_entries_from_longitudinal_review(review))

    for event in queue_events:
        entries.append(ledger_entry_from_queue_event(event))

    for review in teacher_reviews:
        entries.extend(ledger_entries_from_teacher_review(review))

    for event in assignment_outcomes:
        entries.append(ledger_entry_from_assignment_outcome(event))

    for assignment in practice_assignments:
        entries.append(ledger_entry_from_practice_assignment(assignment))

    for recommendation in curriculum_recommendations:
        entries.append(ledger_entry_from_curriculum_recommendation(
            recommendation,
            student_id=student_id,
        ))

    for mediation in teacher_scheduling_mediations:
        entries.append(ledger_entry_from_teacher_scheduling_mediation(mediation))

    entries.sort(key=lambda e: e.timestamp)

    if student_id:
        for entry in entries:
            if entry.student_id is None:
                entry.student_id = student_id

    return PedagogicalEvidenceLedger(
        student_id=student_id,
        entries=entries,
    )


def build_pedagogical_evidence_summary(
    ledger: PedagogicalEvidenceLedger,
) -> PedagogicalEvidenceSummary:
    """Build evidence summary from ledger."""
    counts = {source: 0 for source in PedagogicalEvidenceSource}
    diagnosis_counts: dict[str, int] = {}
    latest_timestamp: Optional[datetime] = None

    for entry in ledger.entries:
        counts[entry.source] += 1

        if entry.diagnosis_code:
            code_value = entry.diagnosis_code.value
            diagnosis_counts[code_value] = diagnosis_counts.get(code_value, 0) + 1

        if latest_timestamp is None or entry.timestamp > latest_timestamp:
            latest_timestamp = entry.timestamp

    return PedagogicalEvidenceSummary(
        total_entries=len(ledger.entries),
        runtime_review_entries=counts[PedagogicalEvidenceSource.runtime_review],
        longitudinal_review_entries=counts[PedagogicalEvidenceSource.longitudinal_review],
        queue_entries=counts[PedagogicalEvidenceSource.queue_event],
        assignment_outcome_entries=counts[PedagogicalEvidenceSource.assignment_outcome],
        curriculum_progression_entries=counts[PedagogicalEvidenceSource.curriculum_progression],
        teacher_review_entries=counts[PedagogicalEvidenceSource.teacher_review],
        practice_assignment_entries=counts[PedagogicalEvidenceSource.practice_assignment],
        teacher_scheduling_mediation_entries=counts[PedagogicalEvidenceSource.teacher_scheduling_mediation],
        diagnosis_counts=diagnosis_counts,
        latest_timestamp=latest_timestamp,
    )


__all__ = [
    "PEDAGOGICAL_LEDGER_BUILDER_VERSION",
    "ledger_entries_from_runtime_review",
    "ledger_entries_from_longitudinal_review",
    "ledger_entry_from_queue_event",
    "ledger_entries_from_teacher_review",
    "ledger_entry_from_assignment_outcome",
    "ledger_entry_from_practice_assignment",
    "ledger_entry_from_curriculum_recommendation",
    "ledger_entry_from_teacher_scheduling_mediation",
    "build_pedagogical_evidence_ledger",
    "build_pedagogical_evidence_summary",
]
