"""
Tests for Goal Tracking builders.

Sprint 13: Tests for weakness progression, goal generation, and status updates.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from sg_coach.practice_history import (
    PracticeHistoryStore,
)
from sg_coach.goal_tracking import (
    build_weakness_progressions,
    generate_practice_goals,
    build_goal_progress_summary,
    update_goal_status,
    _group_findings_by_code,
    _compute_trend,
    _most_common_severity,
    _goal_title_for_code,
    _goal_description_for_code,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    CoachFinding,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    Severity,
)
from sg_spec.schemas.goal_tracking import (
    GoalStatus,
    PracticeGoal,
    WeaknessProgression,
    WeaknessTrend,
)
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)


def make_session(session_id=None, instrument_id="guitar_1") -> SessionRecord:
    """Helper to create test session."""
    return SessionRecord(
        session_id=session_id or uuid4(),
        instrument_id=instrument_id,
        engine_version="test@1.0.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test_prog"),
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
    session_id=None,
    findings: list[CoachFinding] | None = None,
) -> CoachEvaluation:
    """Helper to create test evaluation."""
    return CoachEvaluation(
        session_id=session_id or uuid4(),
        coach_version="test@1.0.0",
        findings=findings or [],
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Practice timing accuracy",
        ),
        confidence=0.8,
    )


def make_finding(
    finding_type: str = "timing",
    code: DiagnosisCode | None = None,
    severity: Severity = Severity.primary,
) -> CoachFinding:
    """Helper to create test finding."""
    return CoachFinding(
        type=finding_type,
        severity=severity,
        interpretation="Test finding",
        code=code,
    )


def make_assignments(count: int = 1) -> AssembledPracticeAssignmentSet:
    """Helper to create test assignment set."""
    assignments = [
        AssembledPracticeAssignment(
            id=f"pa_test{i:06d}",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready,
            title=f"Test Drill {i}",
            instructions="Practice this drill",
        )
        for i in range(count)
    ]
    return AssembledPracticeAssignmentSet(assignments=assignments)


def populate_store_with_findings(
    store: PracticeHistoryStore,
    count: int = 1,
    user_id: str | None = None,
    codes: list[DiagnosisCode] | None = None,
) -> list[str]:
    """Populate store with sessions containing specific findings."""
    session_ids = []
    codes = codes or [DiagnosisCode.TIMING_GRID_DEVIATION]

    for i in range(count):
        session = make_session()
        findings = [
            make_finding("timing", code=code)
            for code in codes
        ]
        evaluation = make_evaluation(session.session_id, findings=findings)
        assignments = make_assignments(1)

        entry = store.append_session(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id=user_id,
        )
        session_ids.append(entry.session_id)

    return session_ids


class TestComputeTrend:
    """Test _compute_trend helper."""

    def test_stable_when_no_history(self):
        result = _compute_trend(occurrence_count=1, recent_occurrence_count=1)
        assert result == WeaknessTrend.stable

    def test_worsening_recent_equals_older(self):
        result = _compute_trend(occurrence_count=6, recent_occurrence_count=3)
        assert result == WeaknessTrend.worsening

    def test_worsening_recent_exceeds_older(self):
        result = _compute_trend(occurrence_count=10, recent_occurrence_count=7)
        assert result == WeaknessTrend.worsening

    def test_improving_recent_less_than_older(self):
        result = _compute_trend(occurrence_count=10, recent_occurrence_count=2)
        assert result == WeaknessTrend.improving

    def test_recurring_multiple_recent(self):
        result = _compute_trend(occurrence_count=2, recent_occurrence_count=2)
        assert result == WeaknessTrend.recurring

    def test_stable_single_occurrence(self):
        result = _compute_trend(occurrence_count=1, recent_occurrence_count=1)
        assert result == WeaknessTrend.stable

    def test_priority_worsening_over_recurring(self):
        result = _compute_trend(occurrence_count=4, recent_occurrence_count=2)
        assert result == WeaknessTrend.worsening


class TestMostCommonSeverity:
    """Test _most_common_severity helper."""

    def test_empty_list(self):
        result = _most_common_severity([])
        assert result is None

    def test_single_severity(self):
        result = _most_common_severity(["primary"])
        assert result == "primary"

    def test_most_common_wins(self):
        result = _most_common_severity(["primary", "secondary", "secondary"])
        assert result == "secondary"

    def test_tie_goes_to_more_severe(self):
        result = _most_common_severity(["primary", "secondary"])
        assert result == "primary"

    def test_tie_primary_beats_info(self):
        result = _most_common_severity(["info", "primary"])
        assert result == "primary"


class TestGoalTitleForCode:
    """Test _goal_title_for_code helper."""

    def test_known_code_timing(self):
        result = _goal_title_for_code(DiagnosisCode.TIMING_GRID_DEVIATION)
        assert result == "Reduce timing grid deviations"

    def test_known_code_dim_orbit(self):
        result = _goal_title_for_code(DiagnosisCode.DIM_ORBIT_VIOLATION)
        assert result == "Stabilize diminished orbit navigation"

    def test_known_code_wrong_note(self):
        result = _goal_title_for_code(DiagnosisCode.WRONG_NOTE)
        assert result == "Improve pitch accuracy"

    def test_known_code_pitch_deviation(self):
        result = _goal_title_for_code(DiagnosisCode.PITCH_DEVIATION)
        assert result == "Reduce pitch deviations"


class TestGoalDescriptionForCode:
    """Test _goal_description_for_code helper."""

    def test_known_code_has_description(self):
        result = _goal_description_for_code(DiagnosisCode.TIMING_GRID_DEVIATION)
        assert "timing" in result.lower()

    def test_known_code_dim_orbit_has_description(self):
        result = _goal_description_for_code(DiagnosisCode.DIM_ORBIT_VIOLATION)
        assert "diminished" in result.lower()


class TestBuildWeaknessProgressions:
    """Test build_weakness_progressions function."""

    def test_empty_store(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        result = build_weakness_progressions(history_store=store)
        assert result == []

    def test_single_session_single_finding(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=1, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert len(result) == 1
        assert result[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result[0].occurrence_count == 1

    def test_multiple_sessions_same_finding(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=5, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert len(result) == 1
        assert result[0].occurrence_count == 5

    def test_multiple_different_findings(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=3,
            codes=[DiagnosisCode.TIMING_GRID_DEVIATION, DiagnosisCode.WRONG_NOTE]
        )

        result = build_weakness_progressions(history_store=store)
        assert len(result) == 2
        total_occurrences = sum(p.occurrence_count for p in result)
        assert total_occurrences == 6

    def test_tracks_related_session_ids(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        session_ids = populate_store_with_findings(
            store, count=3, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert len(result[0].related_session_ids) == 3
        for sid in session_ids:
            assert sid in result[0].related_session_ids

    def test_computes_recent_occurrence_count(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=15, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(
            history_store=store, recent_session_limit=10
        )
        assert result[0].occurrence_count == 15
        assert result[0].recent_occurrence_count == 10

    def test_computes_trend_recurring(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=2, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert result[0].trend == WeaknessTrend.recurring

    def test_computes_trend_improving(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=20, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(
            history_store=store, recent_session_limit=5
        )
        assert result[0].trend == WeaknessTrend.improving

    def test_computes_confidence(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=5, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert result[0].confidence == 0.5

    def test_confidence_caps_at_one(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=15, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert result[0].confidence == 1.0

    def test_filters_by_user_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=3, user_id="user_a",
            codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )
        populate_store_with_findings(
            store, count=5, user_id="user_b",
            codes=[DiagnosisCode.WRONG_NOTE]
        )

        result = build_weakness_progressions(history_store=store, user_id="user_a")
        assert len(result) == 1
        assert result[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result[0].occurrence_count == 3

    def test_sorted_by_occurrence_count(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(
            store, count=2, codes=[DiagnosisCode.WRONG_NOTE]
        )
        populate_store_with_findings(
            store, count=5, codes=[DiagnosisCode.TIMING_GRID_DEVIATION]
        )

        result = build_weakness_progressions(history_store=store)
        assert result[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result[1].diagnosis_code == DiagnosisCode.WRONG_NOTE

    def test_does_not_mutate_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store_with_findings(store, count=3)

        entries_before = store.all()
        build_weakness_progressions(history_store=store)
        entries_after = store.all()

        assert len(entries_before) == len(entries_after)


class TestGeneratePracticeGoals:
    """Test generate_practice_goals function."""

    def test_empty_progressions(self):
        result = generate_practice_goals(progressions=[])
        assert result == []

    def test_below_threshold_no_goal(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=2,
            recent_occurrence_count=2,
        )
        result = generate_practice_goals(
            progressions=[progression], min_occurrence_threshold=3
        )
        assert result == []

    def test_at_threshold_creates_goal(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=3,
            recent_occurrence_count=2,
        )
        result = generate_practice_goals(
            progressions=[progression], min_occurrence_threshold=3
        )
        assert len(result) == 1

    def test_goal_id_deterministic(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].id == "goal_timing_grid_deviation"

    def test_goal_title_deterministic(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].title == "Reduce timing grid deviations"

    def test_goal_description_set(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
        )
        result = generate_practice_goals(progressions=[progression])
        assert len(result[0].description) > 0

    def test_goal_status_active(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].status == GoalStatus.active

    def test_target_occurrence_reduction_set(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=10,
            recent_occurrence_count=3,
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].target_occurrence_reduction == 10

    def test_current_occurrence_count_set(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=10,
            recent_occurrence_count=3,
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].current_occurrence_count == 3

    def test_related_session_ids_copied(self):
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            related_session_ids=["sess_1", "sess_2"],
        )
        result = generate_practice_goals(progressions=[progression])
        assert result[0].related_session_ids == ["sess_1", "sess_2"]

    def test_multiple_progressions_multiple_goals(self):
        progressions = [
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                occurrence_count=5,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                occurrence_count=4,
            ),
        ]
        result = generate_practice_goals(progressions=progressions)
        assert len(result) == 2


class TestUpdateGoalStatus:
    """Test update_goal_status function."""

    def test_completed_when_zero_recent(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            status=GoalStatus.active,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            recent_occurrence_count=0,
            trend=WeaknessTrend.stable,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.status == GoalStatus.completed

    def test_improving_when_trend_improving(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            status=GoalStatus.active,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=10,
            recent_occurrence_count=2,
            trend=WeaknessTrend.improving,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.status == GoalStatus.improving

    def test_regressed_when_trend_worsening(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            status=GoalStatus.active,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=10,
            recent_occurrence_count=7,
            trend=WeaknessTrend.worsening,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.status == GoalStatus.regressed

    def test_active_when_recurring(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            status=GoalStatus.improving,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=2,
            recent_occurrence_count=2,
            trend=WeaknessTrend.recurring,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.status == GoalStatus.active

    def test_does_not_mutate_original(self):
        original_status = GoalStatus.active
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            status=original_status,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            recent_occurrence_count=0,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert goal.status == original_status
        assert result.status == GoalStatus.completed
        assert result is not goal

    def test_updates_current_occurrence_count(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            current_occurrence_count=5,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=10,
            recent_occurrence_count=2,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.current_occurrence_count == 2

    def test_updates_related_session_ids(self):
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            related_session_ids=["sess_1"],
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            recent_occurrence_count=2,
            related_session_ids=["sess_1", "sess_2", "sess_3"],
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.related_session_ids == ["sess_1", "sess_2", "sess_3"]

    def test_preserves_created_at(self):
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            created_at=created,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            recent_occurrence_count=2,
        )
        result = update_goal_status(goal=goal, progression=progression)
        assert result.created_at == created

    def test_updates_updated_at(self):
        old_updated = datetime(2026, 1, 1, tzinfo=timezone.utc)
        goal = PracticeGoal(
            id="goal_timing_grid_deviation",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test goal",
            description="Test description",
            updated_at=old_updated,
        )
        progression = WeaknessProgression(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            occurrence_count=5,
            recent_occurrence_count=2,
        )
        before = datetime.now(timezone.utc)
        result = update_goal_status(goal=goal, progression=progression)
        after = datetime.now(timezone.utc)
        assert before <= result.updated_at <= after


class TestBuildGoalProgressSummary:
    """Test build_goal_progress_summary function."""

    def test_empty_goals(self):
        result = build_goal_progress_summary(goals=[])
        assert result.active_goal_count == 0
        assert result.completed_goal_count == 0
        assert result.goals_by_status == {}

    def test_counts_active_goals(self):
        goals = [
            PracticeGoal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                title="Goal 1",
                description="Desc 1",
                status=GoalStatus.active,
            ),
            PracticeGoal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                title="Goal 2",
                description="Desc 2",
                status=GoalStatus.active,
            ),
        ]
        result = build_goal_progress_summary(goals=goals)
        assert result.active_goal_count == 2

    def test_counts_completed_goals(self):
        goals = [
            PracticeGoal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                title="Goal 1",
                description="Desc 1",
                status=GoalStatus.completed,
            ),
            PracticeGoal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                title="Goal 2",
                description="Desc 2",
                status=GoalStatus.active,
            ),
        ]
        result = build_goal_progress_summary(goals=goals)
        assert result.completed_goal_count == 1
        assert result.active_goal_count == 1

    def test_goals_by_status(self):
        goals = [
            PracticeGoal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                title="Goal 1",
                description="Desc 1",
                status=GoalStatus.active,
            ),
            PracticeGoal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                title="Goal 2",
                description="Desc 2",
                status=GoalStatus.improving,
            ),
            PracticeGoal(
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                title="Goal 3",
                description="Desc 3",
                status=GoalStatus.improving,
            ),
        ]
        result = build_goal_progress_summary(goals=goals)
        assert result.goals_by_status["active"] == 1
        assert result.goals_by_status["improving"] == 2

    def test_top_weaknesses_from_progressions(self):
        progressions = [
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                occurrence_count=10,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                occurrence_count=5,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                occurrence_count=3,
            ),
        ]
        result = build_goal_progress_summary(goals=[], progressions=progressions)
        assert len(result.top_weaknesses) == 3
        assert result.top_weaknesses[0] == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result.top_weaknesses[1] == DiagnosisCode.WRONG_NOTE
        assert result.top_weaknesses[2] == DiagnosisCode.PITCH_DEVIATION

    def test_top_weaknesses_limited_to_three(self):
        progressions = [
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                occurrence_count=10,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                occurrence_count=8,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
                occurrence_count=6,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
                occurrence_count=4,
            ),
        ]
        result = build_goal_progress_summary(goals=[], progressions=progressions)
        assert len(result.top_weaknesses) == 3

    def test_top_weaknesses_sorted_by_occurrence(self):
        progressions = [
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                occurrence_count=3,
            ),
            WeaknessProgression(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                occurrence_count=10,
            ),
        ]
        result = build_goal_progress_summary(goals=[], progressions=progressions)
        assert result.top_weaknesses[0] == DiagnosisCode.TIMING_GRID_DEVIATION

    def test_no_progressions_empty_top_weaknesses(self):
        goals = [
            PracticeGoal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                title="Goal 1",
                description="Desc 1",
            ),
        ]
        result = build_goal_progress_summary(goals=goals, progressions=None)
        assert result.top_weaknesses == []


class TestSchemaExports:
    """Test that goal tracking functions are exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            build_weakness_progressions,
            generate_practice_goals,
            build_goal_progress_summary,
            update_goal_status,
        )
        assert build_weakness_progressions is not None
        assert generate_practice_goals is not None
        assert build_goal_progress_summary is not None
        assert update_goal_status is not None
