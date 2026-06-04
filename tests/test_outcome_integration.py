"""
Tests for Outcome Integration.

Sprint 24: Session-to-queue outcome integration.
"""
from datetime import datetime, timezone

import pytest

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.curriculum_progression import CurriculumProgressState
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.outcome_integration import (
    OUTCOME_INTEGRATION_VERSION,
    outcome_to_queue_status,
    should_advance_curriculum,
    process_assignment_outcome,
)


def make_assignment(
    assignment_id: str = "pa_test_1",
    title: str = "Test Assignment",
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    params: dict | None = None,
) -> AssembledPracticeAssignment:
    """Helper to create test assignment."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        assignment_type=PracticeAssignmentType.drill,
        status=PracticeAssignmentStatus.ready,
        title=title,
        instructions="Test instructions",
        diagnosis_code=diagnosis_code,
        params=params or {},
    )


def make_outcome_event(
    outcome: PracticeOutcome = PracticeOutcome.completed,
    assignment_id: str = "pa_test_1",
) -> AssignmentOutcomeEvent:
    """Helper to create test outcome event."""
    return AssignmentOutcomeEvent(
        id="aoe_test_123",
        assignment_id=assignment_id,
        outcome=outcome,
    )


def make_queue_with_assignment(
    assignment_id: str = "pa_test_1",
    queue_id: str = "queue_abc123456789",
) -> PracticeQueue:
    """Helper to create queue with a scheduled assignment."""
    scheduled = ScheduledPracticeAssignment(
        scheduled_id="sq_abc123456789",
        queue_id=queue_id,
        assignment_id=assignment_id,
        title="Test Assignment",
        scheduled_order=0,
        status=PracticeQueueStatus.queued,
    )
    return PracticeQueue(
        id=queue_id,
        assignments=[scheduled],
    )


class TestVersion:
    """Test version constant."""

    def test_version_exists(self) -> None:
        assert OUTCOME_INTEGRATION_VERSION == "0.1.0"


class TestOutcomeToQueueStatus:
    """Test outcome_to_queue_status function."""

    def test_completed_maps_to_completed(self) -> None:
        status = outcome_to_queue_status(PracticeOutcome.completed)
        assert status == PracticeQueueStatus.completed

    def test_improved_maps_to_completed(self) -> None:
        status = outcome_to_queue_status(PracticeOutcome.improved)
        assert status == PracticeQueueStatus.completed

    def test_abandoned_maps_to_abandoned(self) -> None:
        status = outcome_to_queue_status(PracticeOutcome.abandoned)
        assert status == PracticeQueueStatus.abandoned

    def test_worsened_maps_to_none(self) -> None:
        status = outcome_to_queue_status(PracticeOutcome.worsened)
        assert status is None

    def test_repeated_maps_to_none(self) -> None:
        status = outcome_to_queue_status(PracticeOutcome.repeated)
        assert status is None


class TestShouldAdvanceCurriculum:
    """Test should_advance_curriculum function."""

    def test_completed_advances(self) -> None:
        assert should_advance_curriculum(PracticeOutcome.completed) is True

    def test_improved_advances(self) -> None:
        assert should_advance_curriculum(PracticeOutcome.improved) is True

    def test_repeated_does_not_advance(self) -> None:
        assert should_advance_curriculum(PracticeOutcome.repeated) is False

    def test_worsened_does_not_advance(self) -> None:
        assert should_advance_curriculum(PracticeOutcome.worsened) is False

    def test_abandoned_does_not_advance(self) -> None:
        assert should_advance_curriculum(PracticeOutcome.abandoned) is False


class TestProcessAssignmentOutcomeBasic:
    """Test basic process_assignment_outcome scenarios."""

    def test_returns_result(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event()
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result is not None
        assert result.processed is True

    def test_includes_assignment_id(self) -> None:
        assignment = make_assignment(assignment_id="pa_custom_123")
        outcome_event = make_outcome_event(assignment_id="pa_custom_123")
        queue = make_queue_with_assignment(assignment_id="pa_custom_123")
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.assignment_id == "pa_custom_123"

    def test_includes_outcome_event_id(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event()
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.outcome_event_id == "aoe_test_123"


class TestProcessAssignmentNotInQueue:
    """Test handling of assignment not in queue."""

    def test_returns_not_processed(self) -> None:
        assignment = make_assignment(assignment_id="pa_missing")
        outcome_event = make_outcome_event(assignment_id="pa_missing")
        queue = make_queue_with_assignment(assignment_id="pa_other")
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.processed is False
        assert "assignment_not_in_queue" in result.reasons

    def test_returns_original_queue(self) -> None:
        assignment = make_assignment(assignment_id="pa_missing")
        outcome_event = make_outcome_event(assignment_id="pa_missing")
        queue = make_queue_with_assignment(assignment_id="pa_other")
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue == queue

    def test_returns_original_progress(self) -> None:
        assignment = make_assignment(assignment_id="pa_missing")
        outcome_event = make_outcome_event(assignment_id="pa_missing")
        queue = make_queue_with_assignment(assignment_id="pa_other")
        progress = CurriculumProgressState(
            completed_content_ids=["existing_content"]
        )

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_progress_state == progress

    def test_no_queue_event(self) -> None:
        assignment = make_assignment(assignment_id="pa_missing")
        outcome_event = make_outcome_event(assignment_id="pa_missing")
        queue = make_queue_with_assignment(assignment_id="pa_other")
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.queue_event is None


class TestProcessCompletedOutcome:
    """Test processing completed outcome."""

    def test_updates_queue_status(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.completed

    def test_creates_queue_event(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.queue_event is not None
        assert result.queue_event.event_type.value == "assignment_completed"

    def test_sets_completed_at(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].completed_at is not None


class TestProcessImprovedOutcome:
    """Test processing improved outcome."""

    def test_updates_queue_to_completed(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.improved)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.completed


class TestProcessAbandonedOutcome:
    """Test processing abandoned outcome."""

    def test_updates_queue_to_abandoned(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.abandoned)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.abandoned

    def test_creates_abandoned_event(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.abandoned)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.queue_event is not None
        assert result.queue_event.event_type.value == "assignment_abandoned"


class TestProcessWorsenedOutcome:
    """Test processing worsened outcome."""

    def test_queue_stays_active(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.worsened)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.queued

    def test_no_queue_event(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.worsened)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.queue_event is None


class TestProcessRepeatedOutcome:
    """Test processing repeated outcome."""

    def test_queue_stays_active(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.repeated)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.queued

    def test_no_queue_event(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.repeated)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.queue_event is None


class TestCurriculumAdvancement:
    """Test curriculum advancement scenarios."""

    def test_advances_on_completed_with_content_id(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is True
        assert "timing_grid_alignment_foundation_v1" in result.updated_progress_state.completed_content_ids

    def test_advances_on_improved_with_content_id(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.improved)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is True

    def test_does_not_advance_on_worsened(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.worsened)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is False
        assert "timing_grid_alignment_foundation_v1" not in result.updated_progress_state.completed_content_ids

    def test_does_not_advance_on_repeated(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.repeated)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is False

    def test_does_not_advance_on_abandoned(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.abandoned)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is False


class TestMissingCurriculumContentId:
    """Test handling of missing curriculum_content_id."""

    def test_adds_reason_missing_content_id(self) -> None:
        assignment = make_assignment(params={})
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert "missing_curriculum_content_id" in result.reasons
        assert result.advanced_curriculum is False

    def test_still_updates_queue(self) -> None:
        assignment = make_assignment(params={})
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.processed is True
        assert result.updated_queue.assignments[0].status == PracticeQueueStatus.completed


class TestMissingDiagnosisCode:
    """Test handling of missing diagnosis_code."""

    def test_adds_reason_missing_diagnosis_code(self) -> None:
        assignment = AssembledPracticeAssignment(
            id="pa_test_1",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready,
            title="Test",
            instructions="Test",
            diagnosis_code=None,
            params={"curriculum_content_id": "timing_foundation_v1"},
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert "missing_diagnosis_code" in result.reasons
        assert result.advanced_curriculum is False


class TestCurriculumRecommendation:
    """Test curriculum recommendation in result."""

    def test_returns_recommendation_when_available(self) -> None:
        assignment = make_assignment(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            params={"curriculum_content_id": "some_other_content_v1"},
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is True

    def test_adds_reason_no_next_step(self) -> None:
        assignment = make_assignment(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"},
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.advanced_curriculum is True
        assert "no_next_curriculum_step" in result.reasons


class TestReasonAccumulation:
    """Test that multiple reasons can accumulate."""

    def test_multiple_reasons(self) -> None:
        assignment = AssembledPracticeAssignment(
            id="pa_test_1",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready,
            title="Test",
            instructions="Test",
            diagnosis_code=None,
            params={},
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState()

        result = process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert result.processed is True
        assert "missing_curriculum_content_id" in result.reasons


class TestImmutableUpdates:
    """Test that original objects are not mutated."""

    def test_original_queue_unchanged(self) -> None:
        assignment = make_assignment()
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        original_status = queue.assignments[0].status
        progress = CurriculumProgressState()

        process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert queue.assignments[0].status == original_status

    def test_original_progress_unchanged(self) -> None:
        assignment = make_assignment(
            params={"curriculum_content_id": "timing_grid_alignment_foundation_v1"}
        )
        outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)
        queue = make_queue_with_assignment()
        progress = CurriculumProgressState(completed_content_ids=[])

        process_assignment_outcome(
            assignment=assignment,
            outcome_event=outcome_event,
            queue=queue,
            progress_state=progress,
        )

        assert progress.completed_content_ids == []
