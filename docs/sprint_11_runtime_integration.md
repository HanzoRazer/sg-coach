# Sprint 11: Runtime Integration

**Date:** 2026-05-07
**Status:** COMPLETE

## Overview

Sprint 11 connects the symbolic coaching spine (Sprints 1-10) to a minimal runtime:
MIDI ingestion, CLI evaluation, and practice history persistence.

## Deliverables

### 1. MIDI Ingestion Contract (sg-spec)

**File:** `sg_spec/schemas/midi_session.py`

Schemas for pre-parsed MIDI events + session metadata:
- `MidiEventType` — note_on/note_off enum
- `MidiNoteEvent` — single MIDI note event (note, velocity, time_sec, channel)
- `SessionInputMetadata` — session metadata (IDs, program ref, tempo, expected events)
- `MidiSessionInput` — complete input for coaching evaluation

**Tests:** 38 tests in `tests/test_midi_session_schema.py`

### 2. Session Builder (sg-coach)

**File:** `sg_coach/session_builder.py`

Converts MidiSessionInput → SessionRecord:
- `build_session_from_midi()` — main conversion function
- Extracts note-on events
- Computes performed times, pitch events, pitch classes
- Populates NormalizedSessionData for evaluators
- Calculates timing error statistics

**Tests:** 27 tests in `tests/test_session_builder.py`

### 3. CLI Evaluate Command (sg-coach)

**File:** `sg_coach/cli.py`

Usage:
```bash
# Evaluate session JSON
sg-coach evaluate session.json

# Evaluate MIDI input JSON
sg-coach evaluate --midi midi_input.json

# With persistence
sg-coach evaluate --midi midi_input.json --persist history.jsonl --user-id player1

# Verbose output
sg-coach evaluate --midi midi_input.json -v
```

### 4. Practice History Persistence (sg-coach)

**File:** `sg_coach/practice_history.py`

JSONL append-only storage for practice history:
- `PracticeHistoryEntry` — session + evaluation + assignments bundle
- `PracticeHistoryStore` — JSONL store with query support
- `create_history_entry()` — create entry from pipeline output

Queryable by:
- user_id
- instrument_id
- session_id

**Tests:** 21 tests in `tests/test_practice_history.py`

### 5. End-to-End Pipeline Test

**File:** `tests/test_e2e_midi_pipeline.py`

Verifies complete pipeline:
1. MidiSessionInput → SessionRecord (build_session_from_midi)
2. SessionRecord → CoachEvaluation (evaluate_session)
3. CoachEvaluation → ActionRecommendationSet (attach_recommendations)
4. Recommendations → DrillResolutionResult (resolve_drill)
5. Everything → AssembledPracticeAssignmentSet (assemble_practice_assignments)
6. Persist to PracticeHistoryStore (append_session)

**Tests:** 13 end-to-end tests covering the entire pipeline

## Test Summary

| Module | Tests |
|--------|-------|
| test_midi_session_schema.py | 38 |
| test_session_builder.py | 27 |
| test_practice_history.py | 21 |
| test_e2e_midi_pipeline.py | 13 |
| **Total Sprint 11** | **99** |

## Pipeline Flow

```
MidiSessionInput (MIDI events + metadata)
    ↓ build_session_from_midi()
SessionRecord (normalized for evaluators)
    ↓ evaluate_session()
CoachEvaluation + CoachFindings
    ↓ attach_recommendations()
CoachEvaluation + ActionRecommendationSets
    ↓ resolve_drills_for_evaluation()
List[DrillResolutionResult]
    ↓ assemble_practice_assignments()
AssembledPracticeAssignmentSet
    ↓ store.append_session()
PracticeHistoryEntry (persisted to JSONL)
```

## Success Condition

> Given a MIDI-derived SessionRecord, the system produces a persisted
> PracticeAssignmentSet using the existing symbolic coaching spine.

**Verified by:** `test_full_pipeline_with_persistence` in test_e2e_midi_pipeline.py

## Architectural Notes

### What Sprint 11 Does

- Connects MIDI input to the coaching spine
- Provides CLI for batch evaluation
- Persists practice history as append-only events
- Enables querying by user/instrument/session

### What Sprint 11 Does NOT Do

- Real-time streaming evaluation
- Audio DSP ingestion
- Cloud sync or multi-tenant storage
- UI integration

### Preserved Invariants

1. sg-spec remains canonical contract authority
2. Learning signals remain explainable and inspectable
3. Coaching decisions traceable to evidence
4. Feedback and outcomes are append-only events
5. Ranking may reorder but not invent actions
6. Runtime integrations use governed schemas

## Future Work (Sprint 12+)

1. sg-agentd integration (daemon orchestration)
2. Assignment outcome → learning signal pipeline
3. Practice history aggregation/analytics
4. UI integration for outcome capture
