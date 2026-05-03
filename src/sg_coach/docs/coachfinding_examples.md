# CoachFinding Examples

This document provides canonical examples of CoachFinding output from each evaluator.

## DIM_ORBIT_VIOLATION

**Human-readable summary:**
> Your line is outside the diminished orbit — you're not using the available
> chromatic approach tones. In key of C, use B, D, F, Ab as approach tones.

**Full CoachFinding:**

```json
{
  "type": "harmony",
  "severity": "secondary",
  "interpretation": "Your line is outside the diminished orbit — you're not using the available chromatic approach tones.",
  "code": "dim_orbit_violation",
  "domain": "harmony",
  "title": "Diminished orbit violation",
  "message": "Your line is outside the diminished orbit — you're not using the available chromatic approach tones.",
  "evidence": {
    "metric": "dim_orbit_violations",
    "value": 2.0,
    "key": "C",
    "expected_set": ["B", "D", "F", "Ab"],
    "performed_set": ["C", "E"],
    "aggregate_stats": {
      "notes_evaluated": 8,
      "notes_in_orbit": 6,
      "violation_count": 2
    }
  },
  "render_hint": "summary",
  "suggested_actions": [
    {
      "action_type": "isolate",
      "label": "Isolate problem notes",
      "rationale": "Practice the specific notes that fell outside the orbit"
    },
    {
      "action_type": "review_reference",
      "label": "Review diminished orbit",
      "rationale": "In key of C, the orbit is: B, D, F, Ab"
    },
    {
      "action_type": "assign_drill",
      "label": "Orbit awareness drill",
      "rationale": "Practice chromatic approach patterns using orbit notes"
    }
  ],
  "confidence": 1.0,
  "source_evaluator": "diminished_evaluator"
}
```

**Key evidence fields:**
- `key`: The key context for the exercise
- `expected_set`: The diminished orbit notes
- `performed_set`: Notes that violated the orbit
- `aggregate_stats`: Summary of evaluation

**Render hint:** `summary` — display as a summary card, not inline

---

## TIMING_GRID_DEVIATION

**Human-readable summary:**
> Timing deviation detected: 60.0ms late (threshold: 40ms). Average error: 35.5ms.
> Practice at a slower tempo to lock in the grid.

**Full CoachFinding:**

```json
{
  "type": "timing",
  "severity": "secondary",
  "interpretation": "Timing deviation detected: 60.0ms late (threshold: 40ms). Average error: 35.5ms.",
  "code": "timing_grid_deviation",
  "domain": "timing",
  "title": "Timing grid deviation",
  "message": "Timing deviation detected: 60.0ms late (threshold: 40ms). Average error: 35.5ms.",
  "evidence": {
    "metric": "timing_grid_deviation",
    "value": 60.0,
    "unit": "ms",
    "threshold": 40.0,
    "offset_ms": 60.0,
    "direction": "late",
    "index": 3,
    "aggregate_stats": {
      "average_abs_error_ms": 35.5,
      "max_abs_error_ms": 60.0,
      "events_evaluated": 16,
      "deviation_count": 2,
      "tempo_bpm": 120.0
    }
  },
  "render_hint": "timeline",
  "suggested_actions": [
    {
      "action_type": "repeat",
      "label": "Repeat section",
      "rationale": "Practice the same passage again with focus on timing"
    },
    {
      "action_type": "slow_down",
      "label": "Reduce tempo",
      "rationale": "Practice at a slower tempo to lock in the grid"
    },
    {
      "action_type": "retry_section",
      "label": "Retry problem area",
      "rationale": "Focus on note 4 which was 60ms late"
    }
  ],
  "confidence": 1.0,
  "source_evaluator": "timing_evaluator"
}
```

**Key evidence fields:**
- `offset_ms`: How far off the note was
- `direction`: "early", "late", or "on_time"
- `index`: Which note in the sequence
- `threshold`: The acceptable deviation
- `aggregate_stats`: Session-wide timing statistics

**Render hint:** `timeline` — display on a timeline visualization

---

## Evidence Field Reference

| Field | Type | Used By | Description |
|-------|------|---------|-------------|
| metric | str | All | What was measured |
| value | float | All | The measurement |
| unit | str | Timing | Unit (ms, %, etc.) |
| threshold | float | Timing | Violation threshold |
| offset_ms | float | Timing | Time offset |
| direction | str | Timing | early/late/on_time |
| index | int | Timing | Event index |
| key | str | Harmony | Musical key |
| expected_set | list[str] | Harmony | Expected notes |
| performed_set | list[str] | Harmony | Actual notes |
| aggregate_stats | dict | All | Summary statistics |

---

## Render Hints

| Hint | Usage |
|------|-------|
| `inline` | Show inline with content |
| `timeline` | Display on timeline |
| `summary` | Show as summary card |
| `drill` | Suggest drill/exercise |
| `compare` | Compare expected vs actual |

---

## Action Types

| Type | Usage |
|------|-------|
| `repeat` | Repeat the section |
| `slow_down` | Reduce tempo |
| `isolate` | Focus on problem area |
| `retry_section` | Retry specific section |
| `assign_drill` | Assign practice drill |
| `review_reference` | Review reference material |
