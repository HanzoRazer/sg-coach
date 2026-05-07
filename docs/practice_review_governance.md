# Practice Review Governance

Sprint 12: Read-only review layer over practice history.

## Purpose

The practice review layer enables:
- Post-session review by the player
- Teacher review of student progress
- Progress tracking over time

It builds on the Sprint 11 persistence layer to provide queryable views into practice history.

## Read-Only Rule

**Review utilities must not mutate history.**

The review layer is a read-only projection over persisted practice history:
- `build_session_review()` reads and reconstructs, never writes
- `build_practice_timeline()` queries and sorts, never modifies
- `build_progress_summary()` aggregates and counts, never updates

This rule is enforced by:
1. Not exposing write methods from review functions
2. Returning new objects rather than modifying stored data
3. Testing that store contents remain unchanged after review calls

## Timeline Model

```
PracticeTimeline
├── entries: List[PracticeTimelineEntry]
│   ├── session_id
│   ├── user_id
│   ├── instrument_id
│   ├── timestamp
│   ├── program_ref
│   ├── finding_count
│   ├── assignment_count
│   ├── top_diagnosis_codes (limit 3, by frequency)
│   └── status ("reviewable" in v1)
├── total_sessions (may exceed entries if limited)
└── version
```

**Sorting:** Timestamp descending (most recent first).

**Top diagnosis codes:** Most frequent codes in that session's findings, sorted by frequency descending with stable order for ties.

## Session Review Model

```
SessionReview
├── session_id
├── session: SessionRecord
├── evaluation: CoachEvaluation | None
├── assignments: AssembledPracticeAssignmentSet | None
├── findings_by_domain: dict[FeedbackDomain.value, count]
├── assignment_status_counts: dict[PracticeAssignmentStatus.value, count]
├── summary: str | None (auto-generated)
└── version
```

**Summary generation:** Deterministic string like "2 timing findings, 1 harmony finding, 1 assignment generated." Returns None if no findings and no assignments.

**Graceful degradation:** Missing evaluation or assignments are represented as None, not errors.

## Progress Summary Model

```
PracticeProgressSummary
├── user_id (optional)
├── session_count
├── total_findings
├── total_assignments
├── diagnosis_counts: dict[DiagnosisCode.value, count]
├── recent_diagnosis_codes: list[DiagnosisCode]
└── version
```

**Scope:** All history for the user (no date range in v1).

**Recent codes:** Unique diagnosis codes from the most recent session that has findings. Does not aggregate across multiple sessions.

## Teacher Augmentation Use

Teachers can use the review layer to:
1. View a student's practice timeline
2. Drill into specific session reviews
3. Track diagnosis code trends over time
4. Identify frequently occurring issues

**Structured fields over message parsing:** Teachers should use structured fields (findings_by_domain, diagnosis_counts) rather than parsing summary strings. This enables:
- Consistent display across UI implementations
- Filtering and sorting by code/domain
- Trend analysis over time

## Limitations

### v1 Limitations

1. **No date range filtering** — Progress summary covers all history
2. **No cross-session aggregation for recent_diagnosis_codes** — Only uses most recent session
3. **No UI** — Review layer provides data, not presentation
4. **Local-first only** — JSONL storage, no cloud sync
5. **Single status** — Timeline entries are always "reviewable"

### Architectural Boundaries

1. Review must not re-evaluate sessions
2. Review must not re-rank recommendations
3. Review must not modify assignments or findings
4. Review must not trigger learning signal updates

## Definition of Done

Sprint 12 is complete when:

- [x] PracticeTimelineEntry schema exists
- [x] SessionReview schema exists
- [x] PracticeProgressSummary schema exists
- [x] PracticeTimeline schema exists
- [x] build_session_review() implemented and tested
- [x] build_practice_timeline() implemented and tested
- [x] build_progress_summary() implemented and tested
- [x] All review functions read-only (tested)
- [x] Graceful degradation for missing data
- [x] 40 review tests passing
- [x] Governance doc committed

## API Reference

### build_session_review

```python
def build_session_review(
    *,
    session_id: str,
    history_store: PracticeHistoryStore,
) -> Optional[SessionReview]:
```

Returns None if session not found.

### build_practice_timeline

```python
def build_practice_timeline(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> PracticeTimeline:
```

Returns empty timeline if no matching sessions.

### build_progress_summary

```python
def build_progress_summary(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> PracticeProgressSummary:
```

Returns zero-count summary if no matching sessions.
