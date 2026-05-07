# Goal Tracking Governance

Sprint 13: Longitudinal coaching intelligence layer.

## Purpose

The goal tracking layer enables:
- Identifying recurring weaknesses over time
- Converting repeated findings into explicit practice goals
- Tracking improvement/regression trends
- Providing explainable coaching insights

It builds on the Sprint 11/12 practice history and review layers to provide longitudinal intelligence.

## Weakness Progression Model

```
WeaknessProgression
├── diagnosis_code: DiagnosisCode
├── occurrence_count: total across all history
├── recent_occurrence_count: within last N sessions
├── average_severity: most common severity value
├── trend: stable | improving | worsening | recurring
├── first_seen / last_seen: timestamps
├── related_session_ids: list[str]
├── confidence: min(1.0, occurrence_count / 10)
└── version
```

**Aggregation scope:** All history for the user, no date range filter in v1.

**Recent session limit:** Configurable, default 10 sessions.

## Trend Heuristics

Trend computation uses deterministic rules:

```
older_count = occurrence_count - recent_occurrence_count

Priority order:
1. worsening: older_count > 0 AND recent_occurrence_count >= older_count
2. improving: older_count > 0 AND recent_occurrence_count < older_count
3. recurring: recent_occurrence_count >= 2
4. stable: fallback
```

**Priority reasoning:** Worsening/improving are stronger trend claims than simple recurrence.

## Goal Generation Rules

Goals are generated from progressions using explainable heuristics:

```
If occurrence_count >= min_occurrence_threshold (default: 3):
    generate goal
```

**Goal ID:** Deterministic: `goal_<diagnosis_code_value>`

**Title/description:** Static lookup for Layer 1 codes, fallback derivation for others.

**Target:** `target_occurrence_reduction = occurrence_count` (goal is zero recent occurrences)

## Goal Lifecycle

```
active → improving → completed
      ↘ regressed
```

**Status rules:**

| Condition | New Status |
|-----------|------------|
| recent_occurrence_count == 0 | completed |
| trend == improving | improving |
| trend == worsening | regressed |
| otherwise | active |

**Completion is evidence-based:** A goal is only completed when recent occurrences drop to zero.

## Teacher Augmentation Use

Teachers can use the goal tracking layer to:

1. View student weakness progressions
2. Identify persistent issues across sessions
3. Track improvement trends
4. See auto-generated goals based on recurring weaknesses

**Structured fields over interpretation:** Use structured fields (occurrence_count, trend, diagnosis_code) rather than parsing text. This enables consistent display and filtering.

## Limitations

### v1 Limitations

1. **Goals are ephemeral** — No goal persistence store yet; goals are rebuilt from history
2. **No date range filtering** — Progression covers all history
3. **No teacher override** — Teachers cannot manually adjust goals in v1
4. **Single threshold** — Same min_occurrence_threshold for all codes
5. **No severity weighting** — Occurrences counted equally regardless of severity

### Architectural Boundaries

1. Goal tracking must not mutate history
2. Goal tracking must not re-evaluate sessions
3. Goal generation must remain deterministic
4. Goals must be explainable from findings
5. No ML-based prediction in v1
6. No autonomous goal creation outside explicit heuristics

## Governance Rules

1. **Goals are deterministic and explainable.**
2. **Goals derive from repeated findings, not raw note events.**
3. **Goal tracking must not mutate history.**
4. **Goal progression is heuristic-driven in v1.**
5. **Goal completion is evidence-based, not manually inferred.**
6. **Teacher review may override goals later, but not in v1.**
7. **Goal generation must remain auditable from findings.**

## Definition of Done

Sprint 13 is complete when:

- [x] WeaknessProgression schema exists
- [x] PracticeGoal schema exists
- [x] GoalProgressSummary schema exists
- [x] Weakness progression analysis works
- [x] Practice goals can be generated
- [x] Goal statuses can update
- [x] Goal summaries can be built
- [x] Tests pass
- [x] Docs committed
- [x] History remains immutable
- [x] No new evaluators added

## API Reference

### build_weakness_progressions

```python
def build_weakness_progressions(
    *,
    history_store: PracticeHistoryStore,
    user_id: str | None = None,
    recent_session_limit: int = 10,
) -> list[WeaknessProgression]:
```

Returns empty list if no matching history.

### generate_practice_goals

```python
def generate_practice_goals(
    *,
    progressions: Sequence[WeaknessProgression],
    min_occurrence_threshold: int = 3,
) -> list[PracticeGoal]:
```

Returns empty list if no progressions meet threshold.

### update_goal_status

```python
def update_goal_status(
    *,
    goal: PracticeGoal,
    progression: WeaknessProgression,
) -> PracticeGoal:
```

Returns new PracticeGoal with updated status (does not mutate original).

### build_goal_progress_summary

```python
def build_goal_progress_summary(
    *,
    goals: Sequence[PracticeGoal],
    progressions: Sequence[WeaknessProgression] | None = None,
) -> GoalProgressSummary:
```

Returns summary with counts and top 3 weaknesses.
