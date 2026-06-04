"""
Tests for Pedagogical Evidence Ledger Builder.

Sprint 29: Pedagogical Evidence Ledger.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    CoachFinding,
    DiagnosisCode,
    FocusRecommendation,
    Severity,
)
from sg_spec.schemas.curriculum_progression import (
    CurriculumRecommendation,
    ProgressionLevel,
)
from sg_spec.schemas.longitudinal_review import (
    DiagnosisTrendSummary,
    LongitudinalProgressReview,
    LongitudinalTrend,
    OutcomeTrajectorySummary,
)
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceSource,
    PedagogicalEvidenceSeverity,
)
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_queue import (
    PracticeQueueEvent,
    PracticeQueueEventType,
)
from sg_spec.schemas.runtime_flow import (
    RuntimePracticeSession,
    RuntimeSessionStatus,
)
from sg_spec.schemas.runtime_review import (
    RuntimeReviewReport,
    RuntimeReviewStatus,
    RuntimeEvidenceSummary,
    RuntimeOutcomeSummary,
)
from sg_spec.schemas.teacher_review import (
    TeacherAnnotation,
    TeacherAnnotationType,
    TeacherRecommendation,
    TeacherRecommendationType,
    TeacherReview,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.pedagogical_ledger import (
    PEDAGOGICAL_LEDGER_BUILDER_VERSION,
    ledger_entries_from_runtime_review,
    ledger_entries_from_longitudinal_review,
    ledger_entry_from_queue_event,
    ledger_entries_from_teacher_review,
    ledger_entry_from_assignment_outcome,
    ledger_entry_from_practice_assignment,
    ledger_entry_from_curriculum_recommendation,
    build_pedagogical_evidence_ledger,
    build_pedagogical_evidence_summary,
)


def make_test_finding(
    code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    finding_id: str = "finding_001",
) -> CoachFinding:
    """Create a test finding."""
    return CoachFinding(
        id=finding_id,
        code=code,
        type="timing",
        severity=Severity.primary,
        interpretation="Test interpretation",
        message="Test message",
    )


def make_test_evaluation(
    session_id,
    codes: list[DiagnosisCode] | None = None,
) -> CoachEvaluation:
    """Create a test evaluation."""
    codes = codes or []
    findings = [make_test_finding(code, f"finding_{i}") for i, code in enumerate(codes)]

    return CoachEvaluation(
        session_id=session_id,
        coach_version="test@0.1.0",
        findings=findings,
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Focus on timing",
        ),
        confidence=0.8,
    )


def make_test_runtime_session(
    runtime_session_id: str = "rts_test123",
    evaluation_codes: list[DiagnosisCode] | None = None,
) -> RuntimePracticeSession:
    """Create a test runtime session."""
    session_id = uuid4()
    evaluation = None
    if evaluation_codes is not None:
        evaluation = make_test_evaluation(session_id, evaluation_codes)

    return RuntimePracticeSession(
        runtime_session_id=runtime_session_id,
        queue_id="queue_test123",
        scheduled_id="sq_test123",
        assignment_id="pa_test123",
        student_id="student_123",
        status=RuntimeSessionStatus.completed,
        evaluation=evaluation,
    )


def make_test_runtime_review_report(
    runtime_session_id: str = "rts_test123",
    evaluation_codes: list[DiagnosisCode] | None = None,
    generated_at: datetime | None = None,
) -> RuntimeReviewReport:
    """Create a test runtime review report."""
    session = make_test_runtime_session(runtime_session_id, evaluation_codes)

    return RuntimeReviewReport(
        runtime_session_id=runtime_session_id,
        runtime_session=session,
        status=RuntimeReviewStatus.complete,
        evidence_summary=RuntimeEvidenceSummary(
            finding_count=len(evaluation_codes) if evaluation_codes else 0,
        ),
        outcome_summary=RuntimeOutcomeSummary(
            outcome=PracticeOutcome.completed,
        ),
        generated_at=generated_at or datetime.now(timezone.utc),
    )


def make_test_longitudinal_review(
    trends: list[DiagnosisTrendSummary] | None = None,
    outcome_trajectory: OutcomeTrajectorySummary | None = None,
) -> LongitudinalProgressReview:
    """Create a test longitudinal review."""
    return LongitudinalProgressReview(
        student_id="student_123",
        review_count=5,
        diagnosis_trends=trends or [],
        outcome_trajectory=outcome_trajectory,
        evidence_review_ids=["rts_001", "rts_002"],
    )


def make_test_queue_event(
    event_type: PracticeQueueEventType = PracticeQueueEventType.assignment_completed,
) -> PracticeQueueEvent:
    """Create a test queue event."""
    return PracticeQueueEvent(
        id="pqe_test123",
        queue_id="queue_test123",
        assignment_id="pa_test123",
        event_type=event_type,
    )


def make_test_teacher_review(
    annotations: list[TeacherAnnotation] | None = None,
    recommendations: list[TeacherRecommendation] | None = None,
) -> TeacherReview:
    """Create a test teacher review."""
    return TeacherReview(
        id="trv_test123",
        teacher_id="teacher_001",
        student_id="student_123",
        annotations=annotations or [],
        recommendations=recommendations or [],
    )


def make_test_assignment_outcome(
    outcome: PracticeOutcome = PracticeOutcome.completed,
) -> AssignmentOutcomeEvent:
    """Create a test assignment outcome."""
    return AssignmentOutcomeEvent(
        id="ao_test123",
        assignment_id="pa_test123",
        outcome=outcome,
    )


def make_test_practice_assignment(
    assignment_id: str = "pa_test123",
    diagnosis_code: DiagnosisCode | None = None,
) -> AssembledPracticeAssignment:
    """Create a test practice assignment."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        title="Test Assignment",
        instructions="Practice this drill",
        assignment_type=PracticeAssignmentType.drill,
        diagnosis_code=diagnosis_code,
    )


def make_test_curriculum_recommendation(
    content_id: str = "timing_foundation_v1",
    diagnosis_code: str = "timing_grid_deviation",
) -> CurriculumRecommendation:
    """Create a test curriculum recommendation."""
    return CurriculumRecommendation(
        content_id=content_id,
        diagnosis_code=diagnosis_code,
        progression_level=ProgressionLevel.beginner,
        reason="Recommended based on diagnosis",
    )


class TestLedgerEntriesFromRuntimeReview:
    """Tests for ledger_entries_from_runtime_review."""

    def test_no_evaluation_returns_empty(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=None)
        entries = ledger_entries_from_runtime_review(report)
        assert entries == []

    def test_empty_findings_returns_empty(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[])
        entries = ledger_entries_from_runtime_review(report)
        assert entries == []

    def test_one_entry_per_finding(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
            DiagnosisCode.PITCH_DEVIATION,
        ])
        entries = ledger_entries_from_runtime_review(report)

        assert len(entries) == 2
        codes = {e.diagnosis_code for e in entries}
        assert DiagnosisCode.TIMING_GRID_DEVIATION in codes
        assert DiagnosisCode.PITCH_DEVIATION in codes

    def test_source_is_runtime_review(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
        ])
        entries = ledger_entries_from_runtime_review(report)

        assert entries[0].source == PedagogicalEvidenceSource.runtime_review

    def test_provenance_includes_runtime_session_id(self) -> None:
        report = make_test_runtime_review_report(
            runtime_session_id="rts_abc123",
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
        )
        entries = ledger_entries_from_runtime_review(report)

        assert "runtime_review:rts_abc123" in entries[0].provenance

    def test_title_format(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
        ])
        entries = ledger_entries_from_runtime_review(report)

        assert entries[0].title == "Runtime finding: timing_grid_deviation"

    def test_evidence_id_has_ped_prefix(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
        ])
        entries = ledger_entries_from_runtime_review(report)

        assert entries[0].evidence_id.startswith("ped_")


class TestLedgerEntriesFromLongitudinalReview:
    """Tests for ledger_entries_from_longitudinal_review."""

    def test_empty_trends_returns_empty(self) -> None:
        review = make_test_longitudinal_review(trends=[])
        entries = ledger_entries_from_longitudinal_review(review)
        assert entries == []

    def test_one_entry_per_trend(self) -> None:
        trends = [
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                trend=LongitudinalTrend.improving,
            ),
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                trend=LongitudinalTrend.stable,
            ),
        ]
        review = make_test_longitudinal_review(trends=trends)
        entries = ledger_entries_from_longitudinal_review(review)

        assert len(entries) == 2

    def test_outcome_trajectory_creates_entry(self) -> None:
        trajectory = OutcomeTrajectorySummary(
            total_completed=3,
            total_improved=2,
        )
        review = make_test_longitudinal_review(outcome_trajectory=trajectory)
        entries = ledger_entries_from_longitudinal_review(review)

        assert len(entries) == 1
        assert entries[0].title == "Outcome trajectory summary"

    def test_provenance_includes_evidence_review_ids(self) -> None:
        trends = [
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                trend=LongitudinalTrend.improving,
            ),
        ]
        review = make_test_longitudinal_review(trends=trends)
        entries = ledger_entries_from_longitudinal_review(review)

        assert "runtime_review:rts_001" in entries[0].provenance
        assert "runtime_review:rts_002" in entries[0].provenance

    def test_worsening_trend_is_critical(self) -> None:
        trends = [
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                trend=LongitudinalTrend.worsening,
            ),
        ]
        review = make_test_longitudinal_review(trends=trends)
        entries = ledger_entries_from_longitudinal_review(review)

        assert entries[0].severity == PedagogicalEvidenceSeverity.critical

    def test_stable_trend_is_warning(self) -> None:
        trends = [
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                trend=LongitudinalTrend.stable,
            ),
        ]
        review = make_test_longitudinal_review(trends=trends)
        entries = ledger_entries_from_longitudinal_review(review)

        assert entries[0].severity == PedagogicalEvidenceSeverity.warning

    def test_improving_trend_is_informational(self) -> None:
        trends = [
            DiagnosisTrendSummary(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                trend=LongitudinalTrend.improving,
            ),
        ]
        review = make_test_longitudinal_review(trends=trends)
        entries = ledger_entries_from_longitudinal_review(review)

        assert entries[0].severity == PedagogicalEvidenceSeverity.informational


class TestLedgerEntryFromQueueEvent:
    """Tests for ledger_entry_from_queue_event."""

    def test_creates_single_entry(self) -> None:
        event = make_test_queue_event()
        entry = ledger_entry_from_queue_event(event)

        assert entry is not None
        assert entry.source == PedagogicalEvidenceSource.queue_event

    def test_abandoned_is_critical(self) -> None:
        event = make_test_queue_event(PracticeQueueEventType.assignment_abandoned)
        entry = ledger_entry_from_queue_event(event)

        assert entry.severity == PedagogicalEvidenceSeverity.critical

    def test_deferred_is_warning(self) -> None:
        event = make_test_queue_event(PracticeQueueEventType.assignment_deferred)
        entry = ledger_entry_from_queue_event(event)

        assert entry.severity == PedagogicalEvidenceSeverity.warning

    def test_completed_is_informational(self) -> None:
        event = make_test_queue_event(PracticeQueueEventType.assignment_completed)
        entry = ledger_entry_from_queue_event(event)

        assert entry.severity == PedagogicalEvidenceSeverity.informational

    def test_provenance_includes_event_id(self) -> None:
        event = make_test_queue_event()
        entry = ledger_entry_from_queue_event(event)

        assert f"queue_event:{event.id}" in entry.provenance


class TestLedgerEntriesFromTeacherReview:
    """Tests for ledger_entries_from_teacher_review."""

    def test_empty_review_returns_empty(self) -> None:
        review = make_test_teacher_review()
        entries = ledger_entries_from_teacher_review(review)
        assert entries == []

    def test_one_entry_per_annotation(self) -> None:
        annotations = [
            TeacherAnnotation(
                id="ta_001",
                annotation_type=TeacherAnnotationType.note,
                text="Good progress",
            ),
            TeacherAnnotation(
                id="ta_002",
                annotation_type=TeacherAnnotationType.correction,
                text="Watch your timing",
            ),
        ]
        review = make_test_teacher_review(annotations=annotations)
        entries = ledger_entries_from_teacher_review(review)

        assert len(entries) == 2

    def test_one_entry_per_recommendation(self) -> None:
        recommendations = [
            TeacherRecommendation(
                id="tr_001",
                recommendation_type=TeacherRecommendationType.add_assignment,
                text="Focus on timing",
            ),
        ]
        review = make_test_teacher_review(recommendations=recommendations)
        entries = ledger_entries_from_teacher_review(review)

        assert len(entries) == 1

    def test_warning_annotation_is_warning_severity(self) -> None:
        annotations = [
            TeacherAnnotation(
                annotation_type=TeacherAnnotationType.warning,
                text="Be careful",
            ),
        ]
        review = make_test_teacher_review(annotations=annotations)
        entries = ledger_entries_from_teacher_review(review)

        assert entries[0].severity == PedagogicalEvidenceSeverity.warning

    def test_provenance_includes_review_id(self) -> None:
        annotations = [
            TeacherAnnotation(
                annotation_type=TeacherAnnotationType.note,
                text="Test",
            ),
        ]
        review = make_test_teacher_review(annotations=annotations)
        entries = ledger_entries_from_teacher_review(review)

        assert f"teacher_review:{review.id}" in entries[0].provenance


class TestLedgerEntryFromAssignmentOutcome:
    """Tests for ledger_entry_from_assignment_outcome."""

    def test_creates_single_entry(self) -> None:
        event = make_test_assignment_outcome()
        entry = ledger_entry_from_assignment_outcome(event)

        assert entry is not None
        assert entry.source == PedagogicalEvidenceSource.assignment_outcome

    def test_abandoned_is_critical(self) -> None:
        event = make_test_assignment_outcome(PracticeOutcome.abandoned)
        entry = ledger_entry_from_assignment_outcome(event)

        assert entry.severity == PedagogicalEvidenceSeverity.critical

    def test_worsened_is_warning(self) -> None:
        event = make_test_assignment_outcome(PracticeOutcome.worsened)
        entry = ledger_entry_from_assignment_outcome(event)

        assert entry.severity == PedagogicalEvidenceSeverity.warning

    def test_repeated_is_warning(self) -> None:
        event = make_test_assignment_outcome(PracticeOutcome.repeated)
        entry = ledger_entry_from_assignment_outcome(event)

        assert entry.severity == PedagogicalEvidenceSeverity.warning

    def test_completed_is_informational(self) -> None:
        event = make_test_assignment_outcome(PracticeOutcome.completed)
        entry = ledger_entry_from_assignment_outcome(event)

        assert entry.severity == PedagogicalEvidenceSeverity.informational

    def test_provenance_includes_outcome_id(self) -> None:
        event = make_test_assignment_outcome()
        entry = ledger_entry_from_assignment_outcome(event)

        assert f"assignment_outcome:{event.id}" in entry.provenance


class TestLedgerEntryFromPracticeAssignment:
    """Tests for ledger_entry_from_practice_assignment."""

    def test_creates_single_entry(self) -> None:
        assignment = make_test_practice_assignment()
        entry = ledger_entry_from_practice_assignment(assignment)

        assert entry is not None
        assert entry.source == PedagogicalEvidenceSource.practice_assignment

    def test_always_informational(self) -> None:
        assignment = make_test_practice_assignment()
        entry = ledger_entry_from_practice_assignment(assignment)

        assert entry.severity == PedagogicalEvidenceSeverity.informational

    def test_provenance_includes_assignment_id(self) -> None:
        assignment = make_test_practice_assignment(assignment_id="pa_abc123")
        entry = ledger_entry_from_practice_assignment(assignment)

        assert "practice_assignment:pa_abc123" in entry.provenance

    def test_uses_provided_timestamp(self) -> None:
        assignment = make_test_practice_assignment()
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        entry = ledger_entry_from_practice_assignment(assignment, timestamp=ts)

        assert entry.timestamp == ts

    def test_title_includes_assignment_title(self) -> None:
        assignment = make_test_practice_assignment()
        entry = ledger_entry_from_practice_assignment(assignment)

        assert "Test Assignment" in entry.title


class TestLedgerEntryFromCurriculumRecommendation:
    """Tests for ledger_entry_from_curriculum_recommendation."""

    def test_creates_single_entry(self) -> None:
        rec = make_test_curriculum_recommendation()
        entry = ledger_entry_from_curriculum_recommendation(rec)

        assert entry is not None
        assert entry.source == PedagogicalEvidenceSource.curriculum_progression

    def test_always_informational(self) -> None:
        rec = make_test_curriculum_recommendation()
        entry = ledger_entry_from_curriculum_recommendation(rec)

        assert entry.severity == PedagogicalEvidenceSeverity.informational

    def test_provenance_is_composite(self) -> None:
        rec = make_test_curriculum_recommendation(
            content_id="timing_v1",
            diagnosis_code="timing_grid_deviation",
        )
        entry = ledger_entry_from_curriculum_recommendation(rec)

        assert "curriculum_recommendation:timing_grid_deviation:timing_v1" in entry.provenance

    def test_uses_provided_timestamp(self) -> None:
        rec = make_test_curriculum_recommendation()
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        entry = ledger_entry_from_curriculum_recommendation(rec, timestamp=ts)

        assert entry.timestamp == ts

    def test_uses_provided_student_id(self) -> None:
        rec = make_test_curriculum_recommendation()
        entry = ledger_entry_from_curriculum_recommendation(rec, student_id="student_xyz")

        assert entry.student_id == "student_xyz"


class TestBuildPedagogicalEvidenceLedger:
    """Tests for build_pedagogical_evidence_ledger."""

    def test_empty_inputs_returns_empty_ledger(self) -> None:
        ledger = build_pedagogical_evidence_ledger()

        assert len(ledger.entries) == 0

    def test_merges_all_sources(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
        ])
        queue_event = make_test_queue_event()
        outcome = make_test_assignment_outcome()

        ledger = build_pedagogical_evidence_ledger(
            runtime_reviews=[report],
            queue_events=[queue_event],
            assignment_outcomes=[outcome],
        )

        sources = {e.source for e in ledger.entries}
        assert PedagogicalEvidenceSource.runtime_review in sources
        assert PedagogicalEvidenceSource.queue_event in sources
        assert PedagogicalEvidenceSource.assignment_outcome in sources

    def test_sorts_by_timestamp(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=1)

        report1 = make_test_runtime_review_report(
            runtime_session_id="rts_new",
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=now,
        )
        report2 = make_test_runtime_review_report(
            runtime_session_id="rts_old",
            evaluation_codes=[DiagnosisCode.PITCH_DEVIATION],
            generated_at=old,
        )

        ledger = build_pedagogical_evidence_ledger(
            runtime_reviews=[report1, report2],
        )

        assert ledger.entries[0].timestamp < ledger.entries[1].timestamp

    def test_student_id_propagated(self) -> None:
        queue_event = make_test_queue_event()

        ledger = build_pedagogical_evidence_ledger(
            queue_events=[queue_event],
            student_id="student_xyz",
        )

        assert ledger.student_id == "student_xyz"
        assert ledger.entries[0].student_id == "student_xyz"


class TestBuildPedagogicalEvidenceSummary:
    """Tests for build_pedagogical_evidence_summary."""

    def test_empty_ledger(self) -> None:
        ledger = build_pedagogical_evidence_ledger()
        summary = build_pedagogical_evidence_summary(ledger)

        assert summary.total_entries == 0
        assert summary.latest_timestamp is None

    def test_counts_by_source(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
            DiagnosisCode.PITCH_DEVIATION,
        ])
        queue_event = make_test_queue_event()

        ledger = build_pedagogical_evidence_ledger(
            runtime_reviews=[report],
            queue_events=[queue_event],
        )
        summary = build_pedagogical_evidence_summary(ledger)

        assert summary.runtime_review_entries == 2
        assert summary.queue_entries == 1
        assert summary.total_entries == 3

    def test_diagnosis_counts_aggregated(self) -> None:
        report = make_test_runtime_review_report(evaluation_codes=[
            DiagnosisCode.TIMING_GRID_DEVIATION,
            DiagnosisCode.TIMING_GRID_DEVIATION,
        ])

        ledger = build_pedagogical_evidence_ledger(
            runtime_reviews=[report],
        )
        summary = build_pedagogical_evidence_summary(ledger)

        assert summary.diagnosis_counts["timing_grid_deviation"] == 2

    def test_latest_timestamp_found(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=1)

        report1 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=now,
        )
        report2 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.PITCH_DEVIATION],
            generated_at=old,
        )

        ledger = build_pedagogical_evidence_ledger(
            runtime_reviews=[report1, report2],
        )
        summary = build_pedagogical_evidence_summary(ledger)

        assert summary.latest_timestamp == now


class TestBuilderVersion:
    """Test builder version constant."""

    def test_version_defined(self) -> None:
        assert PEDAGOGICAL_LEDGER_BUILDER_VERSION == "0.1.0"
