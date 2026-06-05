"""
Tests for Adaptive Scheduling Engine.

Sprint 30: Evidence-Driven Adaptive Scheduling.
"""
from datetime import datetime, timezone

import pytest

from sg_spec.schemas.adaptive_scheduling import (
    AdaptiveSchedulingPlan,
    AdaptiveSchedulingRecommendation,
    SchedulingPriorityAdjustment,
    SchedulingRecommendationReason,
)
from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceLedger,
    PedagogicalEvidenceSource,
)
from sg_spec.schemas.practice_queue import PracticeQueuePriority

from sg_coach.adaptive_scheduling import (
    ADAPTIVE_SCHEDULING_VERSION,
    REPEATED_OUTCOME_THRESHOLD,
    RECURRING_DIAGNOSIS_THRESHOLD,
    ABANDONMENT_THRESHOLD,
    build_adaptive_scheduling_recommendations,
    build_adaptive_scheduling_plan,
    apply_adaptive_recommendations_to_queue,
)


def make_entry(
    evidence_id: str = "ped_abc123def456",
    source: PedagogicalEvidenceSource = PedagogicalEvidenceSource.runtime_review,
    diagnosis_code: DiagnosisCode | None = None,
    assignment_id: str | None = None,
    metadata: dict | None = None,
) -> PedagogicalEvidenceEntry:
    """Create a test evidence entry."""
    return PedagogicalEvidenceEntry(
        evidence_id=evidence_id,
        source=source,
        timestamp=datetime.now(timezone.utc),
        diagnosis_code=diagnosis_code,
        assignment_id=assignment_id,
        title="Test entry",
        summary="Test summary",
        metadata=metadata or {},
    )


def make_ledger(
    entries: list[PedagogicalEvidenceEntry] | None = None,
    student_id: str | None = None,
) -> PedagogicalEvidenceLedger:
    """Create a test ledger."""
    return PedagogicalEvidenceLedger(
        student_id=student_id,
        entries=entries or [],
    )


class TestConstants:
    """Test module constants."""

    def test_version_defined(self) -> None:
        assert ADAPTIVE_SCHEDULING_VERSION == "0.1.0"

    def test_repeated_outcome_threshold(self) -> None:
        assert REPEATED_OUTCOME_THRESHOLD == 2

    def test_recurring_diagnosis_threshold(self) -> None:
        assert RECURRING_DIAGNOSIS_THRESHOLD == 3

    def test_abandonment_threshold(self) -> None:
        assert ABANDONMENT_THRESHOLD == 1


class TestWorseningTrend:
    """Test worsening trend detection."""

    def test_worsening_trend_increases_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 1
        assert recs[0].priority_adjustment == SchedulingPriorityAdjustment.increase
        assert recs[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert SchedulingRecommendationReason.worsening_trend in recs[0].reasons

    def test_worsening_trend_sets_high_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert recs[0].recommended_priority == PracticeQueuePriority.high

    def test_worsening_rationale_deterministic(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert "timing grid deviation" in recs[0].rationale.lower()
        assert "higher" in recs[0].rationale.lower() or "worsening" in recs[0].rationale.lower()


class TestImprovingTrend:
    """Test improving trend detection."""

    def test_improving_trend_decreases_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "improving"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 1
        assert recs[0].priority_adjustment == SchedulingPriorityAdjustment.decrease
        assert SchedulingRecommendationReason.improving_trend in recs[0].reasons

    def test_improving_trend_sets_low_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "improving"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert recs[0].recommended_priority == PracticeQueuePriority.low

    def test_improving_trend_suggests_delay(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "improving"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert recs[0].recommended_delay_days is not None
        assert recs[0].recommended_delay_days > 0


class TestRepeatedOutcomes:
    """Test repeated outcome detection."""

    def test_repeated_outcomes_increase_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.assignment_outcome,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"outcome": "repeated"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.assignment_outcome,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"outcome": "repeated"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.repeated_outcomes in r.reasons]
        assert len(matching) == 1
        assert matching[0].priority_adjustment == SchedulingPriorityAdjustment.increase

    def test_repeated_outcomes_below_threshold_ignored(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.assignment_outcome,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"outcome": "repeated"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.repeated_outcomes in r.reasons]
        assert len(matching) == 0

    def test_repeated_outcomes_by_assignment_id(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.assignment_outcome,
                assignment_id="pa_xyz789",
                metadata={"outcome": "repeated"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.assignment_outcome,
                assignment_id="pa_xyz789",
                metadata={"outcome": "repeated"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.repeated_outcomes in r.reasons]
        assert len(matching) == 1
        assert matching[0].assignment_id == "pa_xyz789"


class TestAbandonmentPattern:
    """Test abandonment pattern detection."""

    def test_abandonment_from_assignment_outcome(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.assignment_outcome,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"outcome": "abandoned"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.abandonment_pattern in r.reasons]
        assert len(matching) == 1

    def test_abandonment_from_queue_event(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.queue_event,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"event_type": "assignment_abandoned"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.abandonment_pattern in r.reasons]
        assert len(matching) == 1

    def test_abandonment_triggers_increase_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.assignment_outcome,
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                metadata={"outcome": "abandoned"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.abandonment_pattern in r.reasons]
        assert matching[0].priority_adjustment == SchedulingPriorityAdjustment.increase


class TestRecurringDiagnosis:
    """Test recurring diagnosis frequency detection."""

    def test_recurring_diagnosis_triggers_recommendation(self) -> None:
        entries = [
            make_entry(
                evidence_id=f"ped_{i:03d}",
                source=PedagogicalEvidenceSource.runtime_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            )
            for i in range(3)
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.recurring_issue in r.reasons]
        assert len(matching) == 1

    def test_recurring_diagnosis_below_threshold_ignored(self) -> None:
        entries = [
            make_entry(
                evidence_id=f"ped_{i:03d}",
                source=PedagogicalEvidenceSource.runtime_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            )
            for i in range(2)
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        matching = [r for r in recs if SchedulingRecommendationReason.recurring_issue in r.reasons]
        assert len(matching) == 0


class TestStableEvidence:
    """Test stable evidence handling."""

    def test_stable_trend_no_recommendation(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "stable"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 0

    def test_empty_ledger_no_recommendations(self) -> None:
        ledger = make_ledger([])

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 0


class TestRecommendationOrdering:
    """Test recommendation ordering is deterministic."""

    def test_higher_priority_first(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "improving"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 2
        assert recs[0].recommended_priority == PracticeQueuePriority.high
        assert recs[1].recommended_priority == PracticeQueuePriority.low

    def test_more_evidence_first_when_same_priority(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "worsening"},
            ),
            make_entry(
                evidence_id="ped_003",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 2
        assert recs[0].diagnosis_code == DiagnosisCode.PITCH_DEVIATION
        assert len(recs[0].evidence_ids) > len(recs[1].evidence_ids)

    def test_alphabetical_when_same_priority_and_evidence_count(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                metadata={"trend": "worsening"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 2
        assert recs[0].diagnosis_code == DiagnosisCode.DIM_ORBIT_VIOLATION
        assert recs[1].diagnosis_code == DiagnosisCode.WRONG_NOTE


class TestEvidencePreservation:
    """Test evidence IDs are preserved in recommendations."""

    def test_evidence_ids_preserved(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_unique123",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert "ped_unique123" in recs[0].evidence_ids

    def test_multiple_evidence_ids_preserved(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert "ped_001" in recs[0].evidence_ids
        assert "ped_002" in recs[0].evidence_ids


class TestRationaleDeterministic:
    """Test rationale generation is deterministic."""

    def test_rationale_not_empty(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs[0].rationale) > 0

    def test_rationale_same_for_same_input(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger1 = make_ledger(entries)
        ledger2 = make_ledger(entries)

        recs1 = build_adaptive_scheduling_recommendations(ledger=ledger1)
        recs2 = build_adaptive_scheduling_recommendations(ledger=ledger2)

        assert recs1[0].rationale == recs2[0].rationale


class TestRecommendationIdGeneration:
    """Test recommendation ID generation."""

    def test_recommendation_id_format(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert recs[0].recommendation_id.startswith("asr_")
        assert len(recs[0].recommendation_id) == 16  # asr_ + 12 hex chars

    def test_unique_recommendation_ids(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
            make_entry(
                evidence_id="ped_002",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        ids = [r.recommendation_id for r in recs]
        assert len(ids) == len(set(ids))


class TestNoTargetSkipped:
    """Test entries without diagnosis_code or assignment_id are skipped."""

    def test_no_diagnosis_no_assignment_skipped(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=None,
                assignment_id=None,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger)

        assert len(recs) == 0


class TestPlanGeneration:
    """Test adaptive scheduling plan generation."""

    def test_plan_generation_works(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries, student_id="student_123")

        plan = build_adaptive_scheduling_plan(ledger=ledger)

        assert plan.student_id == "student_123"
        assert plan.source_evidence_count == 1
        assert len(plan.recommendations) == 1

    def test_plan_uses_provided_student_id(self) -> None:
        ledger = make_ledger([], student_id="ledger_student")

        plan = build_adaptive_scheduling_plan(
            ledger=ledger,
            student_id="explicit_student",
        )

        assert plan.student_id == "explicit_student"

    def test_plan_falls_back_to_ledger_student_id(self) -> None:
        ledger = make_ledger([], student_id="ledger_student")

        plan = build_adaptive_scheduling_plan(ledger=ledger)

        assert plan.student_id == "ledger_student"

    def test_plan_generated_at_populated(self) -> None:
        ledger = make_ledger([])
        before = datetime.now(timezone.utc)

        plan = build_adaptive_scheduling_plan(ledger=ledger)

        after = datetime.now(timezone.utc)
        assert before <= plan.generated_at <= after

    def test_empty_ledger_produces_empty_plan(self) -> None:
        ledger = make_ledger([])

        plan = build_adaptive_scheduling_plan(ledger=ledger)

        assert len(plan.recommendations) == 0
        assert plan.source_evidence_count == 0


class TestQueuelessAnalysis:
    """Test analysis without queue."""

    def test_generates_recommendations_without_queue(self) -> None:
        entries = [
            make_entry(
                evidence_id="ped_001",
                source=PedagogicalEvidenceSource.longitudinal_review,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                metadata={"trend": "worsening"},
            ),
        ]
        ledger = make_ledger(entries)

        recs = build_adaptive_scheduling_recommendations(ledger=ledger, queue=None)

        assert len(recs) == 1
        assert recs[0].assignment_id is None
        assert recs[0].diagnosis_code is not None
