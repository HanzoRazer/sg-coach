"""
Tests for Longitudinal Review Builder.

Sprint 28: Longitudinal Progress Review.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from sg_spec.schemas.action_mapping import ActionRecommendationSet, RecommendedAction
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
from sg_spec.schemas.longitudinal_review import (
    LongitudinalTrend,
    DiagnosisTrendSummary,
    OutcomeTrajectorySummary,
    LongitudinalProgressReview,
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
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
from sg_spec.schemas.user_feedback import PracticeOutcome

from sg_coach.longitudinal_review import (
    LONGITUDINAL_REVIEW_BUILDER_VERSION,
    build_diagnosis_trend_summary,
    build_outcome_trajectory_summary,
    build_longitudinal_progress_review,
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


def make_test_evaluation(
    session_id,
    codes: list[DiagnosisCode] | None = None,
) -> CoachEvaluation:
    """Create test evaluation with specified diagnosis codes."""
    codes = codes or []
    findings = [
        CoachFinding(
            id=f"finding_{i}",
            type="timing",
            code=code,
            severity=Severity.primary,
            interpretation=f"Finding {i} interpretation",
            message=f"Finding {i}",
        )
        for i, code in enumerate(codes)
    ]

    return CoachEvaluation(
        session_id=session_id,
        coach_version="test@0.1.0",
        findings=findings,
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Focus on timing accuracy",
        ),
        confidence=0.8,
    )


def make_test_runtime_session(
    runtime_session_id: str | None = None,
    evaluation_codes: list[DiagnosisCode] | None = None,
) -> RuntimePracticeSession:
    """Create test runtime session with optional evaluation."""
    session_id = uuid4()
    runtime_session_id = runtime_session_id or f"rts_{uuid4().hex[:12]}"

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
        started_at=datetime.now(timezone.utc),
        assignment=make_test_assignment(),
        evaluation=evaluation,
    )


def make_test_runtime_review_report(
    *,
    outcome: PracticeOutcome = PracticeOutcome.completed,
    evaluation_codes: list[DiagnosisCode] | None = None,
    generated_at: datetime | None = None,
) -> RuntimeReviewReport:
    """Create a RuntimeReviewReport for testing."""
    session = make_test_runtime_session(evaluation_codes=evaluation_codes)

    return RuntimeReviewReport(
        runtime_session_id=session.runtime_session_id,
        runtime_session=session,
        status=RuntimeReviewStatus.complete,
        evidence_summary=RuntimeEvidenceSummary(
            finding_count=len(evaluation_codes) if evaluation_codes else 0,
        ),
        outcome_summary=RuntimeOutcomeSummary(
            outcome=outcome,
        ),
        generated_at=generated_at or datetime.now(timezone.utc),
    )


class TestBuildDiagnosisTrendSummary:
    """Tests for build_diagnosis_trend_summary."""

    def test_empty_reports_returns_empty(self) -> None:
        result = build_diagnosis_trend_summary([])
        assert result == []

    def test_single_report_insufficient_data(self) -> None:
        report = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
        )
        result = build_diagnosis_trend_summary([report])

        assert len(result) == 1
        summary = result[0]
        assert summary.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert summary.total_occurrences == 1
        assert summary.trend == LongitudinalTrend.insufficient_data

    def test_two_reports_historical_recent_split(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=7)

        report1 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=old,
        )
        report2 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=now,
        )

        result = build_diagnosis_trend_summary([report1, report2])

        assert len(result) == 1
        summary = result[0]
        assert summary.historical_occurrence_count == 1
        assert summary.recent_occurrence_count == 1
        assert summary.trend == LongitudinalTrend.stable

    def test_improving_trend_detected(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [DiagnosisCode.TIMING_GRID_DEVIATION] if i < 2 else []
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_diagnosis_trend_summary(reports)

        timing_summary = next(
            s for s in result
            if s.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        )
        assert timing_summary.historical_occurrence_count == 2
        assert timing_summary.recent_occurrence_count == 0
        assert timing_summary.trend == LongitudinalTrend.improving
        assert timing_summary.improvement_ratio == 1.0

    def test_worsening_trend_detected(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [] if i < 2 else [DiagnosisCode.TIMING_GRID_DEVIATION]
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_diagnosis_trend_summary(reports)

        timing_summary = next(
            s for s in result
            if s.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        )
        assert timing_summary.historical_occurrence_count == 0
        assert timing_summary.recent_occurrence_count == 2
        assert timing_summary.trend == LongitudinalTrend.worsening
        assert timing_summary.improvement_ratio is None

    def test_stable_trend_detected(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            reports.append(make_test_runtime_review_report(
                evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_diagnosis_trend_summary(reports)

        timing_summary = next(
            s for s in result
            if s.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        )
        assert timing_summary.historical_occurrence_count == 2
        assert timing_summary.recent_occurrence_count == 2
        assert timing_summary.trend == LongitudinalTrend.stable

    def test_multiple_diagnosis_codes_tracked(self) -> None:
        now = datetime.now(timezone.utc)

        report1 = make_test_runtime_review_report(
            evaluation_codes=[
                DiagnosisCode.TIMING_GRID_DEVIATION,
                DiagnosisCode.PITCH_DEVIATION,
            ],
            generated_at=now - timedelta(days=1),
        )
        report2 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=now,
        )

        result = build_diagnosis_trend_summary([report1, report2])

        assert len(result) == 2
        codes = {s.diagnosis_code for s in result}
        assert DiagnosisCode.TIMING_GRID_DEVIATION in codes
        assert DiagnosisCode.PITCH_DEVIATION in codes

    def test_session_level_counting(self) -> None:
        """Same diagnosis code appearing twice in one session counts once."""
        now = datetime.now(timezone.utc)

        report = make_test_runtime_review_report(
            evaluation_codes=[
                DiagnosisCode.TIMING_GRID_DEVIATION,
                DiagnosisCode.TIMING_GRID_DEVIATION,
            ],
            generated_at=now,
        )

        result = build_diagnosis_trend_summary([report])

        assert len(result) == 1
        assert result[0].total_occurrences == 1

    def test_first_and_latest_occurrence_tracked(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=7)

        report1 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=old,
        )
        report2 = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
            generated_at=now,
        )

        result = build_diagnosis_trend_summary([report1, report2])

        summary = result[0]
        assert summary.first_occurrence_at == old
        assert summary.latest_occurrence_at == now

    def test_improvement_ratio_partial(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [DiagnosisCode.TIMING_GRID_DEVIATION] if i != 3 else []
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_diagnosis_trend_summary(reports)

        summary = result[0]
        assert summary.historical_occurrence_count == 2
        assert summary.recent_occurrence_count == 1
        assert summary.improvement_ratio == 0.5


class TestBuildOutcomeTrajectorySummary:
    """Tests for build_outcome_trajectory_summary."""

    def test_empty_reports_returns_defaults(self) -> None:
        result = build_outcome_trajectory_summary([])

        assert result.total_completed == 0
        assert result.total_improved == 0
        assert result.total_repeated == 0
        assert result.total_worsened == 0
        assert result.total_abandoned == 0
        assert result.completion_ratio is None
        assert result.improvement_ratio is None

    def test_counts_completed_outcomes(self) -> None:
        reports = [
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.improved),
        ]

        result = build_outcome_trajectory_summary(reports)

        assert result.total_completed == 2
        assert result.total_improved == 1

    def test_counts_all_outcome_types(self) -> None:
        reports = [
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.improved),
            make_test_runtime_review_report(outcome=PracticeOutcome.repeated),
            make_test_runtime_review_report(outcome=PracticeOutcome.worsened),
            make_test_runtime_review_report(outcome=PracticeOutcome.abandoned),
        ]

        result = build_outcome_trajectory_summary(reports)

        assert result.total_completed == 1
        assert result.total_improved == 1
        assert result.total_repeated == 1
        assert result.total_worsened == 1
        assert result.total_abandoned == 1

    def test_completion_ratio_calculated(self) -> None:
        reports = [
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.improved),
            make_test_runtime_review_report(outcome=PracticeOutcome.repeated),
            make_test_runtime_review_report(outcome=PracticeOutcome.abandoned),
        ]

        result = build_outcome_trajectory_summary(reports)

        assert result.completion_ratio == 0.5

    def test_improvement_ratio_calculated(self) -> None:
        reports = [
            make_test_runtime_review_report(outcome=PracticeOutcome.improved),
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
        ]

        result = build_outcome_trajectory_summary(reports)

        assert result.improvement_ratio == 0.25


class TestBuildLongitudinalProgressReview:
    """Tests for build_longitudinal_progress_review."""

    def test_empty_reports_returns_minimal(self) -> None:
        result = build_longitudinal_progress_review(reports=[])

        assert result.review_count == 0
        assert result.diagnosis_trends == []
        assert result.strongest_improvements == []
        assert result.recurring_challenges == []
        assert result.evidence_review_ids == []

    def test_student_id_set(self) -> None:
        result = build_longitudinal_progress_review(
            reports=[],
            student_id="student_123",
        )

        assert result.student_id == "student_123"

    def test_review_count_accurate(self) -> None:
        reports = [
            make_test_runtime_review_report(),
            make_test_runtime_review_report(),
            make_test_runtime_review_report(),
        ]

        result = build_longitudinal_progress_review(reports=reports)

        assert result.review_count == 3

    def test_evidence_review_ids_collected(self) -> None:
        reports = [
            make_test_runtime_review_report(),
            make_test_runtime_review_report(),
        ]

        result = build_longitudinal_progress_review(reports=reports)

        assert len(result.evidence_review_ids) == 2
        assert result.evidence_review_ids[0] == reports[0].runtime_session_id
        assert result.evidence_review_ids[1] == reports[1].runtime_session_id

    def test_strongest_improvements_identified(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [DiagnosisCode.TIMING_GRID_DEVIATION] if i < 2 else []
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_longitudinal_progress_review(reports=reports)

        assert "timing_grid_deviation" in result.strongest_improvements

    def test_recurring_challenges_identified(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            reports.append(make_test_runtime_review_report(
                evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_longitudinal_progress_review(reports=reports)

        assert "timing_grid_deviation" in result.recurring_challenges

    def test_notes_generated_for_improving(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [DiagnosisCode.TIMING_GRID_DEVIATION] if i < 2 else []
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result = build_longitudinal_progress_review(reports=reports)

        assert any("improving" in note.lower() for note in result.notes)

    def test_notes_insufficient_data_for_single_report(self) -> None:
        report = make_test_runtime_review_report(
            evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
        )

        result = build_longitudinal_progress_review(reports=[report])

        assert any("insufficient" in note.lower() for note in result.notes)

    def test_notes_deterministic(self) -> None:
        now = datetime.now(timezone.utc)

        reports = []
        for i in range(4):
            codes = [DiagnosisCode.TIMING_GRID_DEVIATION] if i < 2 else []
            reports.append(make_test_runtime_review_report(
                evaluation_codes=codes,
                generated_at=now - timedelta(days=4 - i),
            ))

        result1 = build_longitudinal_progress_review(reports=reports)
        result2 = build_longitudinal_progress_review(reports=reports)

        assert result1.notes == result2.notes

    def test_outcome_trajectory_included(self) -> None:
        reports = [
            make_test_runtime_review_report(outcome=PracticeOutcome.completed),
            make_test_runtime_review_report(outcome=PracticeOutcome.improved),
        ]

        result = build_longitudinal_progress_review(reports=reports)

        assert result.outcome_trajectory is not None
        assert result.outcome_trajectory.total_completed == 1
        assert result.outcome_trajectory.total_improved == 1

    def test_diagnosis_trends_included(self) -> None:
        now = datetime.now(timezone.utc)

        reports = [
            make_test_runtime_review_report(
                evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
                generated_at=now - timedelta(days=1),
            ),
            make_test_runtime_review_report(
                evaluation_codes=[DiagnosisCode.TIMING_GRID_DEVIATION],
                generated_at=now,
            ),
        ]

        result = build_longitudinal_progress_review(reports=reports)

        assert len(result.diagnosis_trends) == 1
        assert result.diagnosis_trends[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION


class TestBuilderVersion:
    """Test builder version constant."""

    def test_version_defined(self) -> None:
        assert LONGITUDINAL_REVIEW_BUILDER_VERSION == "0.1.0"
