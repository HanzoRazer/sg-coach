"""
Tests for Pedagogical Narrative Projection Engine.

Sprint 35: Pedagogical Narrative Layer.
"""
from datetime import datetime, timezone

import pytest

from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.longitudinal_review import (
    DiagnosisTrendSummary,
    LongitudinalProgressReview,
    LongitudinalTrend,
    OutcomeTrajectorySummary,
)
from sg_spec.schemas.pedagogical_narrative import (
    NarrativeAudience,
    NarrativeSeverity,
)
from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
from sg_spec.schemas.practice_assignment import PracticeAssignmentType
from sg_spec.schemas.practice_queue import PracticeQueuePriority, PracticeQueueStatus
from sg_spec.schemas.runtime_flow import (
    RuntimePracticeSession,
    RuntimeSessionStatus,
)
from sg_spec.schemas.runtime_review import (
    RuntimeEvidenceSummary,
    RuntimeOutcomeSummary,
    RuntimeReviewReport,
    RuntimeReviewStatus,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.pedagogical_narrative import (
    PEDAGOGICAL_NARRATIVE_ENGINE_VERSION,
    build_guided_session_narrative,
    build_longitudinal_review_narrative,
    build_runtime_review_narrative,
)


def make_test_assignment_view(
    assignment_id: str = "pa_test123",
    title: str = "Test Assignment",
    runtime_active: bool = False,
    teacher_modified: bool = False,
    diagnosis_code: DiagnosisCode | None = None,
) -> GuidedPracticeAssignmentView:
    """Create test assignment view."""
    return GuidedPracticeAssignmentView(
        assignment_id=assignment_id,
        title=title,
        assignment_type=PracticeAssignmentType.drill,
        diagnosis_code=diagnosis_code,
        priority=PracticeQueuePriority.normal,
        status=PracticeQueueStatus.queued,
        runtime_active=runtime_active,
        adaptive=False,
        teacher_modified=teacher_modified,
        instructions_preview="Test instructions",
        has_success_criteria=True,
        has_coach_prompts=True,
    )


def make_test_playback_view(
    playback_available: bool = True,
    finding_overlay_count: int = 3,
    critical_overlay_count: int = 0,
) -> GuidedPracticePlaybackView:
    """Create test playback view."""
    return GuidedPracticePlaybackView(
        playback_available=playback_available,
        runtime_session_id="rts_test123",
        timeline_event_count=10,
        finding_overlay_count=finding_overlay_count,
        active_finding_ids=["finding_1", "finding_2"],
        critical_overlay_count=critical_overlay_count,
    )


def make_test_adaptive_view(
    recommendation_count: int = 2,
    high_priority_count: int = 0,
    critical_priority_count: int = 0,
) -> GuidedPracticeAdaptiveView:
    """Create test adaptive view."""
    return GuidedPracticeAdaptiveView(
        recommendation_count=recommendation_count,
        high_priority_count=high_priority_count,
        critical_priority_count=critical_priority_count,
        active_recommendation_ids=["asr_001", "asr_002"][:recommendation_count],
        evidence_ids=["ped_001", "ped_002"],
        notes=[],
    )


def make_test_mediation_view(
    mediation_count: int = 1,
    modified_count: int = 0,
    rejected_count: int = 0,
    deferred_count: int = 0,
) -> GuidedPracticeTeacherMediationView:
    """Create test mediation view."""
    return GuidedPracticeTeacherMediationView(
        mediation_count=mediation_count,
        latest_mediation_id="tsm_001" if mediation_count > 0 else None,
        approved_count=mediation_count - modified_count - rejected_count - deferred_count,
        modified_count=modified_count,
        rejected_count=rejected_count,
        deferred_count=deferred_count,
        teacher_override_count=modified_count,
        notes=[],
    )


def make_test_timeline_view(
    total_events: int = 5,
) -> PedagogicalTimelineView:
    """Create test timeline view."""
    return PedagogicalTimelineView(
        total_events=total_events,
        timeline_events=[],
        diagnosis_groups=[],
        notes=[],
    )


def make_test_session_view(
    assignment: GuidedPracticeAssignmentView | None = None,
    playback: GuidedPracticePlaybackView | None = None,
    adaptive_guidance: GuidedPracticeAdaptiveView | None = None,
    teacher_mediation: GuidedPracticeTeacherMediationView | None = None,
    timeline: PedagogicalTimelineView | None = None,
) -> GuidedPracticeSessionView:
    """Create test session view."""
    return GuidedPracticeSessionView(
        view_id="gpsv_test123456",
        student_id="student_001",
        runtime_session_id="rts_test123",
        queue_id="queue_test123",
        assignment=assignment,
        playback=playback or GuidedPracticePlaybackView(playback_available=False),
        adaptive_guidance=adaptive_guidance or GuidedPracticeAdaptiveView(),
        teacher_mediation=teacher_mediation or GuidedPracticeTeacherMediationView(),
        timeline=timeline,
        notes=["Test note"],
    )


def make_test_runtime_session() -> RuntimePracticeSession:
    """Create test runtime session."""
    from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment

    assignment = AssembledPracticeAssignment(
        id="pa_test123",
        title="Test Assignment",
        assignment_type=PracticeAssignmentType.drill,
        instructions="Test instructions",
    )
    return RuntimePracticeSession(
        runtime_session_id="rts_test123",
        queue_id="queue_test123",
        scheduled_id="sq_test123",
        assignment_id="pa_test123",
        student_id="student_001",
        status=RuntimeSessionStatus.active,
        started_at=datetime.now(timezone.utc),
        assignment=assignment,
    )


def make_test_runtime_review(
    status: RuntimeReviewStatus = RuntimeReviewStatus.complete,
    finding_count: int = 3,
    outcome: PracticeOutcome | None = PracticeOutcome.improved,
) -> RuntimeReviewReport:
    """Create test runtime review report."""
    evidence = RuntimeEvidenceSummary(
        has_session_record=True,
        has_evaluation=True,
        finding_count=finding_count,
        recommendation_count=2,
    )
    outcome_summary = RuntimeOutcomeSummary(
        outcome=outcome,
        queue_updated=True,
        curriculum_advanced=True,
        next_curriculum_content_id="curr_next",
        reasons=["Improved timing accuracy"],
    )
    return RuntimeReviewReport(
        runtime_session_id="rts_test123",
        status=status,
        student_id="student_001",
        assignment_id="pa_test123",
        diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        runtime_session=make_test_runtime_session(),
        evidence_summary=evidence,
        outcome_summary=outcome_summary,
    )


def make_test_longitudinal_review(
    review_count: int = 10,
    improving_count: int = 2,
    worsening_count: int = 1,
) -> LongitudinalProgressReview:
    """Create test longitudinal progress review."""
    trends = []
    for i in range(improving_count):
        trends.append(DiagnosisTrendSummary(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            total_occurrences=5,
            trend=LongitudinalTrend.improving,
        ))
    for i in range(worsening_count):
        trends.append(DiagnosisTrendSummary(
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            total_occurrences=3,
            trend=LongitudinalTrend.worsening,
        ))

    trajectory = OutcomeTrajectorySummary(
        total_completed=8,
        total_improved=5,
        total_repeated=2,
        total_worsened=1,
        completion_ratio=0.8,
        improvement_ratio=0.625,
    )

    return LongitudinalProgressReview(
        student_id="student_001",
        review_count=review_count,
        diagnosis_trends=trends,
        outcome_trajectory=trajectory,
        strongest_improvements=["Timing accuracy", "Note precision"],
        recurring_challenges=["Pitch consistency"],
        evidence_review_ids=["rrr_001", "rrr_002"],
        notes=["Good progress overall"],
    )


class TestVersion:
    """Test version constant."""

    def test_version_format(self) -> None:
        parts = PEDAGOGICAL_NARRATIVE_ENGINE_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestBuildGuidedSessionNarrative:
    """Tests for build_guided_session_narrative()."""

    def test_minimal_view(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(session_view=session_view)

        assert narrative.narrative_id.startswith("pn_")
        assert len(narrative.narrative_id) == 15  # pn_ + 12 hex
        assert narrative.audience == NarrativeAudience.mixed
        assert narrative.title == "Guided Practice Session Summary"
        assert len(narrative.sections) == 5

    def test_with_assignment(self) -> None:
        assignment = make_test_assignment_view(title="Timing Drill")
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assert narrative.title == "Practice Summary: Timing Drill"
        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert "Timing Drill" in assignment_section.summary or "Practice assignment" in assignment_section.summary

    def test_with_active_runtime(self) -> None:
        assignment = make_test_assignment_view(runtime_active=True, title="Active Drill")
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert "active" in assignment_section.summary.lower()

    def test_with_timing_diagnosis(self) -> None:
        assignment = make_test_assignment_view(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION
        )
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert "timing" in assignment_section.summary.lower()

    def test_with_pitch_diagnosis(self) -> None:
        assignment = make_test_assignment_view(
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION
        )
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert "pitch" in assignment_section.summary.lower()

    def test_with_teacher_modified(self) -> None:
        assignment = make_test_assignment_view(teacher_modified=True)
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert assignment_section.severity == NarrativeSeverity.warning
        assert "modified" in assignment_section.summary.lower()

    def test_playback_available(self) -> None:
        playback = make_test_playback_view(playback_available=True, finding_overlay_count=5)
        session_view = make_test_session_view(playback=playback)
        narrative = build_guided_session_narrative(session_view=session_view)

        playback_section = next(
            s for s in narrative.sections if s.title == "Playback"
        )
        assert "5" in playback_section.summary
        assert playback_section.evidence_ids == ["finding_1", "finding_2"]

    def test_playback_not_available(self) -> None:
        playback = make_test_playback_view(playback_available=False)
        session_view = make_test_session_view(playback=playback)
        narrative = build_guided_session_narrative(session_view=session_view)

        playback_section = next(
            s for s in narrative.sections if s.title == "Playback"
        )
        assert "not available" in playback_section.summary.lower()

    def test_adaptive_active(self) -> None:
        adaptive = make_test_adaptive_view(recommendation_count=3)
        session_view = make_test_session_view(adaptive_guidance=adaptive)
        narrative = build_guided_session_narrative(session_view=session_view)

        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert "3" in adaptive_section.summary
        assert "asr_001" in adaptive_section.related_ids

    def test_adaptive_critical(self) -> None:
        adaptive = make_test_adaptive_view(
            recommendation_count=2,
            critical_priority_count=1,
        )
        session_view = make_test_session_view(adaptive_guidance=adaptive)
        narrative = build_guided_session_narrative(session_view=session_view)

        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert adaptive_section.severity == NarrativeSeverity.critical

    def test_mediation_modified(self) -> None:
        mediation = make_test_mediation_view(mediation_count=1, modified_count=1)
        session_view = make_test_session_view(teacher_mediation=mediation)
        narrative = build_guided_session_narrative(session_view=session_view)

        mediation_section = next(
            s for s in narrative.sections if s.title == "Teacher Mediation"
        )
        assert "modified" in mediation_section.summary.lower()
        assert mediation_section.severity == NarrativeSeverity.warning

    def test_mediation_rejected(self) -> None:
        mediation = make_test_mediation_view(mediation_count=1, rejected_count=1)
        session_view = make_test_session_view(teacher_mediation=mediation)
        narrative = build_guided_session_narrative(session_view=session_view)

        mediation_section = next(
            s for s in narrative.sections if s.title == "Teacher Mediation"
        )
        assert "rejected" in mediation_section.summary.lower()

    def test_timeline_active(self) -> None:
        timeline = make_test_timeline_view(total_events=15)
        session_view = make_test_session_view(timeline=timeline)
        narrative = build_guided_session_narrative(session_view=session_view)

        timeline_section = next(
            s for s in narrative.sections if s.title == "Timeline"
        )
        assert "15" in timeline_section.summary

    def test_audience_student(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.student,
        )
        assert narrative.audience == NarrativeAudience.student

    def test_audience_teacher(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.teacher,
        )
        assert narrative.audience == NarrativeAudience.teacher

    def test_sections_sorted_by_severity(self) -> None:
        assignment = make_test_assignment_view(teacher_modified=True)
        adaptive = make_test_adaptive_view(critical_priority_count=1)
        session_view = make_test_session_view(
            assignment=assignment,
            adaptive_guidance=adaptive,
        )
        narrative = build_guided_session_narrative(session_view=session_view)

        severities = [s.severity for s in narrative.sections]
        assert severities[0] == NarrativeSeverity.critical
        assert NarrativeSeverity.warning in severities

    def test_notes_preserved(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(session_view=session_view)

        assert "Test note" in narrative.notes

    def test_metadata_populated(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(session_view=session_view)

        assert narrative.metadata["source_view_id"] == "gpsv_test123456"
        assert narrative.metadata["student_id"] == "student_001"
        assert narrative.metadata["queue_id"] == "queue_test123"

    def test_section_ids_unique(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(session_view=session_view)

        section_ids = [s.section_id for s in narrative.sections]
        assert len(section_ids) == len(set(section_ids))
        for sid in section_ids:
            assert sid.startswith("pns_")


class TestBuildRuntimeReviewNarrative:
    """Tests for build_runtime_review_narrative()."""

    def test_complete_review(self) -> None:
        review = make_test_runtime_review(status=RuntimeReviewStatus.complete)
        narrative = build_runtime_review_narrative(review=review)

        assert narrative.narrative_id.startswith("pn_")
        assert narrative.title == "Runtime Practice Review"
        assert "complete" in narrative.overview.lower()
        assert len(narrative.sections) == 2

    def test_partial_review(self) -> None:
        review = make_test_runtime_review(status=RuntimeReviewStatus.partial)
        narrative = build_runtime_review_narrative(review=review)

        assert "partial" in narrative.overview.lower()

    def test_missing_evidence_review(self) -> None:
        review = make_test_runtime_review(status=RuntimeReviewStatus.missing_evidence)
        narrative = build_runtime_review_narrative(review=review)

        assert "missing" in narrative.overview.lower()

    def test_evidence_section(self) -> None:
        review = make_test_runtime_review(finding_count=5)
        narrative = build_runtime_review_narrative(review=review)

        evidence_section = next(
            s for s in narrative.sections if s.title == "Evidence Summary"
        )
        assert "5" in evidence_section.summary
        assert "findings" in evidence_section.summary.lower()

    def test_outcome_section(self) -> None:
        review = make_test_runtime_review(outcome=PracticeOutcome.improved)
        narrative = build_runtime_review_narrative(review=review)

        outcome_section = next(
            s for s in narrative.sections if s.title == "Outcome Summary"
        )
        assert "improved" in outcome_section.summary.lower()

    def test_audience_teacher(self) -> None:
        review = make_test_runtime_review()
        narrative = build_runtime_review_narrative(
            review=review,
            audience=NarrativeAudience.teacher,
        )
        assert narrative.audience == NarrativeAudience.teacher

    def test_metadata_populated(self) -> None:
        review = make_test_runtime_review()
        narrative = build_runtime_review_narrative(review=review)

        assert narrative.metadata["runtime_session_id"] == "rts_test123"
        assert narrative.metadata["student_id"] == "student_001"
        assert narrative.metadata["review_status"] == "complete"


class TestBuildLongitudinalReviewNarrative:
    """Tests for build_longitudinal_review_narrative()."""

    def test_basic_review(self) -> None:
        review = make_test_longitudinal_review(review_count=10)
        narrative = build_longitudinal_review_narrative(review=review)

        assert narrative.narrative_id.startswith("pn_")
        assert narrative.title == "Longitudinal Progress Review"
        assert "10" in narrative.overview
        assert len(narrative.sections) == 3

    def test_diagnosis_trends_section(self) -> None:
        review = make_test_longitudinal_review(improving_count=3, worsening_count=2)
        narrative = build_longitudinal_review_narrative(review=review)

        trends_section = next(
            s for s in narrative.sections if s.title == "Diagnosis Trends"
        )
        assert "3" in trends_section.summary  # improving
        assert "2" in trends_section.summary  # worsening
        assert trends_section.severity == NarrativeSeverity.warning

    def test_outcome_trajectory_section(self) -> None:
        review = make_test_longitudinal_review()
        narrative = build_longitudinal_review_narrative(review=review)

        trajectory_section = next(
            s for s in narrative.sections if s.title == "Outcome Trajectory"
        )
        assert "completed" in trajectory_section.summary.lower()
        assert "improvement" in trajectory_section.summary.lower()

    def test_improvements_section(self) -> None:
        review = make_test_longitudinal_review()
        narrative = build_longitudinal_review_narrative(review=review)

        patterns_section = next(
            s for s in narrative.sections if s.title == "Progress Patterns"
        )
        assert "Timing accuracy" in patterns_section.summary
        assert "challenges" in patterns_section.summary.lower()

    def test_audience_defaults_to_teacher(self) -> None:
        review = make_test_longitudinal_review()
        narrative = build_longitudinal_review_narrative(review=review)

        assert narrative.audience == NarrativeAudience.teacher

    def test_notes_preserved(self) -> None:
        review = make_test_longitudinal_review()
        narrative = build_longitudinal_review_narrative(review=review)

        assert "Good progress overall" in narrative.notes

    def test_metadata_populated(self) -> None:
        review = make_test_longitudinal_review(review_count=15)
        narrative = build_longitudinal_review_narrative(review=review)

        assert narrative.metadata["review_count"] == 15
        assert narrative.metadata["student_id"] == "student_001"

    def test_evidence_ids_from_review(self) -> None:
        review = make_test_longitudinal_review()
        narrative = build_longitudinal_review_narrative(review=review)

        trends_section = next(
            s for s in narrative.sections if s.title == "Diagnosis Trends"
        )
        assert "rrr_001" in trends_section.evidence_ids


class TestAudienceWording:
    """Tests for audience-specific wording."""

    def test_student_wording_playback(self) -> None:
        playback = make_test_playback_view(playback_available=True)
        session_view = make_test_session_view(playback=playback)

        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.student,
        )
        playback_section = next(
            s for s in narrative.sections if s.title == "Playback"
        )
        assert "highlighted areas" in playback_section.summary

    def test_teacher_wording_playback(self) -> None:
        playback = make_test_playback_view(playback_available=True)
        session_view = make_test_session_view(playback=playback)

        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.teacher,
        )
        playback_section = next(
            s for s in narrative.sections if s.title == "Playback"
        )
        assert "finding overlays" in playback_section.summary

    def test_student_wording_adaptive(self) -> None:
        adaptive = make_test_adaptive_view(recommendation_count=2)
        session_view = make_test_session_view(adaptive_guidance=adaptive)

        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.student,
        )
        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert "suggestions" in adaptive_section.summary.lower()

    def test_teacher_wording_adaptive(self) -> None:
        adaptive = make_test_adaptive_view(recommendation_count=2)
        session_view = make_test_session_view(adaptive_guidance=adaptive)

        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=NarrativeAudience.teacher,
        )
        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert "adaptive scheduling" in adaptive_section.summary.lower()


class TestSeverityMapping:
    """Tests for severity mapping logic."""

    def test_critical_from_adaptive(self) -> None:
        adaptive = make_test_adaptive_view(critical_priority_count=1)
        session_view = make_test_session_view(adaptive_guidance=adaptive)
        narrative = build_guided_session_narrative(session_view=session_view)

        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert adaptive_section.severity == NarrativeSeverity.critical

    def test_warning_from_high_priority(self) -> None:
        adaptive = make_test_adaptive_view(high_priority_count=2)
        session_view = make_test_session_view(adaptive_guidance=adaptive)
        narrative = build_guided_session_narrative(session_view=session_view)

        adaptive_section = next(
            s for s in narrative.sections if s.title == "Adaptive Guidance"
        )
        assert adaptive_section.severity == NarrativeSeverity.warning

    def test_warning_from_teacher_modified(self) -> None:
        assignment = make_test_assignment_view(teacher_modified=True)
        session_view = make_test_session_view(assignment=assignment)
        narrative = build_guided_session_narrative(session_view=session_view)

        assignment_section = next(
            s for s in narrative.sections if s.title == "Assignment"
        )
        assert assignment_section.severity == NarrativeSeverity.warning

    def test_warning_from_mediation_rejection(self) -> None:
        mediation = make_test_mediation_view(rejected_count=1)
        session_view = make_test_session_view(teacher_mediation=mediation)
        narrative = build_guided_session_narrative(session_view=session_view)

        mediation_section = next(
            s for s in narrative.sections if s.title == "Teacher Mediation"
        )
        assert mediation_section.severity == NarrativeSeverity.warning

    def test_informational_default(self) -> None:
        session_view = make_test_session_view()
        narrative = build_guided_session_narrative(session_view=session_view)

        for section in narrative.sections:
            if section.title == "Timeline":
                assert section.severity == NarrativeSeverity.informational


class TestExportsFromInit:
    """Test that functions are exported from sg_coach."""

    def test_version_exported(self) -> None:
        from sg_coach import PEDAGOGICAL_NARRATIVE_ENGINE_VERSION
        assert PEDAGOGICAL_NARRATIVE_ENGINE_VERSION is not None

    def test_build_guided_session_narrative_exported(self) -> None:
        from sg_coach import build_guided_session_narrative
        assert build_guided_session_narrative is not None

    def test_build_runtime_review_narrative_exported(self) -> None:
        from sg_coach import build_runtime_review_narrative
        assert build_runtime_review_narrative is not None

    def test_build_longitudinal_review_narrative_exported(self) -> None:
        from sg_coach import build_longitudinal_review_narrative
        assert build_longitudinal_review_narrative is not None
