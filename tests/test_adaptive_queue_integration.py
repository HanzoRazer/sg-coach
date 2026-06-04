"""
Tests for Adaptive Queue Integration.

Sprint 30: Evidence-Driven Adaptive Scheduling.
"""
from datetime import datetime, timezone

import pytest

from sg_spec.schemas.adaptive_scheduling import (
    AdaptiveSchedulingRecommendation,
    SchedulingPriorityAdjustment,
    SchedulingRecommendationReason,
)
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.practice_queue import (
    PracticeQueue,
    PracticeQueuePriority,
    PracticeQueueStatus,
    ScheduledPracticeAssignment,
)

from sg_coach.adaptive_scheduling import apply_adaptive_recommendations_to_queue


def make_assignment(
    scheduled_id: str = "sq_abc123def456",
    queue_id: str = "queue_xyz789",
    assignment_id: str = "pa_test123",
    diagnosis_code: DiagnosisCode | None = None,
    priority: PracticeQueuePriority = PracticeQueuePriority.normal,
    scheduled_order: int = 0,
    metadata: dict | None = None,
) -> ScheduledPracticeAssignment:
    """Create a test scheduled assignment."""
    return ScheduledPracticeAssignment(
        scheduled_id=scheduled_id,
        queue_id=queue_id,
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        title="Test Assignment",
        priority=priority,
        scheduled_order=scheduled_order,
        metadata=metadata or {},
    )


def make_queue(
    assignments: list[ScheduledPracticeAssignment] | None = None,
    queue_id: str = "queue_xyz789",
) -> PracticeQueue:
    """Create a test queue."""
    return PracticeQueue(
        id=queue_id,
        student_id="student_123",
        assignments=assignments or [],
    )


def make_recommendation(
    recommendation_id: str = "asr_abc123def456",
    assignment_id: str | None = None,
    diagnosis_code: DiagnosisCode | None = None,
    priority_adjustment: SchedulingPriorityAdjustment = SchedulingPriorityAdjustment.increase,
    recommended_priority: PracticeQueuePriority | None = PracticeQueuePriority.high,
    recommended_repetition_count: int | None = 2,
    recommended_delay_days: int | None = None,
    evidence_ids: list[str] | None = None,
) -> AdaptiveSchedulingRecommendation:
    """Create a test recommendation."""
    return AdaptiveSchedulingRecommendation(
        recommendation_id=recommendation_id,
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        priority_adjustment=priority_adjustment,
        recommended_priority=recommended_priority,
        recommended_repetition_count=recommended_repetition_count,
        recommended_delay_days=recommended_delay_days,
        reasons=[SchedulingRecommendationReason.worsening_trend],
        evidence_ids=evidence_ids or ["ped_001"],
        rationale="Test rationale",
    )


class TestQueueUpdatedImmutably:
    """Test queue is updated immutably."""

    def test_returns_new_queue_object(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(assignment_id="pa_001")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated is not queue

    def test_original_queue_unchanged(self) -> None:
        assignment = make_assignment(
            assignment_id="pa_001",
            priority=PracticeQueuePriority.normal,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            recommended_priority=PracticeQueuePriority.high,
        )

        apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert queue.assignments[0].priority == PracticeQueuePriority.normal

    def test_original_assignment_unchanged(self) -> None:
        assignment = make_assignment(
            assignment_id="pa_001",
            metadata={"original": True},
        )
        queue = make_queue([assignment])
        rec = make_recommendation(assignment_id="pa_001")

        apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert "adaptive_scheduling" not in assignment.metadata


class TestPriorityMetadataUpdated:
    """Test priority and metadata are updated."""

    def test_priority_updated_from_recommendation(self) -> None:
        assignment = make_assignment(
            assignment_id="pa_001",
            priority=PracticeQueuePriority.normal,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            recommended_priority=PracticeQueuePriority.high,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.high

    def test_adaptive_metadata_added(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(
            recommendation_id="asr_unique123",
            assignment_id="pa_001",
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert "adaptive_scheduling" in updated.assignments[0].metadata
        meta = updated.assignments[0].metadata["adaptive_scheduling"]
        assert meta["recommendation_id"] == "asr_unique123"

    def test_metadata_includes_priority_adjustment(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            priority_adjustment=SchedulingPriorityAdjustment.increase,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        meta = updated.assignments[0].metadata["adaptive_scheduling"]
        assert meta["priority_adjustment"] == "increase"

    def test_metadata_includes_repetition_count(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            recommended_repetition_count=3,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        meta = updated.assignments[0].metadata["adaptive_scheduling"]
        assert meta["recommended_repetition_count"] == 3

    def test_metadata_includes_delay_days(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            recommended_delay_days=5,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        meta = updated.assignments[0].metadata["adaptive_scheduling"]
        assert meta["recommended_delay_days"] == 5

    def test_metadata_includes_evidence_ids(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            evidence_ids=["ped_001", "ped_002"],
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        meta = updated.assignments[0].metadata["adaptive_scheduling"]
        assert meta["evidence_ids"] == ["ped_001", "ped_002"]


class TestQueueOrderingPreserved:
    """Test queue ordering is preserved."""

    def test_scheduled_order_unchanged(self) -> None:
        assignments = [
            make_assignment(
                scheduled_id="sq_001",
                assignment_id="pa_001",
                scheduled_order=0,
            ),
            make_assignment(
                scheduled_id="sq_002",
                assignment_id="pa_002",
                scheduled_order=1,
            ),
            make_assignment(
                scheduled_id="sq_003",
                assignment_id="pa_003",
                scheduled_order=2,
            ),
        ]
        queue = make_queue(assignments)
        rec = make_recommendation(assignment_id="pa_002")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].scheduled_order == 0
        assert updated.assignments[1].scheduled_order == 1
        assert updated.assignments[2].scheduled_order == 2

    def test_assignment_list_order_preserved(self) -> None:
        assignments = [
            make_assignment(scheduled_id="sq_001", assignment_id="pa_001"),
            make_assignment(scheduled_id="sq_002", assignment_id="pa_002"),
            make_assignment(scheduled_id="sq_003", assignment_id="pa_003"),
        ]
        queue = make_queue(assignments)
        rec = make_recommendation(assignment_id="pa_003")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].assignment_id == "pa_001"
        assert updated.assignments[1].assignment_id == "pa_002"
        assert updated.assignments[2].assignment_id == "pa_003"


class TestNonMatchingAssignmentsIgnored:
    """Test non-matching assignments are ignored."""

    def test_non_matching_assignment_unchanged(self) -> None:
        assignments = [
            make_assignment(
                assignment_id="pa_001",
                priority=PracticeQueuePriority.normal,
            ),
            make_assignment(
                assignment_id="pa_002",
                priority=PracticeQueuePriority.low,
            ),
        ]
        queue = make_queue(assignments)
        rec = make_recommendation(assignment_id="pa_001")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[1].priority == PracticeQueuePriority.low
        assert "adaptive_scheduling" not in updated.assignments[1].metadata

    def test_matching_by_diagnosis_code(self) -> None:
        assignments = [
            make_assignment(
                assignment_id="pa_001",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                priority=PracticeQueuePriority.normal,
            ),
            make_assignment(
                assignment_id="pa_002",
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                priority=PracticeQueuePriority.normal,
            ),
        ]
        queue = make_queue(assignments)
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommended_priority=PracticeQueuePriority.high,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.high
        assert updated.assignments[1].priority == PracticeQueuePriority.normal

    def test_assignment_id_takes_priority_over_diagnosis(self) -> None:
        assignments = [
            make_assignment(
                assignment_id="pa_001",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
        ]
        queue = make_queue(assignments)
        rec_by_assignment = make_recommendation(
            recommendation_id="asr_by_assignment",
            assignment_id="pa_001",
            recommended_priority=PracticeQueuePriority.critical,
        )
        rec_by_diagnosis = make_recommendation(
            recommendation_id="asr_by_diagnosis",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommended_priority=PracticeQueuePriority.low,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec_by_assignment, rec_by_diagnosis],
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.critical

    def test_empty_recommendations_returns_copy(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        queue = make_queue([assignment])

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[],
        )

        assert updated is not queue
        assert len(updated.assignments) == 1


class TestQueuePropertiesPreserved:
    """Test queue-level properties are preserved."""

    def test_queue_id_preserved(self) -> None:
        queue = make_queue([], queue_id="queue_original123")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[],
        )

        assert updated.id == "queue_original123"

    def test_student_id_preserved(self) -> None:
        queue = PracticeQueue(
            id="queue_123",
            student_id="student_special",
            assignments=[],
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[],
        )

        assert updated.student_id == "student_special"

    def test_generated_at_preserved(self) -> None:
        original_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        queue = PracticeQueue(
            id="queue_123",
            assignments=[],
            generated_at=original_time,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[],
        )

        assert updated.generated_at == original_time

    def test_version_preserved(self) -> None:
        queue = PracticeQueue(
            id="queue_123",
            assignments=[],
            version="1.0",
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[],
        )

        assert updated.version == "1.0"


class TestAssignmentPropertiesPreserved:
    """Test assignment-level properties are preserved."""

    def test_status_preserved(self) -> None:
        assignment = make_assignment(assignment_id="pa_001")
        assignment = ScheduledPracticeAssignment(
            scheduled_id="sq_001",
            queue_id="queue_001",
            assignment_id="pa_001",
            title="Test",
            status=PracticeQueueStatus.active,
            scheduled_order=0,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(assignment_id="pa_001")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].status == PracticeQueueStatus.active

    def test_deferred_until_not_changed(self) -> None:
        deferred_time = datetime(2026, 6, 1, tzinfo=timezone.utc)
        assignment = ScheduledPracticeAssignment(
            scheduled_id="sq_001",
            queue_id="queue_001",
            assignment_id="pa_001",
            title="Test",
            scheduled_order=0,
            deferred_until=deferred_time,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_001",
            recommended_delay_days=10,
        )

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].deferred_until == deferred_time

    def test_existing_metadata_preserved(self) -> None:
        assignment = make_assignment(
            assignment_id="pa_001",
            metadata={"custom": "value", "another": 123},
        )
        queue = make_queue([assignment])
        rec = make_recommendation(assignment_id="pa_001")

        updated = apply_adaptive_recommendations_to_queue(
            queue=queue,
            recommendations=[rec],
        )

        assert updated.assignments[0].metadata["custom"] == "value"
        assert updated.assignments[0].metadata["another"] == 123
        assert "adaptive_scheduling" in updated.assignments[0].metadata
