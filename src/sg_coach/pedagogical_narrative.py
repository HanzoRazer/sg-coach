"""
Pedagogical Narrative Projection Engine.

Sprint 35: Pedagogical Narrative Layer.

Provides:
- build_guided_session_narrative(): Project guided session to narrative
- build_runtime_review_narrative(): Project runtime review to narrative
- build_longitudinal_review_narrative(): Project longitudinal review to narrative

Core rules:
- Narratives are projections only (no canonical evidence creation)
- Narrative generation must remain deterministic
- No AI/LLM narrative synthesis
- Narratives do not mutate findings or evidence
- All text derives from deterministic templates
"""
from __future__ import annotations

import secrets
from typing import Any

from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.longitudinal_review import (
    LongitudinalProgressReview,
    LongitudinalTrend,
)
from sg_spec.schemas.pedagogical_narrative import (
    NarrativeAudience,
    NarrativeSection,
    NarrativeSeverity,
    PedagogicalNarrative,
)
from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
from sg_spec.schemas.runtime_review import RuntimeReviewReport, RuntimeReviewStatus


PEDAGOGICAL_NARRATIVE_ENGINE_VERSION = "0.1.0"


def _generate_narrative_id() -> str:
    """Generate unique narrative ID."""
    return f"pn_{secrets.token_hex(6)}"


def _generate_section_id() -> str:
    """Generate unique section ID."""
    return f"pns_{secrets.token_hex(6)}"


STUDENT_TEMPLATES = {
    "assignment_none": "No active practice assignment is available.",
    "assignment_active": "Practice session is currently active for {title}.",
    "assignment_timing": "Timing-focused practice is active.",
    "assignment_pitch": "Pitch-focused practice is active.",
    "assignment_teacher_modified": "Your teacher modified this practice assignment.",
    "playback_none": "Playback is not available for this session.",
    "playback_available": "Playback is available with {count} highlighted areas.",
    "adaptive_none": "No scheduling suggestions are active.",
    "adaptive_active": "Practice suggestions are active with {count} recommendations.",
    "adaptive_critical": "Important practice suggestions require your attention.",
    "mediation_none": "No teacher feedback is attached to this session.",
    "mediation_modified": "Your teacher adjusted practice guidance.",
    "mediation_rejected": "Your teacher declined a practice suggestion.",
    "mediation_deferred": "Your teacher postponed a practice decision.",
    "timeline_none": "No practice history is available.",
    "timeline_active": "Practice history includes {count} events.",
    "runtime_complete": "Practice session completed successfully.",
    "runtime_partial": "Practice session has partial evidence.",
    "runtime_missing": "Practice session is missing evidence.",
    "longitudinal_improving": "Your progress is improving over time.",
    "longitudinal_stable": "Your progress is steady.",
    "longitudinal_worsening": "Some areas need more attention.",
    "longitudinal_insufficient": "More practice sessions are needed to assess progress.",
}

TEACHER_TEMPLATES = {
    "assignment_none": "No active practice assignment is available.",
    "assignment_active": "Practice session is currently active for {title}.",
    "assignment_timing": "Timing-focused practice is active.",
    "assignment_pitch": "Pitch-focused practice is active.",
    "assignment_teacher_modified": "Teacher mediation modified this practice assignment.",
    "playback_none": "Playback evidence is not available for this session.",
    "playback_available": "Playback evidence is available with {count} finding overlays.",
    "adaptive_none": "No adaptive scheduling guidance is active.",
    "adaptive_active": "Adaptive scheduling guidance is active with {count} recommendations.",
    "adaptive_critical": "Critical adaptive scheduling guidance requires review.",
    "mediation_none": "No teacher mediation is attached to this session.",
    "mediation_modified": "Teacher mediation modified practice guidance.",
    "mediation_rejected": "Teacher rejected at least one adaptive scheduling recommendation.",
    "mediation_deferred": "Teacher deferred at least one adaptive scheduling recommendation.",
    "timeline_none": "No timeline evidence is available.",
    "timeline_active": "Timeline evidence includes {count} pedagogical events.",
    "runtime_complete": "Runtime review status: complete.",
    "runtime_partial": "Runtime review status: partial evidence available.",
    "runtime_missing": "Runtime review status: missing evidence.",
    "longitudinal_improving": "Longitudinal evidence shows improving trend.",
    "longitudinal_stable": "Longitudinal evidence shows stable performance.",
    "longitudinal_worsening": "Longitudinal evidence shows worsening trend requiring intervention.",
    "longitudinal_insufficient": "Insufficient longitudinal data for trend analysis.",
}

MIXED_TEMPLATES = {
    "assignment_none": "No active practice assignment is available.",
    "assignment_active": "Practice session is currently active for {title}.",
    "assignment_timing": "Timing-focused practice is active.",
    "assignment_pitch": "Pitch-focused practice is active.",
    "assignment_teacher_modified": "Teacher mediation modified this practice assignment.",
    "playback_none": "Playback evidence is not available for this session.",
    "playback_available": "Playback evidence is available with {count} finding overlays.",
    "adaptive_none": "No adaptive scheduling guidance is active.",
    "adaptive_active": "Adaptive scheduling guidance is active with {count} recommendations.",
    "adaptive_critical": "Critical adaptive scheduling guidance requires review.",
    "mediation_none": "No teacher mediation is attached to this session.",
    "mediation_modified": "Teacher mediation modified practice guidance.",
    "mediation_rejected": "Teacher rejected at least one adaptive scheduling recommendation.",
    "mediation_deferred": "Teacher deferred at least one adaptive scheduling recommendation.",
    "timeline_none": "No timeline evidence is available.",
    "timeline_active": "Timeline evidence includes {count} pedagogical events.",
    "runtime_complete": "Runtime review completed with full evidence.",
    "runtime_partial": "Runtime review completed with partial evidence.",
    "runtime_missing": "Runtime review is missing required evidence.",
    "longitudinal_improving": "Longitudinal progress shows improvement.",
    "longitudinal_stable": "Longitudinal progress is stable.",
    "longitudinal_worsening": "Longitudinal progress shows areas needing attention.",
    "longitudinal_insufficient": "More sessions are needed for longitudinal analysis.",
}


def _get_templates(audience: NarrativeAudience) -> dict[str, str]:
    """Get template dictionary for audience."""
    if audience == NarrativeAudience.student:
        return STUDENT_TEMPLATES
    elif audience == NarrativeAudience.teacher:
        return TEACHER_TEMPLATES
    return MIXED_TEMPLATES


def _build_assignment_section(
    assignment: GuidedPracticeAssignmentView | None,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build assignment narrative section."""
    evidence_ids: list[str] = []
    related_ids: list[str] = []
    severity = NarrativeSeverity.informational

    if assignment is None:
        summary = templates["assignment_none"]
    else:
        related_ids.append(assignment.assignment_id)

        parts = []
        if assignment.runtime_active:
            parts.append(templates["assignment_active"].format(title=assignment.title))

        if assignment.diagnosis_code:
            code_value = assignment.diagnosis_code.value if hasattr(assignment.diagnosis_code, 'value') else str(assignment.diagnosis_code)
            if "timing" in code_value.lower():
                parts.append(templates["assignment_timing"])
            elif "pitch" in code_value.lower():
                parts.append(templates["assignment_pitch"])

        if assignment.teacher_modified:
            parts.append(templates["assignment_teacher_modified"])
            severity = NarrativeSeverity.warning

        if not parts:
            parts.append(f"Practice assignment: {assignment.title}")

        summary = " ".join(parts)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Assignment",
        summary=summary,
        severity=severity,
        evidence_ids=evidence_ids,
        related_ids=related_ids,
        metadata={"source": "assignment"},
    )


def _build_playback_section(
    playback: GuidedPracticePlaybackView | None,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build playback narrative section."""
    evidence_ids: list[str] = []
    related_ids: list[str] = []
    severity = NarrativeSeverity.informational

    if playback is None or not playback.playback_available:
        summary = templates["playback_none"]
    else:
        summary = templates["playback_available"].format(
            count=playback.finding_overlay_count
        )
        evidence_ids.extend(playback.active_finding_ids or [])
        if playback.runtime_session_id:
            related_ids.append(playback.runtime_session_id)

        if playback.critical_overlay_count > 0:
            severity = NarrativeSeverity.warning

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Playback",
        summary=summary,
        severity=severity,
        evidence_ids=evidence_ids,
        related_ids=related_ids,
        metadata={"source": "playback"},
    )


def _build_adaptive_section(
    adaptive: GuidedPracticeAdaptiveView | None,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build adaptive guidance narrative section."""
    evidence_ids: list[str] = []
    related_ids: list[str] = []
    severity = NarrativeSeverity.informational

    if adaptive is None or adaptive.recommendation_count == 0:
        summary = templates["adaptive_none"]
    else:
        parts = []
        parts.append(templates["adaptive_active"].format(
            count=adaptive.recommendation_count
        ))

        if adaptive.critical_priority_count > 0:
            parts.append(templates["adaptive_critical"])
            severity = NarrativeSeverity.critical
        elif adaptive.high_priority_count > 0:
            severity = NarrativeSeverity.warning

        summary = " ".join(parts)
        evidence_ids.extend(adaptive.evidence_ids or [])
        related_ids.extend(adaptive.active_recommendation_ids or [])

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Adaptive Guidance",
        summary=summary,
        severity=severity,
        evidence_ids=evidence_ids,
        related_ids=related_ids,
        metadata={"source": "adaptive_guidance"},
    )


def _build_mediation_section(
    mediation: GuidedPracticeTeacherMediationView | None,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build teacher mediation narrative section."""
    evidence_ids: list[str] = []
    related_ids: list[str] = []
    severity = NarrativeSeverity.informational

    if mediation is None or mediation.mediation_count == 0:
        summary = templates["mediation_none"]
    else:
        parts = []

        if mediation.modified_count > 0:
            parts.append(templates["mediation_modified"])
            severity = NarrativeSeverity.warning

        if mediation.rejected_count > 0:
            parts.append(templates["mediation_rejected"])
            severity = NarrativeSeverity.warning

        if mediation.deferred_count > 0:
            parts.append(templates["mediation_deferred"])

        if not parts:
            parts.append(f"Teacher mediation is active with {mediation.mediation_count} decisions.")

        summary = " ".join(parts)

        if mediation.latest_mediation_id:
            related_ids.append(mediation.latest_mediation_id)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Teacher Mediation",
        summary=summary,
        severity=severity,
        evidence_ids=evidence_ids,
        related_ids=related_ids,
        metadata={"source": "teacher_mediation"},
    )


def _build_timeline_section(
    timeline: PedagogicalTimelineView | None,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build timeline narrative section."""
    evidence_ids: list[str] = []
    related_ids: list[str] = []
    severity = NarrativeSeverity.informational

    if timeline is None or timeline.total_events == 0:
        summary = templates["timeline_none"]
    else:
        summary = templates["timeline_active"].format(count=timeline.total_events)

        if timeline.timeline_events:
            for event in timeline.timeline_events:
                if hasattr(event, 'evidence_id') and event.evidence_id:
                    evidence_ids.append(event.evidence_id)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Timeline",
        summary=summary,
        severity=severity,
        evidence_ids=evidence_ids,
        related_ids=related_ids,
        metadata={"source": "timeline"},
    )


def _sort_sections_by_severity(sections: list[NarrativeSection]) -> list[NarrativeSection]:
    """Sort sections by severity (critical first, then warning, then informational)."""
    severity_order = {
        NarrativeSeverity.critical: 0,
        NarrativeSeverity.warning: 1,
        NarrativeSeverity.informational: 2,
    }
    return sorted(
        sections,
        key=lambda s: (severity_order.get(s.severity, 3), s.title)
    )


def _generate_guided_session_overview(
    session_view: GuidedPracticeSessionView,
    templates: dict[str, str],
) -> str:
    """Generate overview text for guided session narrative."""
    parts = []

    if session_view.assignment:
        if session_view.assignment.runtime_active:
            parts.append(f"Active practice session for {session_view.assignment.title}.")
        else:
            parts.append(f"Practice session: {session_view.assignment.title}.")
    else:
        parts.append("No active practice assignment.")

    if session_view.adaptive_guidance and session_view.adaptive_guidance.recommendation_count > 0:
        parts.append("Adaptive scheduling guidance is active.")

    if session_view.teacher_mediation and session_view.teacher_mediation.mediation_count > 0:
        parts.append("Teacher mediation has been applied.")

    return " ".join(parts)


def build_guided_session_narrative(
    *,
    session_view: GuidedPracticeSessionView,
    audience: NarrativeAudience = NarrativeAudience.mixed,
) -> PedagogicalNarrative:
    """
    Build narrative projection from guided practice session view.

    Parameters
    ----------
    session_view:
        The guided practice session view to project.
    audience:
        Target audience for narrative wording.

    Returns
    -------
    PedagogicalNarrative with deterministic sections.
    """
    templates = _get_templates(audience)

    if session_view.assignment:
        title = f"Practice Summary: {session_view.assignment.title}"
    else:
        title = "Guided Practice Session Summary"

    overview = _generate_guided_session_overview(session_view, templates)

    sections = [
        _build_assignment_section(session_view.assignment, templates),
        _build_playback_section(session_view.playback, templates),
        _build_adaptive_section(session_view.adaptive_guidance, templates),
        _build_mediation_section(session_view.teacher_mediation, templates),
        _build_timeline_section(session_view.timeline, templates),
    ]

    sections = _sort_sections_by_severity(sections)

    notes: list[str] = []
    if session_view.notes:
        notes = session_view.notes[:5]

    metadata: dict[str, Any] = {
        "source_view_id": session_view.view_id,
    }
    if session_view.student_id:
        metadata["student_id"] = session_view.student_id
    if session_view.queue_id:
        metadata["queue_id"] = session_view.queue_id
    if session_view.runtime_session_id:
        metadata["runtime_session_id"] = session_view.runtime_session_id

    return PedagogicalNarrative(
        narrative_id=_generate_narrative_id(),
        audience=audience,
        title=title,
        overview=overview,
        sections=sections,
        notes=notes,
        metadata=metadata,
    )


def _generate_runtime_review_overview(
    review: RuntimeReviewReport,
    templates: dict[str, str],
) -> str:
    """Generate overview text for runtime review narrative."""
    parts = []

    if review.status == RuntimeReviewStatus.complete:
        parts.append(templates["runtime_complete"])
    elif review.status == RuntimeReviewStatus.partial:
        parts.append(templates["runtime_partial"])
    else:
        parts.append(templates["runtime_missing"])

    if review.evidence_summary.finding_count > 0:
        parts.append(f"{review.evidence_summary.finding_count} findings identified.")

    if review.outcome_summary.outcome:
        parts.append(f"Outcome: {review.outcome_summary.outcome.value}.")

    return " ".join(parts)


def _build_runtime_evidence_section(
    review: RuntimeReviewReport,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build evidence summary section for runtime review."""
    evidence = review.evidence_summary
    severity = NarrativeSeverity.informational

    parts = []
    if evidence.has_session_record:
        parts.append("Session record is available.")
    if evidence.has_evaluation:
        parts.append("Evaluation data is available.")
    if evidence.finding_count > 0:
        parts.append(f"{evidence.finding_count} findings recorded.")
    if evidence.recommendation_count > 0:
        parts.append(f"{evidence.recommendation_count} recommendations generated.")

    if not parts:
        parts.append("No evidence data available.")
        severity = NarrativeSeverity.warning

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Evidence Summary",
        summary=" ".join(parts),
        severity=severity,
        evidence_ids=[],
        related_ids=[review.runtime_session_id],
        metadata={"source": "evidence_summary"},
    )


def _build_runtime_outcome_section(
    review: RuntimeReviewReport,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build outcome section for runtime review."""
    outcome = review.outcome_summary
    severity = NarrativeSeverity.informational
    related_ids: list[str] = []

    parts = []
    if outcome.outcome:
        parts.append(f"Practice outcome: {outcome.outcome.value}.")
    if outcome.queue_updated:
        parts.append("Practice queue has been updated.")
    if outcome.curriculum_advanced:
        parts.append("Curriculum progress has advanced.")
        if outcome.next_curriculum_content_id:
            related_ids.append(outcome.next_curriculum_content_id)

    if outcome.reasons:
        parts.extend(outcome.reasons[:3])

    if not parts:
        parts.append("No outcome data available.")

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Outcome Summary",
        summary=" ".join(parts),
        severity=severity,
        evidence_ids=[],
        related_ids=related_ids,
        metadata={"source": "outcome_summary"},
    )


def build_runtime_review_narrative(
    *,
    review: RuntimeReviewReport,
    audience: NarrativeAudience = NarrativeAudience.mixed,
) -> PedagogicalNarrative:
    """
    Build narrative projection from runtime review report.

    Parameters
    ----------
    review:
        The runtime review report to project.
    audience:
        Target audience for narrative wording.

    Returns
    -------
    PedagogicalNarrative with deterministic sections.
    """
    templates = _get_templates(audience)

    title = "Runtime Practice Review"
    overview = _generate_runtime_review_overview(review, templates)

    sections = [
        _build_runtime_evidence_section(review, templates),
        _build_runtime_outcome_section(review, templates),
    ]

    sections = _sort_sections_by_severity(sections)

    metadata: dict[str, Any] = {
        "runtime_session_id": review.runtime_session_id,
        "review_status": review.status.value,
    }
    if review.student_id:
        metadata["student_id"] = review.student_id
    if review.assignment_id:
        metadata["assignment_id"] = review.assignment_id

    return PedagogicalNarrative(
        narrative_id=_generate_narrative_id(),
        audience=audience,
        title=title,
        overview=overview,
        sections=sections,
        notes=[],
        metadata=metadata,
    )


def _generate_longitudinal_overview(
    review: LongitudinalProgressReview,
    templates: dict[str, str],
) -> str:
    """Generate overview text for longitudinal review narrative."""
    parts = []

    parts.append(f"Review covers {review.review_count} practice sessions.")

    if review.outcome_trajectory:
        trajectory = review.outcome_trajectory
        if trajectory.improvement_ratio is not None:
            pct = int(trajectory.improvement_ratio * 100)
            parts.append(f"Improvement rate: {pct}%.")

    if review.strongest_improvements:
        parts.append(f"Key improvements: {', '.join(review.strongest_improvements[:3])}.")

    if review.recurring_challenges:
        parts.append(f"Recurring challenges: {', '.join(review.recurring_challenges[:3])}.")

    return " ".join(parts)


def _build_diagnosis_trends_section(
    review: LongitudinalProgressReview,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build diagnosis trends section for longitudinal review."""
    severity = NarrativeSeverity.informational

    if not review.diagnosis_trends:
        summary = "No diagnosis trends available."
    else:
        parts = []
        worsening_count = 0
        improving_count = 0

        for trend in review.diagnosis_trends:
            if trend.trend == LongitudinalTrend.worsening:
                worsening_count += 1
            elif trend.trend == LongitudinalTrend.improving:
                improving_count += 1

        if improving_count > 0:
            parts.append(f"{improving_count} diagnoses showing improvement.")
        if worsening_count > 0:
            parts.append(f"{worsening_count} diagnoses showing worsening trends.")
            severity = NarrativeSeverity.warning

        stable_count = len(review.diagnosis_trends) - improving_count - worsening_count
        if stable_count > 0:
            parts.append(f"{stable_count} diagnoses stable.")

        if not parts:
            parts.append(f"Tracking {len(review.diagnosis_trends)} diagnosis trends.")

        summary = " ".join(parts)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Diagnosis Trends",
        summary=summary,
        severity=severity,
        evidence_ids=review.evidence_review_ids[:10] if review.evidence_review_ids else [],
        related_ids=[],
        metadata={"source": "diagnosis_trends"},
    )


def _build_outcome_trajectory_section(
    review: LongitudinalProgressReview,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build outcome trajectory section for longitudinal review."""
    severity = NarrativeSeverity.informational

    trajectory = review.outcome_trajectory
    if not trajectory:
        summary = "No outcome trajectory data available."
    else:
        parts = []

        if trajectory.total_completed > 0:
            parts.append(f"{trajectory.total_completed} sessions completed.")

        if trajectory.total_improved > 0:
            parts.append(f"{trajectory.total_improved} showed improvement.")

        if trajectory.total_worsened > 0:
            parts.append(f"{trajectory.total_worsened} showed decline.")
            severity = NarrativeSeverity.warning

        if trajectory.total_abandoned > 0:
            parts.append(f"{trajectory.total_abandoned} abandoned.")

        if trajectory.completion_ratio is not None:
            pct = int(trajectory.completion_ratio * 100)
            parts.append(f"Completion rate: {pct}%.")

        if not parts:
            parts.append("Outcome trajectory is being tracked.")

        summary = " ".join(parts)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Outcome Trajectory",
        summary=summary,
        severity=severity,
        evidence_ids=[],
        related_ids=[],
        metadata={"source": "outcome_trajectory"},
    )


def _build_improvements_section(
    review: LongitudinalProgressReview,
    templates: dict[str, str],
) -> NarrativeSection:
    """Build improvements and challenges section."""
    severity = NarrativeSeverity.informational

    parts = []

    if review.strongest_improvements:
        parts.append(f"Strongest improvements: {', '.join(review.strongest_improvements[:5])}.")

    if review.recurring_challenges:
        parts.append(f"Recurring challenges: {', '.join(review.recurring_challenges[:5])}.")
        if len(review.recurring_challenges) > 2:
            severity = NarrativeSeverity.warning

    if not parts:
        summary = "No improvement or challenge patterns identified yet."
    else:
        summary = " ".join(parts)

    return NarrativeSection(
        section_id=_generate_section_id(),
        title="Progress Patterns",
        summary=summary,
        severity=severity,
        evidence_ids=[],
        related_ids=[],
        metadata={"source": "progress_patterns"},
    )


def build_longitudinal_review_narrative(
    *,
    review: LongitudinalProgressReview,
    audience: NarrativeAudience = NarrativeAudience.teacher,
) -> PedagogicalNarrative:
    """
    Build narrative projection from longitudinal progress review.

    Parameters
    ----------
    review:
        The longitudinal progress review to project.
    audience:
        Target audience for narrative wording (defaults to teacher).

    Returns
    -------
    PedagogicalNarrative with deterministic sections.
    """
    templates = _get_templates(audience)

    title = "Longitudinal Progress Review"
    overview = _generate_longitudinal_overview(review, templates)

    sections = [
        _build_diagnosis_trends_section(review, templates),
        _build_outcome_trajectory_section(review, templates),
        _build_improvements_section(review, templates),
    ]

    sections = _sort_sections_by_severity(sections)

    notes = review.notes[:5] if review.notes else []

    metadata: dict[str, Any] = {
        "review_count": review.review_count,
    }
    if review.student_id:
        metadata["student_id"] = review.student_id

    return PedagogicalNarrative(
        narrative_id=_generate_narrative_id(),
        audience=audience,
        title=title,
        overview=overview,
        sections=sections,
        notes=notes,
        metadata=metadata,
    )


__all__ = [
    "PEDAGOGICAL_NARRATIVE_ENGINE_VERSION",
    "build_guided_session_narrative",
    "build_runtime_review_narrative",
    "build_longitudinal_review_narrative",
]
