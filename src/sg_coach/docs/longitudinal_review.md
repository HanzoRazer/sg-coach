# Longitudinal Review Builder

## Purpose

Synthesizes historical progress from multiple RuntimeReviewReport sessions.
Produces deterministic trend analysis and outcome aggregation.

Part of the Sprint 28: Longitudinal Progress Review.

## Architectural Position

```
RuntimeReviewReport[] (canonical evidence)
→ longitudinal_review builder
→ LongitudinalProgressReview
→ UI dashboards / teacher review / progress reports
```

## Scope

**Does:**
- Aggregate diagnosis occurrences across sessions
- Compute trend direction (improving/stable/worsening)
- Track outcome trajectory across sessions
- Generate deterministic notes from templates

**Does NOT:**
- AI/LLM text generation
- Hidden scoring models
- Assignment volume weighting
- Cross-user comparison

## Canonical Input

### RuntimeReviewReport Sequence

```python
from sg_coach.longitudinal_review import build_longitudinal_progress_review
from sg_spec.schemas.runtime_review import RuntimeReviewReport

reports: list[RuntimeReviewReport] = load_reports_from_store()

review = build_longitudinal_progress_review(
    reports=reports,
    student_id="student_123",
)
```

## Key Algorithms

### Temporal Split

Reports are split into two halves for trend comparison:
- Sort by `generated_at` timestamp ascending
- Historical = first `floor(n / 2)` reports
- Recent = remaining reports

```python
historical, recent = _split_historical_recent(reports)
```

### Trend Computation

```python
def _compute_trend(historical_count, recent_count, total_reports):
    if total_reports < 2:
        return LongitudinalTrend.insufficient_data
    if recent_count < historical_count:
        return LongitudinalTrend.improving
    elif recent_count == historical_count:
        return LongitudinalTrend.stable
    else:
        return LongitudinalTrend.worsening
```

### Session-Level Counting

Diagnosis codes are counted at session level, not assignment level:
- Same DiagnosisCode appearing twice in one report counts once
- This prevents assignment volume from skewing trends

### Improvement Ratio

```python
improvement_ratio = max(0, historical_count - recent_count) / historical_count
```

Returns `None` if `historical_count == 0`.

## Output Schemas

### LongitudinalProgressReview

```python
LongitudinalProgressReview(
    student_id="student_123",
    review_count=10,
    generated_at=datetime.now(timezone.utc),
    diagnosis_trends=[DiagnosisTrendSummary(...)],
    outcome_trajectory=OutcomeTrajectorySummary(...),
    strongest_improvements=["timing_grid_deviation"],
    recurring_challenges=["pitch_deviation"],
    evidence_review_ids=["rts_001", "rts_002", ...],
    notes=["Timing grid deviation is improving over recent sessions."],
    version="0.1",
)
```

### DiagnosisTrendSummary

```python
DiagnosisTrendSummary(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    total_occurrences=10,
    first_occurrence_at=datetime(...),
    latest_occurrence_at=datetime(...),
    recent_occurrence_count=3,
    historical_occurrence_count=7,
    trend=LongitudinalTrend.improving,
    improvement_ratio=0.57,
)
```

### OutcomeTrajectorySummary

```python
OutcomeTrajectorySummary(
    total_completed=5,
    total_improved=3,
    total_repeated=2,
    total_worsened=1,
    total_abandoned=1,
    completion_ratio=0.67,
    improvement_ratio=0.25,
)
```

## Note Templates

Notes are generated deterministically from templates:

| Pattern | Template |
|---------|----------|
| Improving diagnosis | `"{diagnosis} is improving over recent sessions."` |
| Worsening diagnosis | `"{diagnosis} appears to be worsening."` |
| Stable recurring | `"{diagnosis} remains recurring."` |
| < 2 reports | `"Insufficient evidence for stable trend analysis."` |

Maximum 5 notes per review.

## CLI Usage

```bash
# Generate longitudinal review from NDJSON file of RuntimeReviewReports
sg-coach runtime longitudinal-review \
    --reports reports.ndjson \
    --student-id student_123 \
    --pretty
```

Input file format: NDJSON (one RuntimeReviewReport JSON per line)

## Downstream Consumers

| Consumer | Usage |
|----------|-------|
| practice_dashboard | Long-term trend visualization |
| teacher_review | Progress summary for teachers |
| student_progress_view | Self-assessment UI |
| reporting_api | Export for analytics |

## Ranking Rules

### Strongest Improvements

Ordered by:
1. `improvement_ratio` descending
2. `total_occurrences` descending
3. `DiagnosisCode.value` alphabetical

Limited to top 3.

### Recurring Challenges

Ordered by:
1. Trend priority: worsening before stable
2. `total_occurrences` descending
3. `DiagnosisCode.value` alphabetical

Limited to top 3.

## Evidence Source

Diagnosis codes are extracted from:
```
report.runtime_session.evaluation.findings[].code
```

Only findings with non-null `code` are counted.

## Version

- longitudinal_review.py: 0.1.0
- Schema version: 0.1
- Sprint: 28
