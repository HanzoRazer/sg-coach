# Adaptive Scheduling Governance

Sprint 30: Evidence-Driven Adaptive Scheduling

## Purpose

The Adaptive Scheduling Engine analyzes pedagogical evidence to generate deterministic scheduling recommendations. It transforms accumulated evidence into actionable queue evolution guidance.

## Core Rules

1. **Adaptive scheduling must remain deterministic** — same inputs always produce same outputs
2. **Scheduling recommendations must cite evidence** — every recommendation links to `evidence_ids`
3. **Queue mutation remains caller-controlled** — the engine recommends, the caller decides
4. **Hidden scoring systems are prohibited** — all logic is explicit and inspectable
5. **AI scheduling optimization is deferred** — no ML, no predictive analytics
6. **Evidence provenance must remain inspectable** — recommendations trace back to ledger entries

## Pattern Detection

### Worsening Trend
- Source: `longitudinal_review`
- Detection: `metadata["trend"] == "worsening"`
- Action: Increase priority, recommend repetition

### Improving Trend
- Source: `longitudinal_review`
- Detection: `metadata["trend"] == "improving"`
- Action: Decrease priority, suggest delay

### Repeated Outcomes
- Source: `assignment_outcome`
- Detection: `metadata["outcome"] == "repeated"`, count >= 2
- Grouping: By `diagnosis_code` or `assignment_id`
- Action: Increase priority, recommend repetition

### Abandonment Pattern
- Sources: 
  - `assignment_outcome` with `metadata["outcome"] == "abandoned"`
  - `queue_event` with `metadata["event_type"] == "assignment_abandoned"`
- Threshold: >= 1 occurrence
- Action: Increase priority, recommend attention

### Recurring Diagnosis
- Detection: Same `diagnosis_code` appears in >= 3 ledger entries
- Action: Increase priority, recommend repetition

## Thresholds

```python
REPEATED_OUTCOME_THRESHOLD = 2
RECURRING_DIAGNOSIS_THRESHOLD = 3
ABANDONMENT_THRESHOLD = 1
```

These are module-level constants, not configurable per-call.

## Priority Adjustment Semantics

| Adjustment | Recommended Priority | Recommended Repetition | Recommended Delay |
|------------|---------------------|------------------------|-------------------|
| `increase` | `high` | 2 | None |
| `decrease` | `low` | None | 3 days |
| `maintain` | None (unchanged) | None | None |

## Recommendation Targeting

Valid targets:
- `assignment_id` only — assignment-specific evidence
- `diagnosis_code` only — diagnosis-wide evidence
- Both — preferred when both are available

Invalid: Neither `assignment_id` nor `diagnosis_code` — recommendation is skipped.

## Queue Integration

`apply_adaptive_recommendations_to_queue` performs:

1. **Priority update**: Updates `ScheduledPracticeAssignment.priority` directly when `assignment_id` matches
2. **Metadata storage**: Adds `metadata["adaptive_scheduling"]` with:
   - `recommendation_id`
   - `priority_adjustment`
   - `recommended_repetition_count`
   - `recommended_delay_days`
   - `evidence_ids`

The function:
- Returns a new immutable queue
- Does NOT reorder assignments
- Does NOT change `deferred_until`
- Preserves all existing metadata

## Recommendation Ordering

Recommendations are sorted deterministically:

1. Critical/high suggested priority first
2. More evidence IDs descending
3. Diagnosis code alphabetical

## Repetition / Delay Semantics

- `recommended_repetition_count`: Advisory — "consider repeating N times"
- `recommended_delay_days`: Advisory — "consider deferring N days"

Sprint 30 does NOT:
- Clone or schedule new assignments automatically
- Modify `deferred_until` directly

These remain caller-controlled decisions.

## Not Implemented in Sprint 30

- `insufficient_recent_practice` reason — requires practice session cadence model
- Automatic queue mutation
- ML ranking
- Predictive scheduling
- Calendar integration

## CLI Usage

```bash
sg-coach adaptive-scheduling \
    --ledger ledger.json \
    --queue queue.json \
    --student-id student_123 \
    --pretty
```

Output: `AdaptiveSchedulingPlan` JSON with recommendations.

## Schema Exports

From `sg_spec.schemas.adaptive_scheduling`:
- `SchedulingPriorityAdjustment` — increase | maintain | decrease
- `SchedulingRecommendationReason` — evidence-based reasons
- `AdaptiveSchedulingRecommendation` — single recommendation
- `AdaptiveSchedulingPlan` — collection with metadata

From `sg_coach`:
- `build_adaptive_scheduling_recommendations(ledger, queue)` — generate recommendations
- `build_adaptive_scheduling_plan(ledger, queue, student_id)` — build complete plan
- `apply_adaptive_recommendations_to_queue(queue, recommendations)` — apply to queue

## Limitations

1. Pattern detection uses explicit metadata fields only — no text inference
2. Thresholds are fixed constants — no per-call configuration
3. Queue integration is advisory — no automatic scheduling
4. No learning from past recommendation outcomes
5. No cross-student pattern detection
