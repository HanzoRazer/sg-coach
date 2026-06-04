"""
Guided Practice Session View Projection Engine.

Sprint 34: Guided Practice Session UX Projection.

Provides:
- build_assignment_view(): Project assignment to UX view
- build_playback_view(): Project playback to UX view
- build_adaptive_view(): Project adaptive plan to UX view
- build_mediation_view(): Project mediations to UX view
- build_guided_practice_session_view(): Build complete UX view

Core rules:
- Projection from canonical objects (no store loading)
- No mutation
- Graceful partial views
- Deterministic notes
"""
from __future__ import annotations

import secrets
from typing import Any, Optional, Sequence

from sg_spec.schemas.adaptive_scheduling import AdaptiveSchedulingPlan
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueuePriority,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.runtime_flow import RuntimePracticeSession
from sg_spec.schemas.session_playback import SessionPlaybackData
from sg_spec.schemas.teacher_scheduling_mediation import (
    MediationAction,
    TeacherSchedulingMediation,
)


GUIDED_PRACTICE_VIEW_VERSION = "0.1.0"

INSTRUCTIONS_PREVIEW_MAX_LENGTH = 160


def _generate_view_id() -> str:
    """Generate unique view ID."""
    return f"gpsv_{secrets.token_hex(6)}"


def _truncate_instructions(instructions: str | None) -> str | None:
    """Truncate instructions to preview length."""
    if not instructions:
        return None
    if len(instructions) <= INSTRUCTIONS_PREVIEW_MAX_LENGTH:
        return instructions
    return instructions[:INSTRUCTIONS_PREVIEW_MAX_LENGTH]


def _find_scheduled_assignment(
    queue: PracticeQueue | None,
    assignment_id: str,
) -> ScheduledPracticeAssignment | None:
    """Find a scheduled assignment in the queue by ID."""
    if queue is None:
        return None
    for scheduled in queue.assignments:
        if scheduled.assignment_id == assignment_id:
            return scheduled
    return None


def _has_adaptive_metadata(scheduled: ScheduledPracticeAssignment | None) -> bool:
    """Check if scheduled assignment has adaptive scheduling metadata."""
    if scheduled is None:
        return False
    return "adaptive_scheduling" in scheduled.metadata


def _has_teacher_modified(
    assignment_id: str,
    mediations: Sequence[TeacherSchedulingMediation],
) -> bool:
    """Check if any mediation modified this assignment."""
    for mediation in mediations:
        if mediation.action == MediationAction.approve_modified:
            if mediation.recommendation_id:
                return True
    return False


def build_assignment_view(
    *,
    assignment: AssembledPracticeAssignment,
    queue: PracticeQueue | None = None,
    runtime_session: RuntimePracticeSession | None = None,
    mediations: Sequence[TeacherSchedulingMediation] = (),
) -> GuidedPracticeAssignmentView:
    """
    Build assignment UX projection.

    Parameters
    ----------
    assignment:
        The assembled practice assignment.
    queue:
        Optional practice queue for status/priority lookup.
    runtime_session:
        Optional runtime session to check if active.
    mediations:
        Sequence of teacher mediations.

    Returns
    -------
    GuidedPracticeAssignmentView projection.
    """
    scheduled = _find_scheduled_assignment(queue, assignment.id)

    priority: PracticeQueuePriority | None = None
    status: PracticeQueueStatus | None = None
    if scheduled is not None:
        priority = scheduled.priority
        status = scheduled.status

    runtime_active = False
    if runtime_session is not None and runtime_session.assignment_id == assignment.id:
        runtime_active = True

    adaptive = _has_adaptive_metadata(scheduled)
    teacher_modified = _has_teacher_modified(assignment.id, mediations)

    instructions_preview = _truncate_instructions(assignment.instructions)

    has_success_criteria = bool(assignment.params.get("success_criteria"))
    has_coach_prompts = bool(assignment.params.get("coach_prompts"))

    diagnosis_code: DiagnosisCode | None = None
    if assignment.diagnosis_code:
        try:
            diagnosis_code = DiagnosisCode(assignment.diagnosis_code)
        except ValueError:
            pass

    return GuidedPracticeAssignmentView(
        assignment_id=assignment.id,
        title=assignment.title,
        assignment_type=assignment.assignment_type,
        diagnosis_code=diagnosis_code,
        priority=priority,
        status=status,
        runtime_active=runtime_active,
        adaptive=adaptive,
        teacher_modified=teacher_modified,
        instructions_preview=instructions_preview,
        has_success_criteria=has_success_criteria,
        has_coach_prompts=has_coach_prompts,
    )


def build_playback_view(
    *,
    playback: SessionPlaybackData | None,
    runtime_session: RuntimePracticeSession | None = None,
) -> GuidedPracticePlaybackView:
    """
    Build playback UX projection.

    Parameters
    ----------
    playback:
        Optional session playback data.
    runtime_session:
        Optional runtime session for ID reference.

    Returns
    -------
    GuidedPracticePlaybackView projection.
    """
    if playback is None:
        return GuidedPracticePlaybackView(
            playback_available=False,
            runtime_session_id=runtime_session.runtime_session_id if runtime_session else None,
        )

    timeline_event_count = len(playback.timeline_events) if playback.timeline_events else 0
    finding_overlay_count = len(playback.finding_overlays) if playback.finding_overlays else 0

    active_finding_ids: list[str] = []
    critical_overlay_count = 0
    if playback.finding_overlays:
        for overlay in playback.finding_overlays:
            if overlay.finding_id:
                active_finding_ids.append(overlay.finding_id)
            if overlay.severity and overlay.severity.value == "primary":
                critical_overlay_count += 1

    return GuidedPracticePlaybackView(
        playback_available=True,
        runtime_session_id=playback.session_id,
        timeline_event_count=timeline_event_count,
        finding_overlay_count=finding_overlay_count,
        active_finding_ids=active_finding_ids,
        critical_overlay_count=critical_overlay_count,
    )


def build_adaptive_view(
    *,
    adaptive_plan: AdaptiveSchedulingPlan | None,
) -> GuidedPracticeAdaptiveView:
    """
    Build adaptive guidance UX projection.

    Parameters
    ----------
    adaptive_plan:
        Optional adaptive scheduling plan.

    Returns
    -------
    GuidedPracticeAdaptiveView projection.
    """
    if adaptive_plan is None or not adaptive_plan.recommendations:
        notes = ["No adaptive scheduling guidance is active."]
        return GuidedPracticeAdaptiveView(notes=notes)

    recommendations = adaptive_plan.recommendations
    recommendation_count = len(recommendations)

    high_priority_count = 0
    critical_priority_count = 0
    active_recommendation_ids: list[str] = []
    evidence_ids_set: set[str] = set()

    for rec in recommendations:
        active_recommendation_ids.append(rec.recommendation_id)
        if rec.recommended_priority == PracticeQueuePriority.high:
            high_priority_count += 1
        elif rec.recommended_priority == PracticeQueuePriority.critical:
            critical_priority_count += 1
        for eid in rec.evidence_ids:
            evidence_ids_set.add(eid)

    notes: list[str] = []
    if critical_priority_count > 0:
        notes.append(f"{critical_priority_count} critical-priority recommendations active.")
    if high_priority_count > 0:
        notes.append(f"{high_priority_count} high-priority recommendations active.")

    return GuidedPracticeAdaptiveView(
        recommendation_count=recommendation_count,
        high_priority_count=high_priority_count,
        critical_priority_count=critical_priority_count,
        active_recommendation_ids=active_recommendation_ids,
        evidence_ids=sorted(evidence_ids_set),
        notes=notes,
    )


def build_mediation_view(
    *,
    mediations: Sequence[TeacherSchedulingMediation],
) -> GuidedPracticeTeacherMediationView:
    """
    Build teacher mediation UX projection.

    Parameters
    ----------
    mediations:
        Sequence of teacher scheduling mediations.

    Returns
    -------
    GuidedPracticeTeacherMediationView projection.
    """
    if not mediations:
        return GuidedPracticeTeacherMediationView()

    mediation_count = len(mediations)
    approved_count = 0
    modified_count = 0
    rejected_count = 0
    deferred_count = 0
    teacher_override_count = 0

    sorted_mediations = sorted(mediations, key=lambda m: m.created_at, reverse=True)
    latest_mediation_id = sorted_mediations[0].id if sorted_mediations else None

    for mediation in mediations:
        if mediation.action == MediationAction.approve:
            approved_count += 1
        elif mediation.action == MediationAction.approve_modified:
            modified_count += 1
        elif mediation.action == MediationAction.reject:
            rejected_count += 1
        elif mediation.action == MediationAction.defer:
            deferred_count += 1

        if mediation.override is not None:
            teacher_override_count += 1

    notes: list[str] = []
    if rejected_count > 0:
        notes.append(f"{rejected_count} recommendations rejected by teacher.")
    if modified_count > 0:
        notes.append(f"{modified_count} recommendations modified by teacher.")

    return GuidedPracticeTeacherMediationView(
        mediation_count=mediation_count,
        latest_mediation_id=latest_mediation_id,
        approved_count=approved_count,
        modified_count=modified_count,
        rejected_count=rejected_count,
        deferred_count=deferred_count,
        teacher_override_count=teacher_override_count,
        notes=notes,
    )


def _generate_session_notes(
    *,
    assignment: GuidedPracticeAssignmentView | None,
    playback: GuidedPracticePlaybackView | None,
    adaptive_guidance: GuidedPracticeAdaptiveView | None,
    teacher_mediation: GuidedPracticeTeacherMediationView | None,
    timeline: PedagogicalTimelineView | None,
) -> list[str]:
    """Generate deterministic notes for the session view."""
    notes: list[str] = []

    if assignment is None:
        notes.append("No active practice assignment is available.")
    else:
        if assignment.runtime_active:
            notes.append("Practice session is currently active.")
        if assignment.teacher_modified:
            notes.append("Assignment has been modified by teacher.")

    if playback is not None and not playback.playback_available:
        notes.append("No playback data is available for this session.")

    if adaptive_guidance is not None and adaptive_guidance.recommendation_count == 0:
        pass  # Already noted in adaptive_guidance.notes

    if teacher_mediation is not None and teacher_mediation.mediation_count > 0:
        notes.append("Teacher mediation is active for this student.")

    if timeline is not None and timeline.total_events > 0:
        notes.append(f"Pedagogical timeline contains {timeline.total_events} events.")

    return notes[:5]


def build_guided_practice_session_view(
    *,
    queue: PracticeQueue | None = None,
    runtime_session: RuntimePracticeSession | None = None,
    assignment: AssembledPracticeAssignment | None = None,
    playback: SessionPlaybackData | None = None,
    adaptive_plan: AdaptiveSchedulingPlan | None = None,
    mediations: Sequence[TeacherSchedulingMediation] = (),
    timeline: PedagogicalTimelineView | None = None,
    student_id: str | None = None,
) -> GuidedPracticeSessionView:
    """
    Build complete guided practice session UX view.

    Parameters
    ----------
    queue:
        Optional practice queue.
    runtime_session:
        Optional active runtime session.
    assignment:
        Optional current assignment.
    playback:
        Optional session playback data.
    adaptive_plan:
        Optional adaptive scheduling plan.
    mediations:
        Sequence of teacher mediations.
    timeline:
        Optional pedagogical timeline view.
    student_id:
        Optional student ID override.

    Returns
    -------
    GuidedPracticeSessionView ready for UX rendering.
    """
    view_id = _generate_view_id()

    resolved_student_id = student_id
    if resolved_student_id is None and queue is not None:
        resolved_student_id = queue.student_id
    if resolved_student_id is None and runtime_session is not None:
        resolved_student_id = runtime_session.student_id
    if resolved_student_id is None and timeline is not None:
        resolved_student_id = timeline.student_id

    queue_id = queue.id if queue else None
    runtime_session_id = runtime_session.runtime_session_id if runtime_session else None

    assignment_view: GuidedPracticeAssignmentView | None = None
    if assignment is not None:
        assignment_view = build_assignment_view(
            assignment=assignment,
            queue=queue,
            runtime_session=runtime_session,
            mediations=mediations,
        )

    playback_view = build_playback_view(
        playback=playback,
        runtime_session=runtime_session,
    )

    adaptive_view = build_adaptive_view(adaptive_plan=adaptive_plan)

    mediation_view = build_mediation_view(mediations=mediations)

    notes = _generate_session_notes(
        assignment=assignment_view,
        playback=playback_view,
        adaptive_guidance=adaptive_view,
        teacher_mediation=mediation_view,
        timeline=timeline,
    )

    return GuidedPracticeSessionView(
        view_id=view_id,
        student_id=resolved_student_id,
        runtime_session_id=runtime_session_id,
        queue_id=queue_id,
        assignment=assignment_view,
        playback=playback_view,
        adaptive_guidance=adaptive_view,
        teacher_mediation=mediation_view,
        timeline=timeline,
        notes=notes,
    )


__all__ = [
    "GUIDED_PRACTICE_VIEW_VERSION",
    "INSTRUCTIONS_PREVIEW_MAX_LENGTH",
    "build_assignment_view",
    "build_playback_view",
    "build_adaptive_view",
    "build_mediation_view",
    "build_guided_practice_session_view",
]
