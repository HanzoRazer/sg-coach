"""
Tests for Runtime Review Builder.

Sprint 27: Runtime Evidence Review Report.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sg_spec.schemas.action_mapping import ActionRecommendationSet, RecommendedAction
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeEvent
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    CoachFinding,
    DiagnosisCode,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    Severity,
)
from sg_spec.schemas.curriculum_progression import CurriculumRecommendation, ProgressionLevel
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.curriculum_progression import CurriculumProgressState
from sg_spec.schemas.outcome_integration import AssignmentOutcomeProcessingResult
from sg_spec.schemas.practice_queue import PracticeQueue
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.runtime_flow import (
    RuntimePracticeSession,
    RuntimeSessionResult,
    RuntimeSessionStatus,
)
from sg_spec.schemas.runtime_review import (
    RuntimeReviewStatus,
    RuntimeEvidenceSummary,
    RuntimeOutcomeSummary,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.runtime_review import (
    RUNTIME_REVIEW_BUILDER_VERSION,
    build_runtime_evidence_summary,
    build_runtime_outcome_summary,
    build_runtime_review_report,
)


def make_test_assignment(
    assignment_id: str = "pa_test123",
    diagnosis_code: str = "timing_grid_deviation",
) -> AssembledPracticeAssignment:
    """Create minimal test assignment."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        title="Test Assignment",
        assignment_type="drill",
        instructions="Practice this",
        diagnosis_code=diagnosis_code,
    )


def make_test_session_record(session_id=None) -> SessionRecord:
    """Create minimal test session record."""
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


def make_test_evaluation(session_id, finding_count: int = 0, recommendation_count: int = 0) -> CoachEvaluation:
    """Create test evaluation with specified finding/recommendation counts."""
    findings = [
        CoachFinding(
            id=f"finding_{i}",
            type="timing",
            code=DiagnosisCode.TIMING_GRID_DEVIATION,
            severity=Severity.primary,
            interpretation=f"Finding {i} interpretation",
            message=f"Finding {i}",
        )
        for i in range(finding_count)
    ]

    recommendations = None
    if recommendation_count > 0:
        actions = [
            RecommendedAction(
                action_type=FeedbackActionType.assign_drill,
                label=f"Action {i}",
            )
            for i in range(recommendation_count)
        ]
        recommendations = [
            ActionRecommendationSet(
                finding_code="timing_grid_deviation",
                actions=actions,
            )
        ]

    return CoachEvaluation(
        session_id=session_id,
        coach_version="test@0.1.0",
        findings=findings,
        recommendations=recommendations,
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Focus on timing accuracy",
        ),
        confidence=0.8,
    )


def make_test_runtime_session(
    runtime_session_id: str = "rts_test123",
    with_assignment: bool = True,
    with_session_record: bool = False,
    with_evaluation: bool = False,
    finding_count: int = 0,
    recommendation_count: int = 0,
) -> RuntimePracticeSession:
    """Create test runtime session with optional evidence."""
    session_id = uuid4()

    session_record = None
    evaluation = None

    if with_session_record:
        session_record = make_test_session_record(session_id)

    if with_evaluation:
        evaluation = make_test_evaluation(session_id, finding_count, recommendation_count)

    return RuntimePracticeSession(
        runtime_session_id=runtime_session_id,
        queue_id="queue_test123",
        scheduled_id="sq_test123",
        assignment_id="pa_test123",
        student_id="student_123",
        status=RuntimeSessionStatus.active,
        started_at=datetime.now(timezone.utc),
        assignment=make_test_assignment() if with_assignment else None,
        session_record=session_record,
        evaluation=evaluation,
    )


def make_test_runtime_result(
    processed: bool = True,
    queue_updated: bool = True,
    curriculum_advanced: bool = True,
    outcome: PracticeOutcome = PracticeOutcome.completed,
    next_content_id: str | None = "timing_advanced_v1",
    reasons: list[str] | None = None,
) -> RuntimeSessionResult:
    """Create test runtime session result."""
    outcome_event = AssignmentOutcomeEvent(
        id="aoe_test123",
        assignment_id="pa_test123",
        outcome=outcome,
        timestamp=datetime.now(timezone.utc),
    )

    curriculum_rec = None
    if next_content_id:
        curriculum_rec = CurriculumRecommendation(
            content_id=next_content_id,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            progression_level=ProgressionLevel.beginner,
            reason="Completed current level",
        )

    integration_result = AssignmentOutcomeProcessingResult(
        processed=processed,
        updated_queue=PracticeQueue(student_id="student_123"),
        updated_progress_state=CurriculumProgressState(student_id="student_123"),
        queue_event=None,
        advanced_curriculum=curriculum_advanced,
        curriculum_recommendation=curriculum_rec,
        reasons=reasons or [],
    )

    return RuntimeSessionResult(
        runtime_session_id="rts_test123",
        processed=processed,
        queue_updated=queue_updated,
        curriculum_advanced=curriculum_advanced,
        outcome_event=outcome_event,
        integration_result=integration_result,
        reasons=reasons or [],
    )


class TestBuildRuntimeEvidenceSummary:
    """Tests for build_runtime_evidence_summary function."""

    def test_no_evidence(self) -> None:
        session = make_test_runtime_session(
            with_session_record=False,
            with_evaluation=False,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.has_session_record is False
        assert summary.has_evaluation is False
        assert summary.finding_count == 0
        assert summary.recommendation_count == 0

    def test_with_session_record_only(self) -> None:
        session = make_test_runtime_session(
            with_session_record=True,
            with_evaluation=False,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.has_session_record is True
        assert summary.has_evaluation is False

    def test_with_evaluation_only(self) -> None:
        session = make_test_runtime_session(
            with_session_record=False,
            with_evaluation=True,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.has_session_record is False
        assert summary.has_evaluation is True

    def test_with_full_evidence(self) -> None:
        session = make_test_runtime_session(
            with_session_record=True,
            with_evaluation=True,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.has_session_record is True
        assert summary.has_evaluation is True

    def test_finding_count(self) -> None:
        session = make_test_runtime_session(
            with_evaluation=True,
            finding_count=5,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.finding_count == 5

    def test_recommendation_count(self) -> None:
        session = make_test_runtime_session(
            with_evaluation=True,
            recommendation_count=3,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.recommendation_count == 3

    def test_assignment_count_with_assignment(self) -> None:
        session = make_test_runtime_session(with_assignment=True)
        summary = build_runtime_evidence_summary(session)

        assert summary.assignment_count == 1

    def test_assignment_count_without_assignment(self) -> None:
        session = make_test_runtime_session(with_assignment=False)
        summary = build_runtime_evidence_summary(session)

        assert summary.assignment_count == 0

    def test_graceful_degradation_no_recommendations(self) -> None:
        session = make_test_runtime_session(
            with_evaluation=True,
            finding_count=2,
            recommendation_count=0,
        )
        summary = build_runtime_evidence_summary(session)

        assert summary.finding_count == 2
        assert summary.recommendation_count == 0


class TestBuildRuntimeOutcomeSummary:
    """Tests for build_runtime_outcome_summary function."""

    def test_none_result(self) -> None:
        summary = build_runtime_outcome_summary(None)

        assert summary.outcome is None
        assert summary.queue_updated is False
        assert summary.curriculum_advanced is False
        assert summary.next_curriculum_content_id is None
        assert summary.reasons == []

    def test_with_result(self) -> None:
        result = make_test_runtime_result()
        summary = build_runtime_outcome_summary(result)

        assert summary.outcome == PracticeOutcome.completed
        assert summary.queue_updated is True
        assert summary.curriculum_advanced is True
        assert summary.next_curriculum_content_id == "timing_advanced_v1"

    def test_extracts_curriculum_content_id(self) -> None:
        result = make_test_runtime_result(next_content_id="specific_content_v2")
        summary = build_runtime_outcome_summary(result)

        assert summary.next_curriculum_content_id == "specific_content_v2"

    def test_no_curriculum_recommendation(self) -> None:
        result = make_test_runtime_result(next_content_id=None)
        summary = build_runtime_outcome_summary(result)

        assert summary.next_curriculum_content_id is None

    def test_with_reasons(self) -> None:
        result = make_test_runtime_result(reasons=["reason_1", "reason_2"])
        summary = build_runtime_outcome_summary(result)

        assert summary.reasons == ["reason_1", "reason_2"]

    def test_worsened_outcome(self) -> None:
        result = make_test_runtime_result(
            outcome=PracticeOutcome.worsened,
            queue_updated=False,
            curriculum_advanced=False,
        )
        summary = build_runtime_outcome_summary(result)

        assert summary.outcome == PracticeOutcome.worsened
        assert summary.queue_updated is False
        assert summary.curriculum_advanced is False


class TestBuildRuntimeReviewReport:
    """Tests for build_runtime_review_report function."""

    def test_basic_report(self) -> None:
        session = make_test_runtime_session()
        report = build_runtime_review_report(runtime_session=session)

        assert report.runtime_session_id == "rts_test123"
        assert report.student_id == "student_123"
        assert report.assignment_id == "pa_test123"
        assert report.queue_id == "queue_test123"

    def test_embeds_runtime_session(self) -> None:
        session = make_test_runtime_session()
        report = build_runtime_review_report(runtime_session=session)

        assert report.runtime_session is session

    def test_status_complete_with_full_evidence(self) -> None:
        session = make_test_runtime_session(
            with_session_record=True,
            with_evaluation=True,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.status == RuntimeReviewStatus.complete

    def test_status_partial_with_session_record_only(self) -> None:
        session = make_test_runtime_session(
            with_session_record=True,
            with_evaluation=False,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.status == RuntimeReviewStatus.partial

    def test_status_partial_with_evaluation_only(self) -> None:
        session = make_test_runtime_session(
            with_session_record=False,
            with_evaluation=True,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.status == RuntimeReviewStatus.partial

    def test_status_missing_evidence_with_no_evidence(self) -> None:
        session = make_test_runtime_session(
            with_session_record=False,
            with_evaluation=False,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.status == RuntimeReviewStatus.missing_evidence

    def test_extracts_diagnosis_code(self) -> None:
        session = make_test_runtime_session()
        report = build_runtime_review_report(runtime_session=session)

        assert report.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION

    def test_missing_diagnosis_code_returns_none(self) -> None:
        assignment = AssembledPracticeAssignment(
            id="pa_test123",
            title="Test",
            assignment_type="drill",
            instructions="Test",
            diagnosis_code=None,
        )
        session = RuntimePracticeSession(
            runtime_session_id="rts_test123",
            queue_id="queue_test123",
            scheduled_id="sq_test123",
            assignment_id="pa_test123",
            student_id="student_123",
            status=RuntimeSessionStatus.active,
            started_at=datetime.now(timezone.utc),
            assignment=assignment,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.diagnosis_code is None

    def test_no_assignment_no_diagnosis_code(self) -> None:
        session = make_test_runtime_session(with_assignment=False)
        report = build_runtime_review_report(runtime_session=session)

        assert report.diagnosis_code is None

    def test_with_runtime_result(self) -> None:
        session = make_test_runtime_session()
        result = make_test_runtime_result()
        report = build_runtime_review_report(
            runtime_session=session,
            runtime_result=result,
        )

        assert report.outcome_summary.outcome == PracticeOutcome.completed
        assert report.outcome_summary.curriculum_advanced is True

    def test_without_runtime_result(self) -> None:
        session = make_test_runtime_session()
        report = build_runtime_review_report(runtime_session=session)

        assert report.outcome_summary.outcome is None
        assert report.outcome_summary.queue_updated is False

    def test_evidence_summary_populated(self) -> None:
        session = make_test_runtime_session(
            with_session_record=True,
            with_evaluation=True,
            finding_count=3,
            recommendation_count=5,
        )
        report = build_runtime_review_report(runtime_session=session)

        assert report.evidence_summary.has_session_record is True
        assert report.evidence_summary.has_evaluation is True
        assert report.evidence_summary.finding_count == 3
        assert report.evidence_summary.recommendation_count == 5

    def test_generated_at_populated(self) -> None:
        before = datetime.now(timezone.utc)
        session = make_test_runtime_session()
        report = build_runtime_review_report(runtime_session=session)
        after = datetime.now(timezone.utc)

        assert before <= report.generated_at <= after


class TestImmutability:
    """Test that report building doesn't mutate inputs."""

    def test_runtime_session_unchanged(self) -> None:
        session = make_test_runtime_session()
        original_id = session.runtime_session_id

        build_runtime_review_report(runtime_session=session)

        assert session.runtime_session_id == original_id

    def test_runtime_result_unchanged(self) -> None:
        session = make_test_runtime_session()
        result = make_test_runtime_result()
        original_processed = result.processed

        build_runtime_review_report(
            runtime_session=session,
            runtime_result=result,
        )

        assert result.processed == original_processed


class TestVersioning:
    """Test version constants."""

    def test_builder_version_exists(self) -> None:
        assert RUNTIME_REVIEW_BUILDER_VERSION == "0.1.0"
