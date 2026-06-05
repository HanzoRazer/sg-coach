"""
Tests for Runtime Flow Engine.

Sprint 25: Queue-to-runtime practice session flow.
Sprint 26: Runtime session evaluation attachment.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
)
from sg_spec.schemas.curriculum_progression import CurriculumProgressState
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueEventType,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.runtime_flow import (
    RuntimeSessionEventType,
    RuntimeSessionStatus,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.runtime_flow import (
    RUNTIME_FLOW_VERSION,
    abandon_runtime_session,
    attach_evaluation,
    attach_runtime_evidence,
    attach_session_record,
    complete_runtime_session,
    runtime_session_has_evidence,
    start_next_queue_assignment,
    start_runtime_session,
)


def make_test_assignment(
    assignment_id: str = "pa_test123",
    diagnosis_code: DiagnosisCode | None = DiagnosisCode.TIMING_GRID_DEVIATION,
    content_id: str | None = "timing_foundation_v1",
) -> AssembledPracticeAssignment:
    """Create a test assignment."""
    params = {}
    if content_id:
        params["curriculum_content_id"] = content_id

    return AssembledPracticeAssignment(
        id=assignment_id,
        title="Test Assignment",
        assignment_type=PracticeAssignmentType.drill,
        instructions="Practice this drill",
        diagnosis_code=diagnosis_code,
        params=params,
    )


def make_test_queue(
    assignment_id: str = "pa_test123",
    scheduled_id: str = "sq_test123",
    status: PracticeQueueStatus = PracticeQueueStatus.queued,
) -> PracticeQueue:
    """Create a test queue with one assignment."""
    return PracticeQueue(
        id="queue_test123",
        student_id="student_123",
        assignments=[
            ScheduledPracticeAssignment(
                scheduled_id=scheduled_id,
                queue_id="queue_test123",
                assignment_id=assignment_id,
                student_id="student_123",
                title="Test Assignment",
                status=status,
                scheduled_order=0,
            )
        ],
    )


class TestVersion:
    """Test version constant."""

    def test_version_exists(self) -> None:
        assert RUNTIME_FLOW_VERSION == "0.2.0"


class TestStartRuntimeSession:
    """Test start_runtime_session function."""

    def test_returns_runtime_session(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session is not None
        assert runtime_session.runtime_session_id.startswith("rts_")
        assert runtime_session.assignment_id == "pa_test123"

    def test_returns_updated_queue(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert updated_queue.assignments[0].status == PracticeQueueStatus.active

    def test_returns_queue_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, _, queue_event, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert queue_event is not None
        assert queue_event.event_type == PracticeQueueEventType.assignment_started

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, _, _, runtime_event = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_event is not None
        assert runtime_event.event_type == RuntimeSessionEventType.session_started

    def test_populates_assignment_field(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session.assignment is not None
        assert runtime_session.assignment.id == "pa_test123"

    def test_sets_active_status(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session.status == RuntimeSessionStatus.active

    def test_sets_started_at(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session.started_at is not None

    def test_raises_if_assignment_not_found(self) -> None:
        queue = make_test_queue()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return None

        with pytest.raises(ValueError, match="assignment_not_found"):
            start_runtime_session(
                queue=queue,
                scheduled_assignment=queue.assignments[0],
                assignment_lookup=lookup,
            )

    def test_raises_if_scheduled_not_in_queue(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        other_scheduled = ScheduledPracticeAssignment(
            scheduled_id="sq_other",
            queue_id="queue_test123",
            assignment_id="pa_test123",
            title="Other",
            scheduled_order=0,
        )

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        with pytest.raises(ValueError, match="scheduled_assignment_not_in_queue"):
            start_runtime_session(
                queue=queue,
                scheduled_assignment=other_scheduled,
                assignment_lookup=lookup,
            )

    def test_preserves_student_id(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session.student_id == "student_123"

    def test_preserves_queue_id(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session.queue_id == "queue_test123"


class TestCompleteRuntimeSession:
    """Test complete_runtime_session function."""

    def test_returns_result(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result is not None
        assert result.processed is True

    def test_creates_outcome_event(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.outcome_event is not None
        assert result.outcome_event.outcome == PracticeOutcome.completed

    def test_includes_integration_result(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.integration_result is not None

    def test_queue_updated_on_completed(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.queue_updated is True

    def test_curriculum_advanced_on_completed(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.curriculum_advanced is True

    def test_queue_not_updated_on_worsened(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.worsened,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.queue_updated is False

    def test_curriculum_not_advanced_on_worsened(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.worsened,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.curriculum_advanced is False

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        _, runtime_event = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert runtime_event is not None
        assert runtime_event.event_type == RuntimeSessionEventType.outcome_processed

    def test_handles_missing_assignment(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        progress = CurriculumProgressState()

        from sg_spec.schemas.runtime_flow import RuntimePracticeSession

        runtime_session = RuntimePracticeSession(
            runtime_session_id="rts_test123",
            queue_id="queue_test123",
            scheduled_id="sq_test123",
            assignment_id="pa_test123",
            status=RuntimeSessionStatus.active,
            assignment=None,
        )

        result, runtime_event = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=queue,
            progress_state=progress,
        )

        assert result.processed is False
        assert "missing_assignment" in result.reasons
        assert result.queue_updated is False
        assert result.curriculum_advanced is False

    def test_access_updated_queue_via_integration_result(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.integration_result is not None
        final_queue = result.integration_result.updated_queue
        assert final_queue.assignments[0].status == PracticeQueueStatus.completed

    def test_access_updated_progress_via_integration_result(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        result, _ = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.integration_result is not None
        final_progress = result.integration_result.updated_progress_state
        assert "timing_foundation_v1" in final_progress.completed_content_ids


class TestAbandonRuntimeSession:
    """Test abandon_runtime_session function."""

    def test_returns_updated_session(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        abandoned_session, _, _, _ = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert abandoned_session.status == RuntimeSessionStatus.abandoned

    def test_sets_completed_at(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        abandoned_session, _, _, _ = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert abandoned_session.completed_at is not None

    def test_returns_updated_queue(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        _, final_queue, _, _ = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert final_queue.assignments[0].status == PracticeQueueStatus.abandoned

    def test_returns_queue_event(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        _, _, queue_event, _ = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert queue_event is not None
        assert queue_event.event_type == PracticeQueueEventType.assignment_abandoned

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        _, _, _, runtime_event = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert runtime_event is not None
        assert runtime_event.event_type == RuntimeSessionEventType.session_abandoned

    def test_preserves_assignment(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        abandoned_session, _, _, _ = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert abandoned_session.assignment is not None
        assert abandoned_session.assignment.id == "pa_test123"


class TestStartNextQueueAssignment:
    """Test start_next_queue_assignment function."""

    def test_starts_next_available(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is not None
        assert runtime_session.assignment_id == "pa_test123"

    def test_returns_none_for_empty_queue(self) -> None:
        queue = PracticeQueue(id="queue_empty", assignments=[])

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return None

        runtime_session, returned_queue, queue_event, runtime_event = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is None
        assert returned_queue == queue
        assert queue_event is None
        assert runtime_event is None

    def test_handles_unresolved_assignment_gracefully(self) -> None:
        queue = make_test_queue()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return None

        runtime_session, returned_queue, queue_event, runtime_event = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is None
        assert queue_event is None
        assert runtime_event is None

    def test_skips_completed_assignments(self) -> None:
        queue = PracticeQueue(
            id="queue_test",
            assignments=[
                ScheduledPracticeAssignment(
                    scheduled_id="sq_1",
                    queue_id="queue_test",
                    assignment_id="pa_completed",
                    title="Completed",
                    status=PracticeQueueStatus.completed,
                    scheduled_order=0,
                ),
                ScheduledPracticeAssignment(
                    scheduled_id="sq_2",
                    queue_id="queue_test",
                    assignment_id="pa_queued",
                    title="Queued",
                    status=PracticeQueueStatus.queued,
                    scheduled_order=1,
                ),
            ],
        )

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            if aid == "pa_queued":
                return make_test_assignment(assignment_id="pa_queued")
            return None

        runtime_session, _, _, _ = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is not None
        assert runtime_session.assignment_id == "pa_queued"

    def test_returns_updated_queue(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, updated_queue, _, _ = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert updated_queue.assignments[0].status == PracticeQueueStatus.active

    def test_returns_queue_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, _, queue_event, _ = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert queue_event is not None
        assert queue_event.event_type == PracticeQueueEventType.assignment_started

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        _, _, _, runtime_event = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_event is not None
        assert runtime_event.event_type == RuntimeSessionEventType.session_started


class TestImmutableUpdates:
    """Test that original objects remain unchanged."""

    def test_original_queue_unchanged_after_start(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()
        original_status = queue.assignments[0].status

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert queue.assignments[0].status == original_status

    def test_original_queue_unchanged_after_abandon(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        original_updated_status = updated_queue.assignments[0].status

        abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert updated_queue.assignments[0].status == original_updated_status

    def test_original_progress_unchanged_after_complete(self) -> None:
        queue = make_test_queue(status=PracticeQueueStatus.active)
        assignment = make_test_assignment()
        progress = CurriculumProgressState()
        original_completed = list(progress.completed_content_ids)

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert progress.completed_content_ids == original_completed


class TestEndToEndFlow:
    """Test complete runtime flow scenarios."""

    def test_full_completion_flow(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()
        progress = CurriculumProgressState()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, start_queue_event, start_runtime_event = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is not None
        assert updated_queue.assignments[0].status == PracticeQueueStatus.active

        result, complete_runtime_event = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=PracticeOutcome.completed,
            queue=updated_queue,
            progress_state=progress,
        )

        assert result.processed is True
        assert result.queue_updated is True
        assert result.curriculum_advanced is True

        final_queue = result.integration_result.updated_queue
        assert final_queue.assignments[0].status == PracticeQueueStatus.completed

        final_progress = result.integration_result.updated_progress_state
        assert "timing_foundation_v1" in final_progress.completed_content_ids

    def test_full_abandonment_flow(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, updated_queue, _, _ = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        assert runtime_session is not None

        abandoned_session, final_queue, abandon_queue_event, abandon_runtime_event = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=updated_queue,
        )

        assert abandoned_session.status == RuntimeSessionStatus.abandoned
        assert final_queue.assignments[0].status == PracticeQueueStatus.abandoned
        assert abandon_queue_event.event_type == PracticeQueueEventType.assignment_abandoned
        assert abandon_runtime_event.event_type == RuntimeSessionEventType.session_abandoned


def make_test_session_record(session_id=None) -> SessionRecord:
    """Create a minimal valid SessionRecord for testing."""
    return SessionRecord(
        session_id=session_id or uuid4(),
        instrument_id="guitar_001",
        engine_version="test@0.1.0",
        program_ref=ProgramRef(type=ProgramType.ztex, name="test_exercise"),
        timing=SessionTiming(bpm=120, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=16,
            notes_played=16,
            notes_dropped=0,
        ),
    )


def make_test_evaluation(session_id) -> CoachEvaluation:
    """Create a minimal valid CoachEvaluation for testing."""
    return CoachEvaluation(
        session_id=session_id,
        coach_version="test@0.1.0",
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Focus on timing accuracy",
        ),
        confidence=0.8,
    )


class TestAttachSessionRecord:
    """Test attach_session_record function (Sprint 26)."""

    def test_returns_updated_session(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()

        updated_session, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        assert updated_session.session_record is not None
        assert updated_session.session_id == str(session_record.session_id)

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()

        _, runtime_event = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        assert runtime_event.event_type == RuntimeSessionEventType.session_record_attached
        assert runtime_event.metadata["session_id"] == str(session_record.session_id)

    def test_preserves_other_fields(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()

        updated_session, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        assert updated_session.runtime_session_id == runtime_session.runtime_session_id
        assert updated_session.assignment_id == runtime_session.assignment_id
        assert updated_session.status == runtime_session.status
        assert updated_session.assignment is not None


class TestAttachEvaluation:
    """Test attach_evaluation function (Sprint 26)."""

    def test_returns_updated_session(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        session_with_record, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        evaluation = make_test_evaluation(session_record.session_id)

        updated_session, _ = attach_evaluation(
            runtime_session=session_with_record,
            evaluation=evaluation,
        )

        assert updated_session.evaluation is not None
        assert updated_session.evaluation_id == str(evaluation.session_id)

    def test_returns_runtime_event(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        session_with_record, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        evaluation = make_test_evaluation(session_record.session_id)

        _, runtime_event = attach_evaluation(
            runtime_session=session_with_record,
            evaluation=evaluation,
        )

        assert runtime_event.event_type == RuntimeSessionEventType.evaluation_attached

    def test_raises_if_session_record_missing(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        evaluation = make_test_evaluation(uuid4())

        with pytest.raises(ValueError, match="session_record_required"):
            attach_evaluation(
                runtime_session=runtime_session,
                evaluation=evaluation,
            )

    def test_raises_if_session_id_mismatch(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        session_with_record, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        different_session_id = uuid4()
        evaluation = make_test_evaluation(different_session_id)

        with pytest.raises(ValueError, match="session_evaluation_mismatch"):
            attach_evaluation(
                runtime_session=session_with_record,
                evaluation=evaluation,
            )


class TestAttachRuntimeEvidence:
    """Test attach_runtime_evidence function (Sprint 26)."""

    def test_attaches_both_evidence(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        evaluation = make_test_evaluation(session_record.session_id)

        result = attach_runtime_evidence(
            runtime_session=runtime_session,
            session_record=session_record,
            evaluation=evaluation,
        )

        assert result.attached is True
        assert result.session_id == str(session_record.session_id)
        assert result.evaluation_id == str(evaluation.session_id)
        assert result.runtime_session.session_record is not None
        assert result.runtime_session.evaluation is not None

    def test_no_reasons_when_matching(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        evaluation = make_test_evaluation(session_record.session_id)

        result = attach_runtime_evidence(
            runtime_session=runtime_session,
            session_record=session_record,
            evaluation=evaluation,
        )

        assert result.reasons == []

    def test_adds_reason_when_session_ids_differ(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        evaluation = make_test_evaluation(uuid4())

        result = attach_runtime_evidence(
            runtime_session=runtime_session,
            session_record=session_record,
            evaluation=evaluation,
        )

        assert "session_evaluation_link_unverified" in result.reasons


class TestRuntimeSessionHasEvidence:
    """Test runtime_session_has_evidence function (Sprint 26)."""

    def test_returns_false_without_evidence(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        assert runtime_session_has_evidence(runtime_session) is False

    def test_returns_false_with_only_session_record(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        session_with_record, _ = attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        assert runtime_session_has_evidence(session_with_record) is False

    def test_returns_true_with_full_evidence(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        session_record = make_test_session_record()
        evaluation = make_test_evaluation(session_record.session_id)

        result = attach_runtime_evidence(
            runtime_session=runtime_session,
            session_record=session_record,
            evaluation=evaluation,
        )

        assert runtime_session_has_evidence(result.runtime_session) is True


class TestEvidenceImmutability:
    """Test that evidence attachment preserves immutability (Sprint 26)."""

    def test_original_session_unchanged_after_attach(self) -> None:
        queue = make_test_queue()
        assignment = make_test_assignment()

        def lookup(aid: str) -> AssembledPracticeAssignment | None:
            return assignment if aid == "pa_test123" else None

        runtime_session, _, _, _ = start_runtime_session(
            queue=queue,
            scheduled_assignment=queue.assignments[0],
            assignment_lookup=lookup,
        )

        original_session_record = runtime_session.session_record

        session_record = make_test_session_record()
        attach_session_record(
            runtime_session=runtime_session,
            session_record=session_record,
        )

        assert runtime_session.session_record == original_session_record
