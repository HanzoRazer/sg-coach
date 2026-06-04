"""
Tests for Guided Practice Session View Projection Engine.

Sprint 34: Guided Practice Session UX Projection.
"""
from datetime import datetime, timezone

import pytest

from sg_spec.schemas.adaptive_scheduling import (
    AdaptiveSchedulingPlan,
    AdaptiveSchedulingRecommendation,
    SchedulingPriorityAdjustment,
    SchedulingRecommendationReason,
)
from sg_spec.schemas.coach_schemas import DiagnosisCode, Severity
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
from sg_spec.schemas.runtime_flow import (
    RuntimePracticeSession,
    RuntimeSessionStatus,
)
from sg_spec.schemas.session_playback import (
    PlaybackEventType,
    PlaybackFindingOverlay,
    PlaybackTimelineEvent,
    SessionPlaybackData,
)
from sg_spec.schemas.teacher_scheduling_mediation import (
    MediationAction,
    TeacherSchedulingMediation,
    TeacherSchedulingOverride,
)

from sg_coach.guided_practice_view import (
    GUIDED_PRACTICE_VIEW_VERSION,
    INSTRUCTIONS_PREVIEW_MAX_LENGTH,
    build_adaptive_view,
    build_assignment_view,
    build_guided_practice_session_view,
    build_mediation_view,
    build_playback_view,
)


def make_test_assignment(
    assignment_id: str = "pa_test123",
    title: str = "Test Assignment",
    instructions: str | None = None,
    diagnosis_code: str | None = None,
) -> AssembledPracticeAssignment:
    """Create a test assignment."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        title=title,
        assignment_type=PracticeAssignmentType.drill,
        instructions=instructions or "Practice this drill carefully.",
        diagnosis_code=diagnosis_code,
    )


def make_test_queue(
    queue_id: str = "queue_test123",
    student_id: str = "student_001",
    assignments_list: list[AssembledPracticeAssignment] | None = None,
) -> PracticeQueue:
    """Create a test queue."""
    scheduled: list[ScheduledPracticeAssignment] = []
    for i, assignment in enumerate(assignments_list or []):
        scheduled.append(
            ScheduledPracticeAssignment(
                scheduled_id=f"sq_{assignment.id}",
                queue_id=queue_id,
                assignment_id=assignment.id,
                title=assignment.title,
                scheduled_order=i,
                priority=PracticeQueuePriority.normal,
                status=PracticeQueueStatus.queued,
            )
        )
    return PracticeQueue(
        id=queue_id,
        student_id=student_id,
        assignments=scheduled,
    )


def make_test_runtime_session(
    runtime_session_id: str = "rts_test123",
    assignment_id: str = "pa_test123",
    student_id: str = "student_001",
) -> RuntimePracticeSession:
    """Create a test runtime session."""
    return RuntimePracticeSession(
        runtime_session_id=runtime_session_id,
        queue_id="queue_test123",
        scheduled_id="sq_pa_test123",
        assignment_id=assignment_id,
        student_id=student_id,
        status=RuntimeSessionStatus.active,
        started_at=datetime.now(timezone.utc),
        assignment=make_test_assignment(assignment_id=assignment_id),
    )


def make_test_playback(
    session_id: str = "rts_test123",
    event_count: int = 5,
    overlay_count: int = 2,
) -> SessionPlaybackData:
    """Create test playback data."""
    events = [
        PlaybackTimelineEvent(
            timestamp_ms=i * 1000,
            event_type=PlaybackEventType.note,
            label=f"Note event {i}",
        )
        for i in range(event_count)
    ]
    overlays = [
        PlaybackFindingOverlay(
            finding_id=f"finding_{i}",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            severity=Severity.primary if i == 0 else Severity.secondary,
            start_timestamp_ms=i * 500,
            end_timestamp_ms=(i + 1) * 500,
            label=f"Finding overlay {i}",
        )
        for i in range(overlay_count)
    ]
    return SessionPlaybackData(
        session_id=session_id,
        duration_ms=event_count * 1000,
        timeline_events=events,
        finding_overlays=overlays,
    )


def make_test_adaptive_plan(
    student_id: str = "student_001",
    recommendations: list[AdaptiveSchedulingRecommendation] | None = None,
) -> AdaptiveSchedulingPlan:
    """Create a test adaptive scheduling plan."""
    if recommendations is None:
        recommendations = [
            AdaptiveSchedulingRecommendation(
                recommendation_id="asr_001",
                reasons=[SchedulingRecommendationReason.worsening_trend],
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                priority_adjustment=SchedulingPriorityAdjustment.increase,
                recommended_priority=PracticeQueuePriority.high,
                evidence_ids=["ped_001", "ped_002"],
                rationale="Timing errors increasing over last 3 sessions.",
            )
        ]
    return AdaptiveSchedulingPlan(
        student_id=student_id,
        recommendations=recommendations,
        source_evidence_count=len(recommendations),
    )


def make_test_mediation(
    mediation_id: str = "tsm_001",
    action: MediationAction = MediationAction.approve,
    override: TeacherSchedulingOverride | None = None,
) -> TeacherSchedulingMediation:
    """Create a test mediation."""
    effective_override = override
    if action == MediationAction.approve_modified and override is None:
        effective_override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.high,
        )
    return TeacherSchedulingMediation(
        id=mediation_id,
        recommendation_id="asr_001",
        teacher_id="teacher_001",
        action=action,
        override=effective_override,
        rationale="Approved by teacher." if action != MediationAction.approve else None,
        created_at=datetime.now(timezone.utc),
    )


class TestVersion:
    """Test version constant."""

    def test_version_format(self) -> None:
        parts = GUIDED_PRACTICE_VIEW_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestInstructionsPreviewLength:
    """Test instructions preview length constant."""

    def test_is_160(self) -> None:
        assert INSTRUCTIONS_PREVIEW_MAX_LENGTH == 160


class TestBuildAssignmentView:
    """Tests for build_assignment_view()."""

    def test_basic_projection(self) -> None:
        assignment = make_test_assignment()
        view = build_assignment_view(assignment=assignment)
        assert view.assignment_id == "pa_test123"
        assert view.title == "Test Assignment"
        assert view.assignment_type == PracticeAssignmentType.drill

    def test_with_diagnosis_code(self) -> None:
        assignment = make_test_assignment(diagnosis_code="timing_grid_deviation")
        view = build_assignment_view(assignment=assignment)
        assert view.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION

    def test_no_diagnosis_code(self) -> None:
        assignment = make_test_assignment(diagnosis_code=None)
        view = build_assignment_view(assignment=assignment)
        assert view.diagnosis_code is None

    def test_priority_from_queue(self) -> None:
        assignment = make_test_assignment()
        queue = make_test_queue(assignments_list=[assignment])
        queue.assignments[0].priority = PracticeQueuePriority.high
        view = build_assignment_view(assignment=assignment, queue=queue)
        assert view.priority == PracticeQueuePriority.high

    def test_status_from_queue(self) -> None:
        assignment = make_test_assignment()
        queue = make_test_queue(assignments_list=[assignment])
        queue.assignments[0].status = PracticeQueueStatus.active
        view = build_assignment_view(assignment=assignment, queue=queue)
        assert view.status == PracticeQueueStatus.active

    def test_runtime_active_when_matching(self) -> None:
        assignment = make_test_assignment()
        runtime = make_test_runtime_session(assignment_id=assignment.id)
        view = build_assignment_view(assignment=assignment, runtime_session=runtime)
        assert view.runtime_active is True

    def test_runtime_not_active_when_different(self) -> None:
        assignment = make_test_assignment()
        runtime = make_test_runtime_session(assignment_id="different_id")
        view = build_assignment_view(assignment=assignment, runtime_session=runtime)
        assert view.runtime_active is False

    def test_adaptive_flag_from_metadata(self) -> None:
        assignment = make_test_assignment()
        queue = make_test_queue(assignments_list=[assignment])
        queue.assignments[0].metadata["adaptive_scheduling"] = {"recommendation_id": "asr_001"}
        view = build_assignment_view(assignment=assignment, queue=queue)
        assert view.adaptive is True

    def test_teacher_modified_flag(self) -> None:
        assignment = make_test_assignment()
        mediation = make_test_mediation(action=MediationAction.approve_modified)
        view = build_assignment_view(assignment=assignment, mediations=[mediation])
        assert view.teacher_modified is True

    def test_instructions_preview_truncated(self) -> None:
        long_instructions = "X" * 200
        assignment = make_test_assignment(instructions=long_instructions)
        view = build_assignment_view(assignment=assignment)
        assert view.instructions_preview is not None
        assert len(view.instructions_preview) == 160

    def test_instructions_preview_short(self) -> None:
        short_instructions = "Practice slowly."
        assignment = make_test_assignment(instructions=short_instructions)
        view = build_assignment_view(assignment=assignment)
        assert view.instructions_preview == short_instructions

    def test_has_success_criteria(self) -> None:
        assignment = make_test_assignment()
        assignment = AssembledPracticeAssignment(
            id=assignment.id,
            title=assignment.title,
            assignment_type=assignment.assignment_type,
            instructions=assignment.instructions,
            params={"success_criteria": {"target_tempo": 120}},
        )
        view = build_assignment_view(assignment=assignment)
        assert view.has_success_criteria is True

    def test_has_coach_prompts(self) -> None:
        assignment = make_test_assignment()
        assignment = AssembledPracticeAssignment(
            id=assignment.id,
            title=assignment.title,
            assignment_type=assignment.assignment_type,
            instructions=assignment.instructions,
            params={"coach_prompts": [{"message": "Focus on timing"}]},
        )
        view = build_assignment_view(assignment=assignment)
        assert view.has_coach_prompts is True


class TestBuildPlaybackView:
    """Tests for build_playback_view()."""

    def test_no_playback(self) -> None:
        view = build_playback_view(playback=None)
        assert view.playback_available is False
        assert view.timeline_event_count == 0

    def test_with_playback(self) -> None:
        playback = make_test_playback(event_count=10, overlay_count=3)
        view = build_playback_view(playback=playback)
        assert view.playback_available is True
        assert view.timeline_event_count == 10
        assert view.finding_overlay_count == 3

    def test_active_finding_ids(self) -> None:
        playback = make_test_playback(overlay_count=2)
        view = build_playback_view(playback=playback)
        assert "finding_0" in view.active_finding_ids
        assert "finding_1" in view.active_finding_ids

    def test_runtime_session_id_from_playback(self) -> None:
        playback = make_test_playback(session_id="rts_xyz")
        view = build_playback_view(playback=playback)
        assert view.runtime_session_id == "rts_xyz"

    def test_runtime_session_id_from_session_when_no_playback(self) -> None:
        runtime = make_test_runtime_session(runtime_session_id="rts_abc")
        view = build_playback_view(playback=None, runtime_session=runtime)
        assert view.runtime_session_id == "rts_abc"


class TestBuildAdaptiveView:
    """Tests for build_adaptive_view()."""

    def test_no_plan(self) -> None:
        view = build_adaptive_view(adaptive_plan=None)
        assert view.recommendation_count == 0
        assert "No adaptive scheduling guidance is active." in view.notes

    def test_empty_recommendations(self) -> None:
        plan = make_test_adaptive_plan(recommendations=[])
        view = build_adaptive_view(adaptive_plan=plan)
        assert view.recommendation_count == 0

    def test_with_recommendations(self) -> None:
        plan = make_test_adaptive_plan()
        view = build_adaptive_view(adaptive_plan=plan)
        assert view.recommendation_count == 1
        assert "asr_001" in view.active_recommendation_ids

    def test_priority_counts(self) -> None:
        recs = [
            AdaptiveSchedulingRecommendation(
                recommendation_id="asr_001",
                reasons=[SchedulingRecommendationReason.worsening_trend],
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                priority_adjustment=SchedulingPriorityAdjustment.increase,
                recommended_priority=PracticeQueuePriority.high,
                evidence_ids=[],
                rationale="Test",
            ),
            AdaptiveSchedulingRecommendation(
                recommendation_id="asr_002",
                reasons=[SchedulingRecommendationReason.recurring_issue],
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                priority_adjustment=SchedulingPriorityAdjustment.increase,
                recommended_priority=PracticeQueuePriority.critical,
                evidence_ids=[],
                rationale="Test",
            ),
        ]
        plan = make_test_adaptive_plan(recommendations=recs)
        view = build_adaptive_view(adaptive_plan=plan)
        assert view.high_priority_count == 1
        assert view.critical_priority_count == 1

    def test_evidence_ids_collected(self) -> None:
        plan = make_test_adaptive_plan()
        view = build_adaptive_view(adaptive_plan=plan)
        assert "ped_001" in view.evidence_ids
        assert "ped_002" in view.evidence_ids


class TestBuildMediationView:
    """Tests for build_mediation_view()."""

    def test_no_mediations(self) -> None:
        view = build_mediation_view(mediations=[])
        assert view.mediation_count == 0
        assert view.latest_mediation_id is None

    def test_with_mediations(self) -> None:
        mediations = [
            make_test_mediation(mediation_id="tsm_001", action=MediationAction.approve),
            make_test_mediation(mediation_id="tsm_002", action=MediationAction.reject),
        ]
        view = build_mediation_view(mediations=mediations)
        assert view.mediation_count == 2
        assert view.approved_count == 1
        assert view.rejected_count == 1

    def test_action_counts(self) -> None:
        mediations = [
            make_test_mediation(mediation_id="tsm_001", action=MediationAction.approve),
            make_test_mediation(mediation_id="tsm_002", action=MediationAction.approve_modified),
            make_test_mediation(mediation_id="tsm_003", action=MediationAction.reject),
            make_test_mediation(mediation_id="tsm_004", action=MediationAction.defer),
        ]
        view = build_mediation_view(mediations=mediations)
        assert view.approved_count == 1
        assert view.modified_count == 1
        assert view.rejected_count == 1
        assert view.deferred_count == 1

    def test_teacher_override_count(self) -> None:
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediations = [
            make_test_mediation(
                mediation_id="tsm_001",
                action=MediationAction.approve_modified,
                override=override,
            ),
        ]
        view = build_mediation_view(mediations=mediations)
        assert view.teacher_override_count == 1

    def test_notes_for_rejected(self) -> None:
        mediations = [
            make_test_mediation(mediation_id="tsm_001", action=MediationAction.reject),
        ]
        view = build_mediation_view(mediations=mediations)
        assert any("rejected" in note.lower() for note in view.notes)

    def test_notes_for_modified(self) -> None:
        mediations = [
            make_test_mediation(mediation_id="tsm_001", action=MediationAction.approve_modified),
        ]
        view = build_mediation_view(mediations=mediations)
        assert any("modified" in note.lower() for note in view.notes)


class TestBuildGuidedPracticeSessionView:
    """Tests for build_guided_practice_session_view()."""

    def test_minimal_view(self) -> None:
        view = build_guided_practice_session_view()
        assert view.view_id.startswith("gpsv_")
        assert len(view.view_id) == 17  # gpsv_ + 12 hex

    def test_student_id_from_queue(self) -> None:
        queue = make_test_queue(student_id="student_from_queue")
        view = build_guided_practice_session_view(queue=queue)
        assert view.student_id == "student_from_queue"

    def test_student_id_override(self) -> None:
        queue = make_test_queue(student_id="student_from_queue")
        view = build_guided_practice_session_view(queue=queue, student_id="override_id")
        assert view.student_id == "override_id"

    def test_queue_id_populated(self) -> None:
        queue = make_test_queue(queue_id="queue_xyz")
        view = build_guided_practice_session_view(queue=queue)
        assert view.queue_id == "queue_xyz"

    def test_runtime_session_id_populated(self) -> None:
        runtime = make_test_runtime_session(runtime_session_id="rts_xyz")
        view = build_guided_practice_session_view(runtime_session=runtime)
        assert view.runtime_session_id == "rts_xyz"

    def test_with_assignment(self) -> None:
        assignment = make_test_assignment()
        view = build_guided_practice_session_view(assignment=assignment)
        assert view.assignment is not None
        assert view.assignment.assignment_id == "pa_test123"

    def test_with_playback(self) -> None:
        playback = make_test_playback()
        view = build_guided_practice_session_view(playback=playback)
        assert view.playback is not None
        assert view.playback.playback_available is True

    def test_with_adaptive_plan(self) -> None:
        plan = make_test_adaptive_plan()
        view = build_guided_practice_session_view(adaptive_plan=plan)
        assert view.adaptive_guidance is not None
        assert view.adaptive_guidance.recommendation_count == 1

    def test_with_mediations(self) -> None:
        mediations = [make_test_mediation()]
        view = build_guided_practice_session_view(mediations=mediations)
        assert view.teacher_mediation is not None
        assert view.teacher_mediation.mediation_count == 1

    def test_with_timeline(self) -> None:
        timeline = PedagogicalTimelineView(total_events=5)
        view = build_guided_practice_session_view(timeline=timeline)
        assert view.timeline is not None
        assert view.timeline.total_events == 5

    def test_notes_for_no_assignment(self) -> None:
        view = build_guided_practice_session_view()
        assert "No active practice assignment is available." in view.notes

    def test_notes_for_active_session(self) -> None:
        assignment = make_test_assignment()
        runtime = make_test_runtime_session(assignment_id=assignment.id)
        view = build_guided_practice_session_view(
            assignment=assignment,
            runtime_session=runtime,
        )
        assert "Practice session is currently active." in view.notes

    def test_notes_for_mediation_active(self) -> None:
        mediations = [make_test_mediation()]
        view = build_guided_practice_session_view(mediations=mediations)
        assert "Teacher mediation is active for this student." in view.notes

    def test_notes_for_timeline_events(self) -> None:
        timeline = PedagogicalTimelineView(total_events=10)
        view = build_guided_practice_session_view(timeline=timeline)
        assert any("10 events" in note for note in view.notes)


class TestExportsFromInit:
    """Test that functions are exported from sg_coach."""

    def test_version_exported(self) -> None:
        from sg_coach import GUIDED_PRACTICE_VIEW_VERSION
        assert GUIDED_PRACTICE_VIEW_VERSION is not None

    def test_preview_length_exported(self) -> None:
        from sg_coach import INSTRUCTIONS_PREVIEW_MAX_LENGTH
        assert INSTRUCTIONS_PREVIEW_MAX_LENGTH is not None

    def test_build_assignment_view_exported(self) -> None:
        from sg_coach import build_assignment_view
        assert build_assignment_view is not None

    def test_build_playback_view_exported(self) -> None:
        from sg_coach import build_playback_view
        assert build_playback_view is not None

    def test_build_adaptive_view_exported(self) -> None:
        from sg_coach import build_adaptive_view
        assert build_adaptive_view is not None

    def test_build_mediation_view_exported(self) -> None:
        from sg_coach import build_mediation_view
        assert build_mediation_view is not None

    def test_build_guided_practice_session_view_exported(self) -> None:
        from sg_coach import build_guided_practice_session_view
        assert build_guided_practice_session_view is not None
