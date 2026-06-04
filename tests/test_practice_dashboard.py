"""
Tests for Practice Dashboard Builder.

Sprint 17: Dashboard data layer.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from sg_spec.schemas.coach_finding import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachEvaluation, CoachFinding, FocusRecommendation, Severity
from sg_spec.schemas.goal_tracking import GoalStatus, WeaknessTrend
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.practice_dashboard import (
    DashboardAssignmentSummary,
    DashboardGoalCard,
    DashboardMetricCard,
    DashboardPracticeFrequency,
    DashboardWeaknessTrend,
    PracticeDashboardData,
)

from sg_coach.practice_dashboard import (
    DASHBOARD_VERSION,
    build_practice_dashboard,
)
from sg_coach.practice_history import PracticeHistoryStore
from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    ProgramRef,
    ProgramType,
    PerformanceSummary,
)


def make_session(session_id: str | None = None) -> SessionRecord:
    """Create minimal session for testing."""
    return SessionRecord(
        session_id=session_id or str(uuid4()),
        instrument_id="guitar_1",
        engine_version="test@1.0.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test"),
        timing=SessionTiming(bpm=120.0, grid=8),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=16,
            notes_played=14,
            notes_dropped=2,
        ),
    )


def make_evaluation(
    findings: list[CoachFinding] | None = None,
) -> CoachEvaluation:
    """Create minimal evaluation for testing."""
    return CoachEvaluation(
        session_id=uuid4(),
        coach_version="test@1.0.0",
        findings=findings or [],
        focus_recommendation=FocusRecommendation(
            concept="Practice",
            reason="Continue practicing to improve",
        ),
        confidence=0.8,
    )


def make_finding(
    code: DiagnosisCode,
    severity: Severity = Severity.secondary,
) -> CoachFinding:
    """Create minimal finding for testing."""
    return CoachFinding(
        type="timing",
        severity=severity,
        code=code,
        interpretation="Test finding interpretation",
    )


def make_assignments(
    statuses: list[PracticeAssignmentStatus] | None = None,
) -> AssembledPracticeAssignmentSet:
    """Create assignment set with given statuses."""
    if statuses is None:
        statuses = [PracticeAssignmentStatus.ready]

    assignments = []
    for i, status in enumerate(statuses):
        assignments.append(
            AssembledPracticeAssignment(
                assignment_type=PracticeAssignmentType.drill,
                status=status,
                title=f"Assignment {i}",
                instructions="Test instructions",
            )
        )

    return AssembledPracticeAssignmentSet(assignments=assignments)


class TestBuildPracticeDashboard:
    """Test build_practice_dashboard function."""

    def test_returns_practice_dashboard_data(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        dashboard = build_practice_dashboard(history_store=store)
        assert isinstance(dashboard, PracticeDashboardData)

    def test_handles_empty_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        dashboard = build_practice_dashboard(history_store=store)

        assert dashboard.user_id is None
        assert len(dashboard.metrics) == 5
        assert dashboard.metrics[0].value == 0  # Total Sessions
        assert dashboard.weakness_trends == []
        assert dashboard.goals == []
        assert dashboard.assignment_summary.total_assignments == 0
        assert dashboard.practice_frequency.session_count == 0

    def test_filters_by_user_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments(),
            user_id="user_a",
        )
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments(),
            user_id="user_b",
        )

        dashboard = build_practice_dashboard(
            history_store=store,
            user_id="user_a",
        )

        assert dashboard.user_id == "user_a"
        assert dashboard.metrics[0].value == 1  # Total Sessions for user_a

    def test_generated_at_is_set(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        before = datetime.now(timezone.utc)
        dashboard = build_practice_dashboard(history_store=store)
        after = datetime.now(timezone.utc)
        assert before <= dashboard.generated_at <= after

    def test_version_is_set(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.version == DASHBOARD_VERSION

    def test_does_not_mutate_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments(),
        )

        entries_before = list(store.all())
        build_practice_dashboard(history_store=store)
        entries_after = list(store.all())

        assert len(entries_before) == len(entries_after)


class TestMetrics:
    """Test metric card generation."""

    def test_metrics_include_total_sessions(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        for _ in range(3):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        session_metric = next(m for m in dashboard.metrics if m.label == "Total Sessions")
        assert session_metric.value == 3

    def test_metrics_include_total_findings(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(findings=[
                make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                make_finding(DiagnosisCode.WRONG_NOTE),
            ]),
            assignments=make_assignments(),
        )

        dashboard = build_practice_dashboard(history_store=store)

        findings_metric = next(m for m in dashboard.metrics if m.label == "Total Findings")
        assert findings_metric.value == 2

    def test_metrics_include_total_assignments(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments([
                PracticeAssignmentStatus.ready,
                PracticeAssignmentStatus.ready,
                PracticeAssignmentStatus.unresolved,
            ]),
        )

        dashboard = build_practice_dashboard(history_store=store)

        assignments_metric = next(m for m in dashboard.metrics if m.label == "Total Assignments")
        assert assignments_metric.value == 3

    def test_metrics_include_active_goals(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        goals_metric = next(m for m in dashboard.metrics if m.label == "Active Goals")
        assert goals_metric.value >= 1

    def test_metrics_include_top_weakness(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        for _ in range(3):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        weakness_metric = next(m for m in dashboard.metrics if m.label == "Top Weakness")
        assert weakness_metric.value == "timing_grid_deviation"
        assert "3 occurrences" in weakness_metric.description

    def test_metrics_order(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        dashboard = build_practice_dashboard(history_store=store)

        labels = [m.label for m in dashboard.metrics]
        assert labels == [
            "Total Sessions",
            "Total Findings",
            "Total Assignments",
            "Active Goals",
            "Top Weakness",
        ]


class TestWeaknessTrends:
    """Test weakness trend generation."""

    def test_weakness_trends_are_sorted(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )
        for _ in range(3):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.WRONG_NOTE),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        if len(dashboard.weakness_trends) >= 2:
            assert dashboard.weakness_trends[0].occurrence_count >= dashboard.weakness_trends[1].occurrence_count

    def test_weakness_trends_limited_to_top_5(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        codes = [
            DiagnosisCode.TIMING_GRID_DEVIATION,
            DiagnosisCode.WRONG_NOTE,
            DiagnosisCode.PITCH_DEVIATION,
            DiagnosisCode.DIM_ORBIT_VIOLATION,
            DiagnosisCode.RUSHING,
            DiagnosisCode.DRAGGING,
        ]

        for code in codes:
            for _ in range(3):
                store.append_session(
                    session=make_session(),
                    evaluation=make_evaluation(findings=[make_finding(code)]),
                    assignments=make_assignments(),
                )

        dashboard = build_practice_dashboard(history_store=store)
        assert len(dashboard.weakness_trends) <= 5

    def test_weakness_trend_confidence(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        if dashboard.weakness_trends:
            trend = dashboard.weakness_trends[0]
            assert 0.0 <= trend.confidence <= 1.0
            assert trend.confidence == min(1.0, trend.occurrence_count / 10)


class TestGoals:
    """Test goal card generation."""

    def test_goals_exclude_completed(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        for goal in dashboard.goals:
            assert goal.status != GoalStatus.completed
            assert goal.status != GoalStatus.abandoned

    def test_goals_include_active(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(findings=[
                    make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
                ]),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)

        if dashboard.goals:
            statuses = {g.status for g in dashboard.goals}
            assert GoalStatus.completed not in statuses
            assert GoalStatus.abandoned not in statuses


class TestAssignmentSummary:
    """Test assignment summary generation."""

    def test_assignment_summary_counts_ready(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments([
                PracticeAssignmentStatus.ready,
                PracticeAssignmentStatus.ready,
            ]),
        )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.assignment_summary.ready_count == 2

    def test_assignment_summary_counts_unresolved(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments([
                PracticeAssignmentStatus.unresolved,
                PracticeAssignmentStatus.unresolved,
                PracticeAssignmentStatus.ready,
            ]),
        )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.assignment_summary.unresolved_count == 2
        assert dashboard.assignment_summary.ready_count == 1

    def test_assignment_summary_completed_is_none(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments(),
        )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.assignment_summary.completed_count is None
        assert dashboard.assignment_summary.abandoned_count is None


class TestPracticeFrequency:
    """Test practice frequency generation."""

    def test_practice_frequency_counts_sessions(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        for _ in range(5):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.practice_frequency.session_count == 5

    def test_practice_frequency_counts_active_days(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(3):
            store.append_session(
                session=make_session(),
                evaluation=make_evaluation(),
                assignments=make_assignments(),
            )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.practice_frequency.active_days >= 1

    def test_practice_frequency_finds_first_last(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(),
            assignments=make_assignments(),
        )

        dashboard = build_practice_dashboard(history_store=store)
        assert dashboard.practice_frequency.first_session_at is not None
        assert dashboard.practice_frequency.last_session_at is not None
        assert dashboard.practice_frequency.first_session_at <= dashboard.practice_frequency.last_session_at

    def test_practice_frequency_empty_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        dashboard = build_practice_dashboard(history_store=store)

        assert dashboard.practice_frequency.session_count == 0
        assert dashboard.practice_frequency.active_days == 0
        assert dashboard.practice_frequency.first_session_at is None
        assert dashboard.practice_frequency.last_session_at is None


class TestSerialization:
    """Test dashboard serialization."""

    def test_dashboard_serializes_to_json(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        store.append_session(
            session=make_session(),
            evaluation=make_evaluation(findings=[
                make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
            ]),
            assignments=make_assignments(),
        )

        dashboard = build_practice_dashboard(history_store=store)
        data = dashboard.model_dump(mode="json")

        assert isinstance(data, dict)
        assert "metrics" in data
        assert "weakness_trends" in data
        assert "goals" in data
        assert "assignment_summary" in data
        assert "practice_frequency" in data
        assert "generated_at" in data
