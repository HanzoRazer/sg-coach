# Sprint 13: Goal Tracking & Weakness Progression

**Date:** 2026-05-07
**Status:** COMPLETE

## Overview

Sprint 13 adds the first longitudinal coaching intelligence layer:
- Weakness progression analysis from practice history
- Practice goal generation from repeated weaknesses
- Goal status tracking based on improvement trends
- Goal progress summaries for teacher/player review

## Deliverables

### 1. Goal Tracking Schemas (sg-spec)

**File:** `sg_spec/schemas/goal_tracking.py`

Five schema definitions:
- `GoalStatus` — Enum: active, improving, completed, regressed, abandoned
- `WeaknessTrend` — Enum: stable, improving, worsening, recurring
- `WeaknessProgression` — Tracks a weakness over time
- `PracticeGoal` — Explicit practice goal derived from weaknesses
- `GoalProgressSummary` — Aggregated goal status overview

**Tests:** 33 tests in `tests/test_goal_tracking_schema.py`

### 2. Goal Tracking Builders (sg-coach)

**File:** `sg_coach/goal_tracking.py`

Four builder functions:
- `build_weakness_progressions()` — Analyze findings over time
- `generate_practice_goals()` — Create goals from repeated weaknesses
- `update_goal_status()` — Update goal based on progression
- `build_goal_progress_summary()` — Aggregate goal status overview

**Tests:** 60 tests in `tests/test_goal_tracking.py`

### 3. Governance Documentation

**Files:**
- `docs/goal_tracking_governance.md` — Rules and limitations
- `docs/goal_tracking_examples.md` — Practical usage examples

## Test Summary

| Module | Tests |
|--------|-------|
| test_goal_tracking_schema.py (sg-spec) | 33 |
| test_goal_tracking.py (sg-coach) | 60 |
| **Total Sprint 13** | **93** |

## API Summary

### build_weakness_progressions

```python
def build_weakness_progressions(
    *,
    history_store: PracticeHistoryStore,
    user_id: str | None = None,
    recent_session_limit: int = 10,
) -> list[WeaknessProgression]:
```

### generate_practice_goals

```python
def generate_practice_goals(
    *,
    progressions: Sequence[WeaknessProgression],
    min_occurrence_threshold: int = 3,
) -> list[PracticeGoal]:
```

### update_goal_status

```python
def update_goal_status(
    *,
    goal: PracticeGoal,
    progression: WeaknessProgression,
) -> PracticeGoal:
```

### build_goal_progress_summary

```python
def build_goal_progress_summary(
    *,
    goals: Sequence[PracticeGoal],
    progressions: Sequence[WeaknessProgression] | None = None,
) -> GoalProgressSummary:
```

## Architecture Position

```
Sprint 12 (Review Layer)
├── build_practice_timeline() → PracticeTimeline
├── build_session_review() → SessionReview
└── build_progress_summary() → PracticeProgressSummary
        ↓
Sprint 13 (Goal Tracking)
├── build_weakness_progressions() → list[WeaknessProgression]
├── generate_practice_goals() → list[PracticeGoal]
├── update_goal_status() → PracticeGoal
└── build_goal_progress_summary() → GoalProgressSummary
```

## Key Design Decisions

1. **Deterministic goals** — Goals generated from explainable heuristics, not ML
2. **Ephemeral goals** — Goals rebuilt from history each time (no persistence in v1)
3. **Read-only** — Goal tracking never mutates history
4. **Evidence-based completion** — Goal completed only when recent_occurrence_count == 0
5. **Trend priority** — worsening > improving > recurring > stable
6. **Confidence from sample size** — `min(1.0, occurrence_count / 10)`
7. **Deterministic IDs** — `goal_<diagnosis_code_value>` prevents duplicates

## Governance Rules

1. Goals are deterministic and explainable
2. Goals derive from repeated findings, not raw note events
3. Goal tracking must not mutate history
4. Goal progression is heuristic-driven in v1
5. Goal completion is evidence-based, not manually inferred
6. Teacher review may override goals later, but not in v1
7. Goal generation must remain auditable from findings

## What Sprint 13 Enables

For the **player**:
- See which weaknesses persist over time
- Track improvement on specific skills
- Get auto-generated practice goals
- See progress toward goal completion

For the **teacher**:
- Identify students with recurring issues
- Track improvement trends across sessions
- View auto-generated goals for discussion
- See top weaknesses per student

## Future Work (Sprint 14+)

1. Goal persistence store (GoalStore)
2. Teacher goal override capability
3. Per-code threshold configuration
4. Severity-weighted occurrence counting
5. Date range filtering for progressions
6. UI integration for goal surfaces
