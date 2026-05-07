# Goal Tracking Examples

Sprint 13: Practical examples of weakness progression and goal generation.

## Example 1: Recurring Timing Weakness

**Scenario:** Player has timing grid deviations in 5 of the last 10 sessions.

```python
from sg_coach import (
    build_weakness_progressions,
    generate_practice_goals,
)

# Build progressions from history
progressions = build_weakness_progressions(
    history_store=store,
    user_id="user_123",
    recent_session_limit=10,
)

# Find the timing progression
timing_prog = next(
    (p for p in progressions
     if p.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION),
    None
)

# Result:
# timing_prog.occurrence_count = 8
# timing_prog.recent_occurrence_count = 5
# timing_prog.trend = WeaknessTrend.worsening  # 5 >= 3 (older)
# timing_prog.confidence = 0.8

# Generate goals from progressions
goals = generate_practice_goals(
    progressions=progressions,
    min_occurrence_threshold=3,
)

# Result:
# goals[0].id = "goal_timing_grid_deviation"
# goals[0].title = "Reduce timing grid deviations"
# goals[0].status = GoalStatus.active
# goals[0].target_occurrence_reduction = 8
```

## Example 2: Improving Pitch Accuracy

**Scenario:** Player had many wrong notes historically, but recent sessions show improvement.

```python
# Progression shows improvement
progression = WeaknessProgression(
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    occurrence_count=15,       # Total historical
    recent_occurrence_count=2,  # Only 2 in last 10 sessions
    trend=WeaknessTrend.improving,  # 2 < 13 (older)
    confidence=1.0,
)

# Update existing goal status
goal = PracticeGoal(
    id="goal_wrong_note",
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    title="Improve pitch accuracy",
    description="Work on exercises...",
    status=GoalStatus.active,
)

updated_goal = update_goal_status(
    goal=goal,
    progression=progression,
)

# Result:
# updated_goal.status = GoalStatus.improving
# updated_goal.current_occurrence_count = 2
```

## Example 3: Goal Completion

**Scenario:** Player has zero recent occurrences of diminished orbit violations.

```python
progression = WeaknessProgression(
    diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    occurrence_count=6,
    recent_occurrence_count=0,  # Zero in last 10 sessions!
    trend=WeaknessTrend.stable,
    confidence=0.6,
)

goal = PracticeGoal(
    id="goal_dim_orbit_violation",
    diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    title="Stabilize diminished orbit navigation",
    description="Practice exercises...",
    status=GoalStatus.active,
)

updated_goal = update_goal_status(
    goal=goal,
    progression=progression,
)

# Result:
# updated_goal.status = GoalStatus.completed
# Goal is marked complete because recent_occurrence_count == 0
```

## Example 4: Regression Detection

**Scenario:** Player was improving but recent sessions show more errors.

```python
# Progression shows worsening
progression = WeaknessProgression(
    diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
    occurrence_count=10,
    recent_occurrence_count=7,  # 7 >= 3 (older count)
    trend=WeaknessTrend.worsening,
    confidence=1.0,
)

goal = PracticeGoal(
    id="goal_pitch_deviation",
    diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
    title="Reduce pitch deviations",
    description="Practice intonation...",
    status=GoalStatus.improving,
)

updated_goal = update_goal_status(
    goal=goal,
    progression=progression,
)

# Result:
# updated_goal.status = GoalStatus.regressed
# Status changed from improving to regressed
```

## Example 5: Goal Progress Summary

**Scenario:** Teacher wants to see student's overall goal status.

```python
from sg_coach import (
    build_weakness_progressions,
    generate_practice_goals,
    update_goal_status,
    build_goal_progress_summary,
)

# Get progressions
progressions = build_weakness_progressions(
    history_store=store,
    user_id="student_001",
)

# Generate goals
goals = generate_practice_goals(progressions=progressions)

# Update each goal with current progression
updated_goals = []
for goal in goals:
    prog = next(
        (p for p in progressions
         if p.diagnosis_code == goal.diagnosis_code),
        None
    )
    if prog:
        updated_goals.append(
            update_goal_status(goal=goal, progression=prog)
        )

# Build summary
summary = build_goal_progress_summary(
    goals=updated_goals,
    progressions=progressions,
)

# Result:
# summary.active_goal_count = 2
# summary.completed_goal_count = 1
# summary.goals_by_status = {"active": 2, "completed": 1}
# summary.top_weaknesses = [
#     DiagnosisCode.TIMING_GRID_DEVIATION,
#     DiagnosisCode.WRONG_NOTE,
#     DiagnosisCode.DIM_ORBIT_VIOLATION,
# ]
```

## Example 6: Below Threshold (No Goal Generated)

**Scenario:** Player has only 2 occurrences of a weakness — not enough for a goal.

```python
progression = WeaknessProgression(
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    occurrence_count=2,
    recent_occurrence_count=2,
    trend=WeaknessTrend.recurring,
    confidence=0.2,
)

goals = generate_practice_goals(
    progressions=[progression],
    min_occurrence_threshold=3,  # Default
)

# Result:
# goals == []
# No goal generated because occurrence_count < threshold
```

## Trend Computation Examples

| Total | Recent | Older | Trend |
|-------|--------|-------|-------|
| 1 | 1 | 0 | stable |
| 2 | 2 | 0 | recurring |
| 6 | 3 | 3 | worsening |
| 6 | 4 | 2 | worsening |
| 10 | 2 | 8 | improving |
| 10 | 3 | 7 | improving |
| 3 | 3 | 0 | recurring |

## Architecture Flow

```
PracticeHistoryStore
│
├── build_weakness_progressions()
│   └── list[WeaknessProgression]
│
├── generate_practice_goals()
│   └── list[PracticeGoal]
│
├── update_goal_status()
│   └── PracticeGoal (updated)
│
└── build_goal_progress_summary()
    └── GoalProgressSummary
```

**Key property:** All functions are read-only with respect to history. Goals are ephemeral and rebuilt from history each time.
