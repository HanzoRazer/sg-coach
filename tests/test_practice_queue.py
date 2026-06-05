"""
Tests for Practice Queue Engine.

Sprint 23: Assignment scheduling and practice queue management.
"""
from datetime import datetime, timezone, timedelta

import pytest

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueuePriority,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)

from sg_coach.practice_queue import (
    QUEUE_VERSION,
    build_practice_queue,
    queue_priority_for_assignment,
    sort_practice_queue,
    mark_assignment_active,
    mark_assignment_completed,
    mark_assignment_deferred,
    mark_assignment_abandoned,
    next_queue_assignment,
)


def make_assignment(
    assignment_id: str = "pa_test_1",
    title: str = "Test Assignment",
    status: PracticeAssignmentStatus = PracticeAssignmentStatus.ready,
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    params: dict | None = None,
) -> AssembledPracticeAssignment:
    """Helper to create test assignment."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        assignment_type=PracticeAssignmentType.drill,
        status=status,
        title=title,
        instructions="Test instructions",
        diagnosis_code=diagnosis_code,
        params=params or {},
    )


class TestQueueVersion:
    """Test version constant."""

    def test_version_exists(self) -> None:
        assert QUEUE_VERSION == "0.1.0"


class TestQueuePriorityForAssignment:
    """Test queue_priority_for_assignment function."""

    def test_unresolved_is_critical(self) -> None:
        assignment = make_assignment(status=PracticeAssignmentStatus.unresolved)
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.critical

    def test_primary_severity_is_high(self) -> None:
        assignment = make_assignment(params={"severity": "primary"})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.high

    def test_secondary_severity_is_normal(self) -> None:
        assignment = make_assignment(params={"severity": "secondary"})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.normal

    def test_info_severity_is_low(self) -> None:
        assignment = make_assignment(params={"severity": "info"})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.low

    def test_minor_severity_is_low(self) -> None:
        assignment = make_assignment(params={"severity": "minor"})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.low

    def test_no_severity_is_normal(self) -> None:
        assignment = make_assignment(params={})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.normal

    def test_unknown_severity_is_normal(self) -> None:
        assignment = make_assignment(params={"severity": "unknown"})
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.normal

    def test_none_params_is_normal(self) -> None:
        assignment = make_assignment()
        assignment = AssembledPracticeAssignment(
            id="pa_test",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready,
            title="Test",
            instructions="Test",
        )
        assert queue_priority_for_assignment(assignment) == PracticeQueuePriority.normal


class TestBuildPracticeQueue:
    """Test build_practice_queue function."""

    def test_creates_queue(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(assignments=assignments)
        assert queue is not None
        assert isinstance(queue, PracticeQueue)

    def test_generates_queue_id(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(assignments=assignments)
        assert queue.id is not None
        assert queue.id.startswith("queue_")

    def test_uses_provided_queue_id(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(
            assignments=assignments,
            queue_id="queue_custom123456",
        )
        assert queue.id == "queue_custom123456"

    def test_sets_student_id(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(
            assignments=assignments,
            student_id="student_123",
        )
        assert queue.student_id == "student_123"

    def test_creates_scheduled_assignments(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        assert len(queue.assignments) == 2

    def test_scheduled_assignments_have_ids(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(assignments=assignments)
        scheduled = queue.assignments[0]
        assert scheduled.scheduled_id.startswith("sq_")
        assert scheduled.queue_id == queue.id

    def test_preserves_assignment_id(self) -> None:
        assignments = [make_assignment(assignment_id="pa_original")]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].assignment_id == "pa_original"

    def test_preserves_title(self) -> None:
        assignments = [make_assignment(title="My Title")]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].title == "My Title"

    def test_preserves_diagnosis_code(self) -> None:
        assignments = [make_assignment(diagnosis_code=DiagnosisCode.WRONG_NOTE)]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].diagnosis_code == DiagnosisCode.WRONG_NOTE

    def test_scheduled_order_starts_at_zero(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
            make_assignment(assignment_id="pa_3"),
        ]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].scheduled_order == 0
        assert queue.assignments[1].scheduled_order == 1
        assert queue.assignments[2].scheduled_order == 2

    def test_default_status_is_queued(self) -> None:
        assignments = [make_assignment()]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].status == PracticeQueueStatus.queued

    def test_priority_assigned_from_assignment(self) -> None:
        assignments = [make_assignment(params={"severity": "primary"})]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].priority == PracticeQueuePriority.high

    def test_extracts_estimated_minutes(self) -> None:
        assignments = [make_assignment(params={"estimated_minutes": 15})]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].estimated_minutes == 15

    def test_estimated_minutes_none_when_missing(self) -> None:
        assignments = [make_assignment(params={})]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].estimated_minutes is None

    def test_estimated_minutes_none_when_invalid(self) -> None:
        assignments = [make_assignment(params={"estimated_minutes": 0})]
        queue = build_practice_queue(assignments=assignments)
        assert queue.assignments[0].estimated_minutes is None

    def test_empty_assignments_creates_empty_queue(self) -> None:
        queue = build_practice_queue(assignments=[])
        assert len(queue.assignments) == 0


class TestSortPracticeQueue:
    """Test sort_practice_queue function."""

    def test_returns_new_queue(self) -> None:
        queue = PracticeQueue(id="queue_test")
        sorted_queue = sort_practice_queue(queue)
        assert sorted_queue is not queue

    def test_preserves_queue_id(self) -> None:
        queue = PracticeQueue(id="queue_test")
        sorted_queue = sort_practice_queue(queue)
        assert sorted_queue.id == "queue_test"

    def test_preserves_student_id(self) -> None:
        queue = PracticeQueue(id="queue_test", student_id="student_123")
        sorted_queue = sort_practice_queue(queue)
        assert sorted_queue.student_id == "student_123"

    def test_sorts_by_priority(self) -> None:
        assignments = [
            ScheduledPracticeAssignment(
                scheduled_id="sq_1",
                queue_id="queue_test",
                assignment_id="pa_1",
                title="Low",
                scheduled_order=0,
                priority=PracticeQueuePriority.low,
            ),
            ScheduledPracticeAssignment(
                scheduled_id="sq_2",
                queue_id="queue_test",
                assignment_id="pa_2",
                title="Critical",
                scheduled_order=1,
                priority=PracticeQueuePriority.critical,
            ),
            ScheduledPracticeAssignment(
                scheduled_id="sq_3",
                queue_id="queue_test",
                assignment_id="pa_3",
                title="High",
                scheduled_order=2,
                priority=PracticeQueuePriority.high,
            ),
        ]
        queue = PracticeQueue(id="queue_test", assignments=assignments)
        sorted_queue = sort_practice_queue(queue)

        assert sorted_queue.assignments[0].priority == PracticeQueuePriority.critical
        assert sorted_queue.assignments[1].priority == PracticeQueuePriority.high
        assert sorted_queue.assignments[2].priority == PracticeQueuePriority.low

    def test_sorts_by_scheduled_order_within_priority(self) -> None:
        assignments = [
            ScheduledPracticeAssignment(
                scheduled_id="sq_1",
                queue_id="queue_test",
                assignment_id="pa_1",
                title="Second",
                scheduled_order=2,
                priority=PracticeQueuePriority.normal,
            ),
            ScheduledPracticeAssignment(
                scheduled_id="sq_2",
                queue_id="queue_test",
                assignment_id="pa_2",
                title="First",
                scheduled_order=1,
                priority=PracticeQueuePriority.normal,
            ),
        ]
        queue = PracticeQueue(id="queue_test", assignments=assignments)
        sorted_queue = sort_practice_queue(queue)

        assert sorted_queue.assignments[0].scheduled_order == 1
        assert sorted_queue.assignments[1].scheduled_order == 2


class TestMarkAssignmentActive:
    """Test mark_assignment_active function."""

    def test_returns_tuple(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        result = mark_assignment_active(queue, "pa_1")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_updates_status(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_active(queue, "pa_1")
        assert new_queue.assignments[0].status == PracticeQueueStatus.active

    def test_creates_event(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_active(queue, "pa_1")
        assert event.event_type.value == "assignment_started"
        assert event.assignment_id == "pa_1"

    def test_raises_for_unknown_assignment(self) -> None:
        queue = PracticeQueue(id="queue_test")
        with pytest.raises(ValueError, match="not found"):
            mark_assignment_active(queue, "pa_unknown")

    def test_original_queue_unchanged(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        original_status = queue.assignments[0].status
        mark_assignment_active(queue, "pa_1")
        assert queue.assignments[0].status == original_status


class TestMarkAssignmentCompleted:
    """Test mark_assignment_completed function."""

    def test_updates_status(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_completed(queue, "pa_1")
        assert new_queue.assignments[0].status == PracticeQueueStatus.completed

    def test_sets_completed_at(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_completed(queue, "pa_1")
        assert new_queue.assignments[0].completed_at is not None

    def test_uses_provided_completed_at(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        new_queue, event = mark_assignment_completed(
            queue, "pa_1", completed_at=custom_time
        )
        assert new_queue.assignments[0].completed_at == custom_time

    def test_creates_event(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_completed(queue, "pa_1")
        assert event.event_type.value == "assignment_completed"


class TestMarkAssignmentDeferred:
    """Test mark_assignment_deferred function."""

    def test_updates_status(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_deferred(queue, "pa_1")
        assert new_queue.assignments[0].status == PracticeQueueStatus.deferred

    def test_sets_deferred_until(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        defer_time = datetime.now(timezone.utc) + timedelta(hours=1)
        new_queue, event = mark_assignment_deferred(
            queue, "pa_1", deferred_until=defer_time
        )
        assert new_queue.assignments[0].deferred_until == defer_time

    def test_creates_event(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_deferred(queue, "pa_1")
        assert event.event_type.value == "assignment_deferred"


class TestMarkAssignmentAbandoned:
    """Test mark_assignment_abandoned function."""

    def test_updates_status(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_abandoned(queue, "pa_1")
        assert new_queue.assignments[0].status == PracticeQueueStatus.abandoned

    def test_creates_event(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        new_queue, event = mark_assignment_abandoned(queue, "pa_1")
        assert event.event_type.value == "assignment_abandoned"


class TestNextQueueAssignment:
    """Test next_queue_assignment function."""

    def test_returns_first_queued(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_1"

    def test_returns_none_for_empty_queue(self) -> None:
        queue = PracticeQueue(id="queue_test")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is None

    def test_skips_completed(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        queue, _ = mark_assignment_completed(queue, "pa_1")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_2"

    def test_skips_abandoned(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        queue, _ = mark_assignment_abandoned(queue, "pa_1")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_2"

    def test_skips_deferred_with_future_until(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        queue, _ = mark_assignment_deferred(queue, "pa_1", deferred_until=future_time)
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_2"

    def test_includes_deferred_with_past_until(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        queue, _ = mark_assignment_deferred(queue, "pa_1", deferred_until=past_time)
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_1"

    def test_includes_deferred_without_until(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1"),
            make_assignment(assignment_id="pa_2"),
        ]
        queue = build_practice_queue(assignments=assignments)
        queue, _ = mark_assignment_deferred(queue, "pa_1")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_1"

    def test_returns_none_when_all_completed(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        queue, _ = mark_assignment_completed(queue, "pa_1")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is None

    def test_respects_priority(self) -> None:
        assignments = [
            make_assignment(assignment_id="pa_1", params={"severity": "info"}),
            make_assignment(assignment_id="pa_2", params={"severity": "primary"}),
        ]
        queue = build_practice_queue(assignments=assignments)
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_2"

    def test_returns_active_assignment(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        queue, _ = mark_assignment_active(queue, "pa_1")
        next_assignment = next_queue_assignment(queue)
        assert next_assignment is not None
        assert next_assignment.assignment_id == "pa_1"


class TestImmutableUpdates:
    """Test that all updates are immutable."""

    def test_mark_active_preserves_original(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        original_assignments = list(queue.assignments)
        mark_assignment_active(queue, "pa_1")
        assert queue.assignments == original_assignments

    def test_mark_completed_preserves_original(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        original_status = queue.assignments[0].status
        mark_assignment_completed(queue, "pa_1")
        assert queue.assignments[0].status == original_status

    def test_mark_deferred_preserves_original(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        original_status = queue.assignments[0].status
        mark_assignment_deferred(queue, "pa_1")
        assert queue.assignments[0].status == original_status

    def test_mark_abandoned_preserves_original(self) -> None:
        assignments = [make_assignment(assignment_id="pa_1")]
        queue = build_practice_queue(assignments=assignments)
        original_status = queue.assignments[0].status
        mark_assignment_abandoned(queue, "pa_1")
        assert queue.assignments[0].status == original_status

    def test_sort_preserves_original(self) -> None:
        assignments = [
            ScheduledPracticeAssignment(
                scheduled_id="sq_1",
                queue_id="queue_test",
                assignment_id="pa_1",
                title="Low",
                scheduled_order=0,
                priority=PracticeQueuePriority.low,
            ),
            ScheduledPracticeAssignment(
                scheduled_id="sq_2",
                queue_id="queue_test",
                assignment_id="pa_2",
                title="High",
                scheduled_order=1,
                priority=PracticeQueuePriority.high,
            ),
        ]
        queue = PracticeQueue(id="queue_test", assignments=assignments)
        original_order = [a.assignment_id for a in queue.assignments]
        sort_practice_queue(queue)
        assert [a.assignment_id for a in queue.assignments] == original_order
