"""
Tests for Practice Queue Store.

Sprint 23: Assignment scheduling and practice queue management.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from sg_spec.schemas.practice_queue import (
    PracticeQueueEventType,
    PracticeQueuePriority,
    PracticeQueueStatus,
)

from sg_coach.practice_queue_store import (
    PRACTICE_QUEUE_STORE_VERSION,
    PracticeQueueStore,
)


class TestPracticeQueueStoreVersion:
    """Test version constant."""

    def test_version_exists(self) -> None:
        assert PRACTICE_QUEUE_STORE_VERSION == "0.1.0"


class TestPracticeQueueStoreInit:
    """Test store initialization."""

    def test_creates_store(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        assert store.path == tmp_path / "queue.jsonl"


class TestScheduleAssignment:
    """Test schedule_assignment method."""

    def test_creates_event(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="Test Assignment",
        )
        assert event.event_type == PracticeQueueEventType.assignment_scheduled
        assert event.assignment_id == "pa_test_1"

    def test_writes_to_file(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_test_1",
            title="Test Assignment",
        )
        assert store.path.exists()
        content = store.path.read_text()
        assert "pa_test_1" in content

    def test_generates_queue_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="Test",
        )
        assert event.queue_id.startswith("queue_")

    def test_uses_provided_queue_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="Test",
            queue_id="queue_custom123456",
        )
        assert event.queue_id == "queue_custom123456"

    def test_stores_metadata(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="My Title",
            student_id="student_123",
            priority=PracticeQueuePriority.high,
            scheduled_order=5,
            estimated_minutes=15,
            diagnosis_code="timing_grid_deviation",
        )
        assert event.metadata["title"] == "My Title"
        assert event.metadata["student_id"] == "student_123"
        assert event.metadata["priority"] == "high"
        assert event.metadata["scheduled_order"] == 5
        assert event.metadata["estimated_minutes"] == 15

    def test_idempotent_by_assignment_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event1 = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        event2 = store.schedule_assignment(
            assignment_id="pa_test_1",
            title="Second",
            queue_id="queue_abc123456789",
        )
        assert event1.id == event2.id
        events = store.list_events()
        schedule_events = [
            e for e in events
            if e.event_type == PracticeQueueEventType.assignment_scheduled
        ]
        assert len(schedule_events) == 1


class TestMarkStarted:
    """Test mark_started method."""

    def test_creates_event(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.mark_started(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
        )
        assert event.event_type == PracticeQueueEventType.assignment_started
        assert event.assignment_id == "pa_test_1"


class TestMarkCompleted:
    """Test mark_completed method."""

    def test_creates_event(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.mark_completed(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
        )
        assert event.event_type == PracticeQueueEventType.assignment_completed

    def test_stores_completed_at(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event = store.mark_completed(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
            completed_at=custom_time,
        )
        assert "completed_at" in event.metadata


class TestMarkDeferred:
    """Test mark_deferred method."""

    def test_creates_event(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.mark_deferred(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
        )
        assert event.event_type == PracticeQueueEventType.assignment_deferred

    def test_stores_deferred_until(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        defer_time = datetime.now(timezone.utc) + timedelta(hours=1)
        event = store.mark_deferred(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
            deferred_until=defer_time,
        )
        assert event.metadata["deferred_until"] is not None


class TestMarkAbandoned:
    """Test mark_abandoned method."""

    def test_creates_event(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        event = store.mark_abandoned(
            queue_id="queue_abc123456789",
            assignment_id="pa_test_1",
        )
        assert event.event_type == PracticeQueueEventType.assignment_abandoned


class TestListEvents:
    """Test list_events method."""

    def test_returns_empty_for_new_store(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        events = store.list_events()
        assert events == []

    def test_returns_all_events(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(assignment_id="pa_1", title="First")
        store.schedule_assignment(assignment_id="pa_2", title="Second")
        events = store.list_events()
        assert len(events) == 2

    def test_filters_by_queue_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_aaa111222333",
        )
        store.schedule_assignment(
            assignment_id="pa_2",
            title="Second",
            queue_id="queue_bbb444555666",
        )
        events = store.list_events(queue_id="queue_aaa111222333")
        assert len(events) == 1
        assert events[0].assignment_id == "pa_1"

    def test_filters_by_assignment_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(assignment_id="pa_1", title="First")
        store.schedule_assignment(assignment_id="pa_2", title="Second")
        events = store.list_events(assignment_id="pa_1")
        assert len(events) == 1
        assert events[0].assignment_id == "pa_1"

    def test_filters_by_student_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            student_id="student_a",
        )
        store.schedule_assignment(
            assignment_id="pa_2",
            title="Second",
            student_id="student_b",
        )
        events = store.list_events(student_id="student_a")
        assert len(events) == 1
        assert events[0].assignment_id == "pa_1"


class TestLoadQueue:
    """Test load_queue method."""

    def test_returns_empty_queue_for_new_store(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        queue = store.load_queue()
        assert len(queue.assignments) == 0

    def test_rebuilds_from_schedule_events(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.schedule_assignment(
            assignment_id="pa_2",
            title="Second",
            queue_id="queue_abc123456789",
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert len(queue.assignments) == 2
        assert queue.assignments[0].status == PracticeQueueStatus.queued
        assert queue.assignments[1].status == PracticeQueueStatus.queued

    def test_rebuilds_started_status(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.mark_started(
            queue_id="queue_abc123456789",
            assignment_id="pa_1",
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].status == PracticeQueueStatus.active

    def test_rebuilds_completed_status(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.mark_completed(
            queue_id="queue_abc123456789",
            assignment_id="pa_1",
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].status == PracticeQueueStatus.completed
        assert queue.assignments[0].completed_at is not None

    def test_rebuilds_deferred_status(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        defer_time = datetime.now(timezone.utc) + timedelta(hours=1)
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.mark_deferred(
            queue_id="queue_abc123456789",
            assignment_id="pa_1",
            deferred_until=defer_time,
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].status == PracticeQueueStatus.deferred
        assert queue.assignments[0].deferred_until is not None

    def test_rebuilds_abandoned_status(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.mark_abandoned(
            queue_id="queue_abc123456789",
            assignment_id="pa_1",
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].status == PracticeQueueStatus.abandoned

    def test_ignores_duplicate_schedule_events(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
        )
        store.schedule_assignment(
            assignment_id="pa_1",
            title="Duplicate",
            queue_id="queue_abc123456789",
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert len(queue.assignments) == 1
        assert queue.assignments[0].title == "First"

    def test_preserves_priority(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="High Priority",
            queue_id="queue_abc123456789",
            priority=PracticeQueuePriority.high,
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].priority == PracticeQueuePriority.high

    def test_preserves_scheduled_order(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="First",
            queue_id="queue_abc123456789",
            scheduled_order=5,
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].scheduled_order == 5

    def test_preserves_estimated_minutes(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="Timed",
            queue_id="queue_abc123456789",
            estimated_minutes=20,
        )
        queue = store.load_queue(queue_id="queue_abc123456789")
        assert queue.assignments[0].estimated_minutes == 20

    def test_filters_by_student_id(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="Student A",
            student_id="student_a",
        )
        store.schedule_assignment(
            assignment_id="pa_2",
            title="Student B",
            student_id="student_b",
        )
        queue = store.load_queue(student_id="student_a")
        assert len(queue.assignments) == 1
        assert queue.assignments[0].assignment_id == "pa_1"

    def test_sets_queue_id_from_events(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="Test",
            queue_id="queue_abc123456789",
        )
        queue = store.load_queue()
        assert queue.id == "queue_abc123456789"

    def test_sets_student_id_from_events(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")
        store.schedule_assignment(
            assignment_id="pa_1",
            title="Test",
            student_id="student_123",
        )
        queue = store.load_queue()
        assert queue.student_id == "student_123"


class TestEventSequence:
    """Test complex event sequences."""

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")

        store.schedule_assignment(
            assignment_id="pa_1",
            title="Assignment 1",
            queue_id="queue_abc123456789",
        )
        store.schedule_assignment(
            assignment_id="pa_2",
            title="Assignment 2",
            queue_id="queue_abc123456789",
        )
        store.schedule_assignment(
            assignment_id="pa_3",
            title="Assignment 3",
            queue_id="queue_abc123456789",
        )

        store.mark_started(queue_id="queue_abc123456789", assignment_id="pa_1")
        store.mark_completed(queue_id="queue_abc123456789", assignment_id="pa_1")
        store.mark_deferred(queue_id="queue_abc123456789", assignment_id="pa_2")
        store.mark_abandoned(queue_id="queue_abc123456789", assignment_id="pa_3")

        queue = store.load_queue(queue_id="queue_abc123456789")

        assert len(queue.assignments) == 3

        by_id = {a.assignment_id: a for a in queue.assignments}
        assert by_id["pa_1"].status == PracticeQueueStatus.completed
        assert by_id["pa_2"].status == PracticeQueueStatus.deferred
        assert by_id["pa_3"].status == PracticeQueueStatus.abandoned

    def test_multiple_status_changes(self, tmp_path: Path) -> None:
        store = PracticeQueueStore(tmp_path / "queue.jsonl")

        store.schedule_assignment(
            assignment_id="pa_1",
            title="Test",
            queue_id="queue_abc123456789",
        )

        store.mark_started(queue_id="queue_abc123456789", assignment_id="pa_1")
        store.mark_deferred(queue_id="queue_abc123456789", assignment_id="pa_1")
        store.mark_started(queue_id="queue_abc123456789", assignment_id="pa_1")
        store.mark_completed(queue_id="queue_abc123456789", assignment_id="pa_1")

        queue = store.load_queue(queue_id="queue_abc123456789")

        assert queue.assignments[0].status == PracticeQueueStatus.completed
