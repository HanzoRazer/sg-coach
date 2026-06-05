# Practice Dashboard Governance

Sprint 17: Dashboard data layer for visualizing longitudinal practice progress.

## Purpose

The practice dashboard provides structured JSON data for UI rendering of practice progress. It aggregates metrics, weakness trends, goals, assignments, and practice frequency from the local-first history store.

## Dashboard Data Model

### PracticeDashboardData

Top-level container for all dashboard sections:

```python
class PracticeDashboardData(BaseModel):
    user_id: Optional[str]
    metrics: list[DashboardMetricCard]
    weakness_trends: list[DashboardWeaknessTrend]
    goals: list[DashboardGoalCard]
    assignment_summary: DashboardAssignmentSummary
    practice_frequency: DashboardPracticeFrequency
    generated_at: datetime
    version: str = "0.1"
```

### Metric Cards

Five standard metrics in exact order:

1. **Total Sessions** — int, count of all practice sessions
2. **Total Findings** — int, count of all coaching findings
3. **Total Assignments** — int, count of all practice assignments
4. **Active Goals** — int, count of active/improving/regressed goals
5. **Top Weakness** — str (DiagnosisCode value), description: "{n} occurrences"

### Weakness Trends

Converted from WeaknessProgression:

- **diagnosis_code** — the weakness being tracked
- **occurrence_count** — total occurrences across history
- **recent_occurrence_count** — occurrences in recent sessions
- **trend** — WeaknessTrend value (worsening, improving, recurring, stable)
- **confidence** — computed as `min(1.0, occurrence_count / 10)`

Sorted by:
1. occurrence_count descending
2. diagnosis_code.value alphabetically ascending

Limited to top 5.

### Goal Cards

Converted from PracticeGoal:

- **goal_id** — from PracticeGoal.id (None if not set)
- **title** — goal title
- **diagnosis_code** — the weakness this goal addresses
- **status** — GoalStatus (active, improving, regressed)
- **current_occurrence_count** — from PracticeGoal
- **target_occurrence_reduction** — from PracticeGoal

Includes: active, improving, regressed
Excludes: completed, abandoned

### Assignment Summary

Counts by status from history:

- **total_assignments** — total across all sessions
- **ready_count** — status == "ready"
- **unresolved_count** — status == "unresolved"
- **completed_count** — None (outcome tracking not in MVP)
- **abandoned_count** — None (outcome tracking not in MVP)

### Practice Frequency

Session statistics:

- **session_count** — total practice sessions
- **active_days** — unique calendar dates (UTC) with sessions
- **first_session_at** — earliest session timestamp
- **last_session_at** — most recent session timestamp

## Governance Rules

1. **Read-only** — Dashboard must not mutate history or goals
2. **No re-evaluation** — Dashboard must not re-evaluate sessions
3. **No mutation** — Dashboard must not modify goals or history entries
4. **Structured fields** — Dashboard must use structured fields, not parse messages
5. **JSON serializable** — Dashboard data must be serializable to JSON
6. **UI-independent** — Dashboard output is UI-ready but UI-independent

## Builder Inputs

```python
def build_practice_dashboard(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> PracticeDashboardData
```

Internally reuses existing builders:
- `build_practice_timeline()` — for session count
- `build_progress_summary()` — for findings and assignments totals
- `build_weakness_progressions()` — for weakness trends
- `generate_practice_goals()` — for goal cards

## CLI Usage

```bash
sg-coach dashboard --history history.jsonl
sg-coach dashboard --history history.jsonl --user-id user_123
sg-coach dashboard --history history.jsonl --pretty
```

Output: JSON (default) or pretty-printed JSON (--pretty)

## Future UI Usage

The dashboard data is designed for UI rendering:

```json
{
  "metrics": [
    {"label": "Total Sessions", "value": 42},
    {"label": "Top Weakness", "value": "timing_grid_deviation", "description": "7 occurrences"}
  ],
  "weakness_trends": [
    {"diagnosis_code": "timing_grid_deviation", "occurrence_count": 7, "trend": "worsening"}
  ],
  "goals": [
    {"title": "Improve Timing", "status": "active"}
  ]
}
```

A web UI can consume this directly via API or file.

## Limitations

- No real-time updates (post-session only)
- No outcome tracking for assignments (v1)
- No historical comparison (single point-in-time snapshot)
- No teacher dashboard features (v1)
- Local timezone not handled (UTC dates)
