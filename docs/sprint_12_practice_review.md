# Sprint 12: Practice Timeline & Session Review

**Date:** 2026-05-07
**Status:** COMPLETE

## Overview

Sprint 12 turns persisted practice history into a queryable review layer:
- Practice timeline for multi-session overview
- Session review for detailed single-session inspection
- Progress summary for aggregated metrics

## Deliverables

### 1. Review Schemas (sg-spec)

**File:** `sg_spec/schemas/practice_review.py`

Four review schemas:
- `PracticeTimelineEntry` — Lightweight session summary for timeline display
- `SessionReview` — Complete review data for a single session
- `PracticeProgressSummary` — Aggregated progress metrics
- `PracticeTimeline` — Collection of timeline entries

**Tests:** 28 tests in `tests/test_practice_review_schema.py`

### 2. Review Builders (sg-coach)

**File:** `sg_coach/practice_review.py`

Three builder functions:
- `build_session_review()` — Build complete session review
- `build_practice_timeline()` — Build multi-session timeline
- `build_progress_summary()` — Build aggregated progress summary

**Tests:** 40 tests in `tests/test_practice_review.py`

### 3. Governance Documentation

**File:** `docs/practice_review_governance.md`

Documents:
- Read-only rule
- Timeline model
- Session review model
- Progress summary model
- Teacher augmentation use
- v1 limitations

## Test Summary

| Module | Tests |
|--------|-------|
| test_practice_review_schema.py (sg-spec) | 28 |
| test_practice_review.py (sg-coach) | 40 |
| **Total Sprint 12** | **68** |

## API Summary

### build_session_review

```python
def build_session_review(
    *,
    session_id: str,
    history_store: PracticeHistoryStore,
) -> Optional[SessionReview]:
```

### build_practice_timeline

```python
def build_practice_timeline(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> PracticeTimeline:
```

### build_progress_summary

```python
def build_progress_summary(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> PracticeProgressSummary:
```

## Architecture Position

```
Sprint 11 (Runtime Integration)
├── MidiSessionInput → SessionRecord
├── evaluate_session → recommendations → assignments
└── PracticeHistoryStore (persistence)
        ↓
Sprint 12 (Review Layer)
├── build_practice_timeline() → PracticeTimeline
├── build_session_review() → SessionReview
└── build_progress_summary() → PracticeProgressSummary
```

## Key Design Decisions

1. **Read-only** — Review utilities never mutate history
2. **Bundled storage** — Uses existing Sprint 11 PracticeHistoryStore
3. **Model reconstruction** — Extracts and validates Pydantic models from stored dicts
4. **Graceful degradation** — Missing evaluation/assignments return None, not errors
5. **Top codes by frequency** — Timeline entries show most frequent DiagnosisCodes
6. **Recent from most recent session** — Progress summary recent_diagnosis_codes from single session
7. **Auto-generated summary** — Deterministic string generation

## Governance Rules

1. Review layer is read-only
2. Review must not re-evaluate sessions
3. Review must not re-rank recommendations
4. Missing evaluation/assignments degrade gracefully
5. Teacher review uses structured fields, not message parsing
6. Timeline is local-first and JSONL-backed in v1

## What Sprint 12 Enables

For the **player**:
- Review past practice sessions
- Track progress over time
- See which issues occur most frequently

For the **teacher**:
- View student practice timeline
- Drill into specific session details
- Monitor diagnosis code trends
- Identify persistent issues

## Future Work (Sprint 13+)

1. Date range filtering for progress summary
2. Cross-session diagnosis code trends
3. UI integration for review surfaces
4. Teacher dashboard read API
