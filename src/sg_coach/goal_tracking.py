"""
Goal Tracking — Weakness progression analysis and goal generation.

Sprint 13: Longitudinal coaching intelligence layer.

This module provides:
- build_weakness_progressions(): Analyze findings over time
- generate_practice_goals(): Create goals from repeated weaknesses
- build_goal_progress_summary(): Aggregate goal status overview
- update_goal_status(): Update goal based on progression

Core rules:
- Goals are deterministic and explainable
- Goals derive from repeated findings, not raw note events
- Goal tracking must not mutate history
- Goal progression is heuristic-driven in v1

Ownership: sg-coach (builders)
Schemas: sg-spec (WeaknessProgression, PracticeGoal, GoalProgressSummary)
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachEvaluation
from sg_spec.schemas.goal_tracking import (
    GoalProgressSummary,
    GoalStatus,
    PracticeGoal,
    WeaknessProgression,
    WeaknessTrend,
)

from .practice_history import PracticeHistoryEntry, PracticeHistoryStore


GOAL_TITLES: Dict[DiagnosisCode, str] = {
    DiagnosisCode.DIM_ORBIT_VIOLATION: "Stabilize diminished orbit navigation",
    DiagnosisCode.TIMING_GRID_DEVIATION: "Reduce timing grid deviations",
    DiagnosisCode.WRONG_NOTE: "Improve pitch accuracy",
    DiagnosisCode.PITCH_DEVIATION: "Reduce pitch deviations",
}

GOAL_DESCRIPTIONS: Dict[DiagnosisCode, str] = {
    DiagnosisCode.DIM_ORBIT_VIOLATION: (
        "Practice exercises that reinforce diminished chord navigation patterns."
    ),
    DiagnosisCode.TIMING_GRID_DEVIATION: (
        "Focus on exercises that target timing accuracy and grid alignment."
    ),
    DiagnosisCode.WRONG_NOTE: (
        "Work on exercises that improve note selection and pitch recognition."
    ),
    DiagnosisCode.PITCH_DEVIATION: (
        "Practice intonation exercises to reduce pitch variance."
    ),
}


def _reconstruct_evaluation(entry: PracticeHistoryEntry) -> Optional[CoachEvaluation]:
    """Reconstruct CoachEvaluation from history entry."""
    if not entry.evaluation:
        return None
    return CoachEvaluation.model_validate(entry.evaluation)


def _group_findings_by_code(
    entries: List[PracticeHistoryEntry],
) -> Dict[DiagnosisCode, List[tuple[PracticeHistoryEntry, str]]]:
    """
    Group findings by DiagnosisCode.

    Returns dict mapping code to list of (entry, severity) tuples.
    """
    grouped: Dict[DiagnosisCode, List[tuple[PracticeHistoryEntry, str]]] = {}

    for entry in entries:
        evaluation = _reconstruct_evaluation(entry)
        if not evaluation:
            continue

        for finding in evaluation.findings:
            if finding.code is None:
                continue

            if finding.code not in grouped:
                grouped[finding.code] = []

            severity_value = finding.severity.value if finding.severity else "info"
            grouped[finding.code].append((entry, severity_value))

    return grouped


def _compute_trend(
    occurrence_count: int,
    recent_occurrence_count: int,
) -> WeaknessTrend:
    """
    Compute trend based on occurrence counts.

    Priority order:
    1. worsening (strongest negative claim)
    2. improving (positive claim)
    3. recurring (neutral recurrence)
    4. stable (fallback)
    """
    older_count = occurrence_count - recent_occurrence_count

    if older_count > 0 and recent_occurrence_count >= older_count:
        return WeaknessTrend.worsening

    if older_count > 0 and recent_occurrence_count < older_count:
        return WeaknessTrend.improving

    if recent_occurrence_count >= 2:
        return WeaknessTrend.recurring

    return WeaknessTrend.stable


def _most_common_severity(severities: List[str]) -> Optional[str]:
    """
    Get most common severity, with more severe winning ties.

    Severity order (most severe first): primary, secondary, info
    """
    if not severities:
        return None

    severity_order = {"primary": 0, "secondary": 1, "info": 2}
    counts = Counter(severities)

    sorted_severities = sorted(
        counts.keys(),
        key=lambda s: (-counts[s], severity_order.get(s, 99)),
    )

    return sorted_severities[0] if sorted_severities else None


def _goal_title_for_code(code: DiagnosisCode) -> str:
    """Get goal title for diagnosis code."""
    if code in GOAL_TITLES:
        return GOAL_TITLES[code]

    code_name = code.value.replace("_", " ").title()
    return f"Address {code_name}"


def _goal_description_for_code(code: DiagnosisCode) -> str:
    """Get goal description for diagnosis code."""
    if code in GOAL_DESCRIPTIONS:
        return GOAL_DESCRIPTIONS[code]

    code_name = code.value.replace("_", " ").lower()
    return f"Practice exercises to address {code_name} issues."


def build_weakness_progressions(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
    recent_session_limit: int = 10,
) -> List[WeaknessProgression]:
    """
    Build weakness progressions from practice history.

    Parameters
    ----------
    history_store:
        The practice history store.
    user_id:
        Optional user ID filter.
    recent_session_limit:
        Number of recent sessions for recent_occurrence_count.

    Returns
    -------
    List of WeaknessProgression objects, one per DiagnosisCode found.

    Notes
    -----
    - Read-only: does not mutate history
    - Aggregates findings across all sessions
    - Computes trend based on recent vs historical counts
    - Confidence = min(1.0, occurrence_count / 10)
    """
    from .practice_history import PracticeHistoryQuery

    query = PracticeHistoryQuery(user_id=user_id)
    all_entries = history_store.query(query)

    if not all_entries:
        return []

    sorted_entries = sorted(
        all_entries,
        key=lambda e: e.timestamp,
        reverse=True,
    )

    recent_entries = sorted_entries[:recent_session_limit]
    recent_session_ids = {e.session_id for e in recent_entries}

    grouped = _group_findings_by_code(sorted_entries)

    progressions: List[WeaknessProgression] = []

    for code, findings_list in grouped.items():
        occurrence_count = len(findings_list)

        recent_occurrence_count = sum(
            1 for entry, _ in findings_list
            if entry.session_id in recent_session_ids
        )

        severities = [sev for _, sev in findings_list]
        average_severity = _most_common_severity(severities)

        trend = _compute_trend(occurrence_count, recent_occurrence_count)

        timestamps = [entry.timestamp for entry, _ in findings_list]
        first_seen = min(timestamps) if timestamps else None
        last_seen = max(timestamps) if timestamps else None

        related_session_ids = list(dict.fromkeys(
            entry.session_id for entry, _ in findings_list
        ))

        confidence = min(1.0, occurrence_count / 10)

        progression = WeaknessProgression(
            diagnosis_code=code,
            occurrence_count=occurrence_count,
            recent_occurrence_count=recent_occurrence_count,
            average_severity=average_severity,
            trend=trend,
            first_seen=first_seen,
            last_seen=last_seen,
            related_session_ids=related_session_ids,
            confidence=confidence,
        )
        progressions.append(progression)

    progressions.sort(
        key=lambda p: (-p.occurrence_count, p.diagnosis_code.value)
    )

    return progressions


def generate_practice_goals(
    *,
    progressions: Sequence[WeaknessProgression],
    min_occurrence_threshold: int = 3,
) -> List[PracticeGoal]:
    """
    Generate practice goals from weakness progressions.

    Parameters
    ----------
    progressions:
        List of WeaknessProgression objects.
    min_occurrence_threshold:
        Minimum occurrences to generate a goal.

    Returns
    -------
    List of PracticeGoal objects.

    Notes
    -----
    - Goals are deterministic: same progressions yield same goals
    - Goal ID is deterministic: goal_<diagnosis_code_value>
    - Goals only generated if occurrence_count >= threshold
    """
    goals: List[PracticeGoal] = []

    for progression in progressions:
        if progression.occurrence_count < min_occurrence_threshold:
            continue

        goal_id = f"goal_{progression.diagnosis_code.value}"
        title = _goal_title_for_code(progression.diagnosis_code)
        description = _goal_description_for_code(progression.diagnosis_code)

        now = datetime.now(timezone.utc)

        goal = PracticeGoal(
            id=goal_id,
            diagnosis_code=progression.diagnosis_code,
            title=title,
            description=description,
            status=GoalStatus.active,
            target_occurrence_reduction=progression.occurrence_count,
            current_occurrence_count=progression.recent_occurrence_count,
            created_at=now,
            updated_at=now,
            related_session_ids=progression.related_session_ids.copy(),
        )
        goals.append(goal)

    return goals


def update_goal_status(
    *,
    goal: PracticeGoal,
    progression: WeaknessProgression,
) -> PracticeGoal:
    """
    Update goal status based on current progression.

    Parameters
    ----------
    goal:
        The practice goal to update.
    progression:
        Current weakness progression.

    Returns
    -------
    Updated PracticeGoal (new copy, original not mutated).

    Notes
    -----
    Status rules:
    - completed: recent_occurrence_count == 0
    - improving: trend == improving
    - regressed: trend == worsening
    - active: otherwise
    """
    if progression.recent_occurrence_count == 0:
        new_status = GoalStatus.completed
    elif progression.trend == WeaknessTrend.improving:
        new_status = GoalStatus.improving
    elif progression.trend == WeaknessTrend.worsening:
        new_status = GoalStatus.regressed
    else:
        new_status = GoalStatus.active

    return PracticeGoal(
        id=goal.id,
        diagnosis_code=goal.diagnosis_code,
        title=goal.title,
        description=goal.description,
        status=new_status,
        target_occurrence_reduction=goal.target_occurrence_reduction,
        current_occurrence_count=progression.recent_occurrence_count,
        created_at=goal.created_at,
        updated_at=datetime.now(timezone.utc),
        related_session_ids=progression.related_session_ids.copy(),
        source=goal.source,
        version=goal.version,
    )


def build_goal_progress_summary(
    *,
    goals: Sequence[PracticeGoal],
    progressions: Optional[Sequence[WeaknessProgression]] = None,
) -> GoalProgressSummary:
    """
    Build aggregated goal progress summary.

    Parameters
    ----------
    goals:
        List of PracticeGoal objects.
    progressions:
        Optional list of WeaknessProgression for top_weaknesses.

    Returns
    -------
    GoalProgressSummary with counts and top weaknesses.

    Notes
    -----
    - top_weaknesses: top 3 by occurrence_count, tie-breaker alphabetical
    """
    goals_by_status: Dict[str, int] = {}
    active_count = 0
    completed_count = 0

    for goal in goals:
        status_key = goal.status.value
        goals_by_status[status_key] = goals_by_status.get(status_key, 0) + 1

        if goal.status == GoalStatus.active:
            active_count += 1
        elif goal.status == GoalStatus.completed:
            completed_count += 1

    top_weaknesses: List[DiagnosisCode] = []
    if progressions:
        sorted_progressions = sorted(
            progressions,
            key=lambda p: (-p.occurrence_count, p.diagnosis_code.value),
        )
        top_weaknesses = [p.diagnosis_code for p in sorted_progressions[:3]]

    return GoalProgressSummary(
        active_goal_count=active_count,
        completed_goal_count=completed_count,
        goals_by_status=goals_by_status,
        top_weaknesses=top_weaknesses,
    )


__all__ = [
    "build_weakness_progressions",
    "generate_practice_goals",
    "build_goal_progress_summary",
    "update_goal_status",
]
