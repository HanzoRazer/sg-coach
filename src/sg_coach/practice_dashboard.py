"""
Practice Dashboard Builder.

Sprint 17: Dashboard data layer for visualizing longitudinal practice progress.

The dashboard is read-only and does not mutate history or goals.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sg_spec.schemas.coach_finding import DiagnosisCode
from sg_spec.schemas.goal_tracking import GoalStatus, WeaknessTrend
from sg_spec.schemas.practice_assignment import PracticeAssignmentStatus
from sg_spec.schemas.practice_dashboard import (
    DashboardAssignmentSummary,
    DashboardGoalCard,
    DashboardMetricCard,
    DashboardPracticeFrequency,
    DashboardWeaknessTrend,
    PracticeDashboardData,
)

from .goal_tracking import build_weakness_progressions, generate_practice_goals
from .practice_history import PracticeHistoryQuery, PracticeHistoryStore
from .practice_review import build_practice_timeline, build_progress_summary


DASHBOARD_VERSION = "0.1"


def _get_entries(
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> list:
    """Get history entries with optional user filtering."""
    if user_id is not None:
        query = PracticeHistoryQuery(user_id=user_id)
        return history_store.query(query)
    return history_store.all()


def _compute_confidence(occurrence_count: int) -> float:
    """
    Compute confidence based on sample size.

    Returns min(1.0, occurrence_count / 10).
    """
    return min(1.0, occurrence_count / 10)


def _build_metrics(
    *,
    total_sessions: int,
    total_findings: int,
    total_assignments: int,
    active_goals: int,
    top_weakness: Optional[DiagnosisCode],
    top_weakness_count: int,
) -> list[DashboardMetricCard]:
    """
    Build the 5 standard metric cards in exact order.

    Order:
    1. Total Sessions
    2. Total Findings
    3. Total Assignments
    4. Active Goals
    5. Top Weakness
    """
    metrics = [
        DashboardMetricCard(
            label="Total Sessions",
            value=total_sessions,
        ),
        DashboardMetricCard(
            label="Total Findings",
            value=total_findings,
        ),
        DashboardMetricCard(
            label="Total Assignments",
            value=total_assignments,
        ),
        DashboardMetricCard(
            label="Active Goals",
            value=active_goals,
        ),
    ]

    if top_weakness is not None:
        metrics.append(
            DashboardMetricCard(
                label="Top Weakness",
                value=top_weakness.value,
                description=f"{top_weakness_count} occurrences",
            )
        )
    else:
        metrics.append(
            DashboardMetricCard(
                label="Top Weakness",
                value="None",
                description="No weaknesses detected",
            )
        )

    return metrics


def _build_weakness_trends(
    progressions: list,
    limit: int = 5,
) -> list[DashboardWeaknessTrend]:
    """
    Convert WeaknessProgressions to DashboardWeaknessTrends.

    Sorted by:
    - occurrence_count descending
    - diagnosis_code.value alphabetically ascending

    Limited to top N (default 5).
    """
    sorted_progressions = sorted(
        progressions,
        key=lambda p: (-p.occurrence_count, p.diagnosis_code.value),
    )

    trends = []
    for prog in sorted_progressions[:limit]:
        trends.append(
            DashboardWeaknessTrend(
                diagnosis_code=prog.diagnosis_code,
                occurrence_count=prog.occurrence_count,
                recent_occurrence_count=prog.recent_occurrence_count,
                trend=prog.trend,
                confidence=_compute_confidence(prog.occurrence_count),
            )
        )

    return trends


def _build_goal_cards(goals: list) -> list[DashboardGoalCard]:
    """
    Convert PracticeGoals to DashboardGoalCards.

    Includes: active, improving, regressed
    Excludes: completed, abandoned
    """
    cards = []
    included_statuses = {GoalStatus.active, GoalStatus.improving, GoalStatus.regressed}

    for goal in goals:
        if goal.status not in included_statuses:
            continue

        cards.append(
            DashboardGoalCard(
                goal_id=goal.id,
                title=goal.title,
                diagnosis_code=goal.diagnosis_code,
                status=goal.status,
                current_occurrence_count=goal.current_occurrence_count,
                target_occurrence_reduction=goal.target_occurrence_reduction,
            )
        )

    return cards


def _build_assignment_summary(
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> DashboardAssignmentSummary:
    """
    Build assignment summary by counting statuses from history.

    Counts ready and unresolved assignments.
    completed_count and abandoned_count are None in v1.
    """
    entries = _get_entries(history_store, user_id)

    total = 0
    ready = 0
    unresolved = 0

    for entry in entries:
        assignments_dict = entry.assignments
        if assignments_dict and "assignments" in assignments_dict:
            for assignment in assignments_dict["assignments"]:
                total += 1
                status = assignment.get("status")
                if status == PracticeAssignmentStatus.ready.value:
                    ready += 1
                elif status == PracticeAssignmentStatus.unresolved.value:
                    unresolved += 1

    return DashboardAssignmentSummary(
        total_assignments=total,
        ready_count=ready,
        unresolved_count=unresolved,
        completed_count=None,
        abandoned_count=None,
    )


def _build_practice_frequency(
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> DashboardPracticeFrequency:
    """
    Build practice frequency statistics.

    Uses UTC dates for active_days calculation.
    """
    entries = _get_entries(history_store, user_id)

    if not entries:
        return DashboardPracticeFrequency(
            session_count=0,
            active_days=0,
            first_session_at=None,
            last_session_at=None,
        )

    session_count = len(entries)

    timestamps = [e.timestamp for e in entries if e.timestamp]

    if not timestamps:
        return DashboardPracticeFrequency(
            session_count=session_count,
            active_days=0,
            first_session_at=None,
            last_session_at=None,
        )

    sorted_timestamps = sorted(timestamps)
    first_session_at = sorted_timestamps[0]
    last_session_at = sorted_timestamps[-1]

    unique_dates = set()
    for ts in timestamps:
        unique_dates.add(ts.date())

    active_days = len(unique_dates)

    return DashboardPracticeFrequency(
        session_count=session_count,
        active_days=active_days,
        first_session_at=first_session_at,
        last_session_at=last_session_at,
    )


def build_practice_dashboard(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> PracticeDashboardData:
    """
    Build complete dashboard data from practice history.

    Parameters
    ----------
    history_store:
        The practice history store to read from.
    user_id:
        Optional user ID to filter all sections.

    Returns
    -------
    PracticeDashboardData with all sections populated.

    Notes
    -----
    This is read-only. It does not mutate history or goals.
    All data is derived from existing history entries.
    """
    timeline = build_practice_timeline(
        history_store=history_store,
        user_id=user_id,
    )

    progress = build_progress_summary(
        history_store=history_store,
        user_id=user_id,
    )

    progressions = build_weakness_progressions(
        history_store=history_store,
        user_id=user_id,
    )

    goals = generate_practice_goals(progressions=progressions)

    total_sessions = timeline.total_sessions
    total_findings = progress.total_findings
    total_assignments = progress.total_assignments

    active_goal_statuses = {GoalStatus.active, GoalStatus.improving, GoalStatus.regressed}
    active_goals = sum(1 for g in goals if g.status in active_goal_statuses)

    top_weakness = None
    top_weakness_count = 0
    if progressions:
        sorted_progs = sorted(
            progressions,
            key=lambda p: (-p.occurrence_count, p.diagnosis_code.value),
        )
        top_weakness = sorted_progs[0].diagnosis_code
        top_weakness_count = sorted_progs[0].occurrence_count

    metrics = _build_metrics(
        total_sessions=total_sessions,
        total_findings=total_findings,
        total_assignments=total_assignments,
        active_goals=active_goals,
        top_weakness=top_weakness,
        top_weakness_count=top_weakness_count,
    )

    weakness_trends = _build_weakness_trends(progressions, limit=5)

    goal_cards = _build_goal_cards(goals)

    assignment_summary = _build_assignment_summary(
        history_store=history_store,
        user_id=user_id,
    )

    practice_frequency = _build_practice_frequency(
        history_store=history_store,
        user_id=user_id,
    )

    return PracticeDashboardData(
        user_id=user_id,
        metrics=metrics,
        weakness_trends=weakness_trends,
        goals=goal_cards,
        assignment_summary=assignment_summary,
        practice_frequency=practice_frequency,
        generated_at=datetime.now(timezone.utc),
        version=DASHBOARD_VERSION,
    )


__all__ = [
    "DASHBOARD_VERSION",
    "build_practice_dashboard",
]
