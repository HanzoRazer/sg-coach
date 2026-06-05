"""
Tests for Teacher Scheduling Mediation.

Sprint 31: Teacher-Adaptive Scheduling Mediation.
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
    ScheduledPracticeAssignment,
)
from sg_spec.schemas.teacher_scheduling_mediation import (
    MediationAction,
    TeacherSchedulingMediation,
    TeacherSchedulingOverride,
)

from sg_coach.teacher_scheduling_mediation import (
    TEACHER_SCHEDULING_MEDIATION_VERSION,
    create_teacher_scheduling_mediation,
    effective_recommendation_from_mediation,
    apply_mediation_to_queue,
)


def make_recommendation(
    recommendation_id: str = "asr_abc123def456",
    assignment_id: str | None = None,
    diagnosis_code: DiagnosisCode | None = DiagnosisCode.TIMING_GRID_DEVIATION,
    recommended_priority: PracticeQueuePriority = PracticeQueuePriority.high,
    recommended_repetition_count: int | None = 2,
    recommended_delay_days: int | None = None,
) -> AdaptiveSchedulingRecommendation:
    """Create a test recommendation."""
    return AdaptiveSchedulingRecommendation(
        recommendation_id=recommendation_id,
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        priority_adjustment=SchedulingPriorityAdjustment.increase,
        recommended_priority=recommended_priority,
        recommended_repetition_count=recommended_repetition_count,
        recommended_delay_days=recommended_delay_days,
        reasons=[SchedulingRecommendationReason.worsening_trend],
        evidence_ids=["ped_001"],
        rationale="Test rationale",
    )


def make_assignment(
    scheduled_id: str = "sq_abc123def456",
    queue_id: str = "queue_xyz789",
    assignment_id: str = "pa_test123",
    diagnosis_code: DiagnosisCode | None = DiagnosisCode.TIMING_GRID_DEVIATION,
    priority: PracticeQueuePriority = PracticeQueuePriority.normal,
) -> ScheduledPracticeAssignment:
    """Create a test assignment."""
    return ScheduledPracticeAssignment(
        scheduled_id=scheduled_id,
        queue_id=queue_id,
        assignment_id=assignment_id,
        diagnosis_code=diagnosis_code,
        title="Test Assignment",
        priority=priority,
        scheduled_order=0,
    )


def make_queue(
    assignments: list[ScheduledPracticeAssignment] | None = None,
) -> PracticeQueue:
    """Create a test queue."""
    return PracticeQueue(
        id="queue_xyz789",
        student_id="student_123",
        assignments=assignments or [],
    )


class TestConstants:
    """Test module constants."""

    def test_version_defined(self) -> None:
        assert TEACHER_SCHEDULING_MEDIATION_VERSION == "0.1.0"


class TestCreateTeacherSchedulingMediation:
    """Tests for create_teacher_scheduling_mediation."""

    def test_creates_approve_mediation(self) -> None:
        rec = make_recommendation()

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        assert mediation.id.startswith("tsm_")
        assert mediation.recommendation_id == rec.recommendation_id
        assert mediation.teacher_id == "teacher_001"
        assert mediation.action == MediationAction.approve

    def test_preserves_recommendation_context(self) -> None:
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            assignment_id="pa_specific",
        )

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
            student_id="student_xyz",
        )

        assert mediation.diagnosis_code == DiagnosisCode.PITCH_DEVIATION
        assert mediation.assignment_id == "pa_specific"
        assert mediation.student_id == "student_xyz"

    def test_stores_original_values_in_metadata(self) -> None:
        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=3,
            recommended_delay_days=2,
        )

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        assert mediation.metadata["original_priority_adjustment"] == "increase"
        assert mediation.metadata["original_recommended_priority"] == "high"
        assert mediation.metadata["original_recommended_repetition_count"] == 3
        assert mediation.metadata["original_recommended_delay_days"] == 2

    def test_accepts_override_for_approve_modified(self) -> None:
        rec = make_recommendation()
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Increased priority",
        )

        assert mediation.action == MediationAction.approve_modified
        assert mediation.override is not None
        assert mediation.override.recommended_priority == PracticeQueuePriority.critical

    def test_accepts_prior_mediation_id(self) -> None:
        rec = make_recommendation()

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not needed",
            prior_mediation_id="tsm_previous123",
        )

        assert mediation.prior_mediation_id == "tsm_previous123"

    def test_accepts_explicit_mediation_id(self) -> None:
        rec = make_recommendation()

        mediation = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
            mediation_id="tsm_explicit123",
        )

        assert mediation.id == "tsm_explicit123"

    def test_unique_ids_generated(self) -> None:
        rec = make_recommendation()

        med1 = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )
        med2 = create_teacher_scheduling_mediation(
            recommendation=rec,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        assert med1.id != med2.id


class TestEffectiveRecommendationFromMediation:
    """Tests for effective_recommendation_from_mediation."""

    def test_approve_returns_original(self) -> None:
        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is not None
        assert effective.recommended_priority == PracticeQueuePriority.high
        assert "mediation_id" in effective.metadata
        assert effective.metadata["mediation_action"] == "approve"

    def test_reject_returns_none(self) -> None:
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not appropriate",
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is None

    def test_defer_returns_none(self) -> None:
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.defer,
            rationale="Need to discuss",
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is None

    def test_approve_modified_applies_overrides(self) -> None:
        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=2,
        )
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
            recommended_repetition_count=5,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Increased",
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is not None
        assert effective.recommended_priority == PracticeQueuePriority.critical
        assert effective.recommended_repetition_count == 5

    def test_approve_modified_partial_override(self) -> None:
        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=2,
            recommended_delay_days=3,
        )
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Priority only",
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is not None
        assert effective.recommended_priority == PracticeQueuePriority.critical
        assert effective.recommended_repetition_count == 2
        assert effective.recommended_delay_days == 3

    def test_approve_modified_includes_override_in_metadata(self) -> None:
        rec = make_recommendation()
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Modified",
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is not None
        assert "teacher_override" in effective.metadata
        assert effective.metadata["teacher_override"]["recommended_priority"] == "critical"

    def test_preserves_original_fields(self) -> None:
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            assignment_id="pa_specific",
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        effective = effective_recommendation_from_mediation(
            mediation=mediation,
            original_recommendation=rec,
        )

        assert effective is not None
        assert effective.diagnosis_code == DiagnosisCode.PITCH_DEVIATION
        assert effective.assignment_id == "pa_specific"
        assert effective.evidence_ids == ["ped_001"]
        assert effective.rationale == "Test rationale"


class TestApplyMediationToQueue:
    """Tests for apply_mediation_to_queue."""

    def test_approved_mediation_updates_priority(self) -> None:
        assignment = make_assignment(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            priority=PracticeQueuePriority.normal,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.high

    def test_rejected_mediation_adds_metadata_no_priority_change(self) -> None:
        assignment = make_assignment(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            priority=PracticeQueuePriority.normal,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not needed",
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.normal
        assert "teacher_scheduling_mediation" in updated.assignments[0].metadata

    def test_mediation_metadata_includes_action(self) -> None:
        assignment = make_assignment()
        queue = make_queue([assignment])
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        meta = updated.assignments[0].metadata["teacher_scheduling_mediation"]
        assert meta["mediation_id"] == "tsm_test123"
        assert meta["mediation_action"] == "approve"
        assert meta["teacher_id"] == "teacher_001"

    def test_mediation_metadata_includes_rationale(self) -> None:
        assignment = make_assignment()
        queue = make_queue([assignment])
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Student not ready",
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        meta = updated.assignments[0].metadata["teacher_scheduling_mediation"]
        assert meta["rationale"] == "Student not ready"

    def test_matches_by_assignment_id(self) -> None:
        assignment = make_assignment(
            assignment_id="pa_specific",
            diagnosis_code=None,
        )
        queue = make_queue([assignment])
        rec = make_recommendation(
            assignment_id="pa_specific",
            diagnosis_code=None,
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.high

    def test_non_matching_assignments_unchanged(self) -> None:
        assignment1 = make_assignment(
            scheduled_id="sq_001",
            assignment_id="pa_001",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            priority=PracticeQueuePriority.normal,
        )
        assignment2 = make_assignment(
            scheduled_id="sq_002",
            assignment_id="pa_002",
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            priority=PracticeQueuePriority.low,
        )
        queue = make_queue([assignment1, assignment2])
        rec = make_recommendation(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated.assignments[0].priority == PracticeQueuePriority.high
        assert updated.assignments[1].priority == PracticeQueuePriority.low
        assert "teacher_scheduling_mediation" not in updated.assignments[1].metadata

    def test_queue_properties_preserved(self) -> None:
        queue = PracticeQueue(
            id="queue_original",
            student_id="student_xyz",
            assignments=[],
        )
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated.id == "queue_original"
        assert updated.student_id == "student_xyz"

    def test_returns_new_queue_object(self) -> None:
        queue = make_queue([make_assignment()])
        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        updated = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=rec,
        )

        assert updated is not queue


class TestLedgerIntegration:
    """Tests for ledger entry conversion."""

    def test_creates_ledger_entry_from_mediation(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation
        from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceSource

        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            student_id="student_123",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=MediationAction.approve,
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.source == PedagogicalEvidenceSource.teacher_scheduling_mediation
        assert entry.student_id == "student_123"
        assert entry.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert "tsm_test123" in entry.provenance[0]

    def test_ledger_entry_includes_mediation_metadata(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation

        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Increased priority",
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.metadata["action"] == "approve_modified"
        assert entry.metadata["teacher_id"] == "teacher_001"
        assert "override" in entry.metadata

    def test_ledger_entry_reject_has_critical_severity(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation
        from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceSeverity

        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not needed",
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.severity == PedagogicalEvidenceSeverity.critical

    def test_ledger_entry_approve_modified_has_warning_severity(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation
        from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceSeverity

        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Modified",
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.severity == PedagogicalEvidenceSeverity.warning

    def test_ledger_entry_defer_has_warning_severity(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation
        from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceSeverity

        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            action=MediationAction.defer,
            rationale="Pending discussion",
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.severity == PedagogicalEvidenceSeverity.warning

    def test_ledger_entry_approve_has_informational_severity(self) -> None:
        from sg_coach.pedagogical_ledger import ledger_entry_from_teacher_scheduling_mediation
        from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceSeverity

        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id="asr_xyz789",
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        entry = ledger_entry_from_teacher_scheduling_mediation(mediation)

        assert entry.severity == PedagogicalEvidenceSeverity.informational


class TestEffectiveSchedulingDecision:
    """Tests for effective_scheduling_decision_from_mediation."""

    def test_approve_sets_approved_flag(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.approved is True
        assert decision.rejected is False
        assert decision.deferred is False

    def test_reject_sets_rejected_flag(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not needed",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.approved is False
        assert decision.rejected is True
        assert decision.deferred is False

    def test_defer_sets_deferred_flag(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.defer,
            rationale="Pending discussion",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.approved is False
        assert decision.rejected is False
        assert decision.deferred is True

    def test_approve_modified_sets_approved_flag(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Modified",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.approved is True
        assert decision.rejected is False
        assert decision.deferred is False

    def test_approve_uses_recommendation_values(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=3,
            recommended_delay_days=2,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.effective_priority == PracticeQueuePriority.high
        assert decision.effective_repetition_count == 3
        assert decision.effective_delay_days == 2

    def test_approve_modified_uses_override_values(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=3,
        )
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
            recommended_repetition_count=5,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Increased",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.effective_priority == PracticeQueuePriority.critical
        assert decision.effective_repetition_count == 5

    def test_approve_modified_partial_override_uses_fallback(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
            recommended_repetition_count=3,
            recommended_delay_days=2,
        )
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.critical,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve_modified,
            override=override,
            rationale="Priority only",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.effective_priority == PracticeQueuePriority.critical
        assert decision.effective_repetition_count == 3
        assert decision.effective_delay_days == 2

    def test_rejected_has_no_effective_values(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation(
            recommended_priority=PracticeQueuePriority.high,
        )
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Not needed",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.effective_priority is None
        assert decision.effective_repetition_count is None
        assert decision.effective_delay_days is None

    def test_includes_evidence_ids(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.evidence_ids == ["ped_001"]

    def test_includes_rationale(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation()
        mediation = TeacherSchedulingMediation(
            id="tsm_test123",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.reject,
            rationale="Student needs rest",
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.rationale == "Student needs rest"

    def test_includes_ids(self) -> None:
        from sg_coach.teacher_scheduling_mediation import effective_scheduling_decision_from_mediation

        rec = make_recommendation(recommendation_id="asr_specific")
        mediation = TeacherSchedulingMediation(
            id="tsm_specific",
            recommendation_id=rec.recommendation_id,
            teacher_id="teacher_001",
            action=MediationAction.approve,
        )

        decision = effective_scheduling_decision_from_mediation(
            recommendation=rec,
            mediation=mediation,
        )

        assert decision.recommendation_id == "asr_specific"
        assert decision.mediation_id == "tsm_specific"
