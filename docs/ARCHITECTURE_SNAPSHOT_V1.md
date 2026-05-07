# Architecture Snapshot v1.0

Smart Guitar Coaching Platform — MVP Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        sg-coach CLI                             │
│  evaluate | review | goals | timeline                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Runtime Pipeline                             │
│  run_coaching_pipeline() → RuntimeCoachingResult                │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Session Builder │  │   Evaluators    │  │ Recommendation  │
│ MIDI → Session  │  │ timing/pitch/   │  │    Engine       │
│                 │  │ diminished      │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Drill Resolver  │  │   Assignment    │  │ Goal Tracking   │
│                 │  │   Assembler     │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Practice History Store                       │
│                      (JSONL persistence)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Package Dependencies

```
sg-spec (v2.0.0)          sg-coach (v1.0.0)
├── schemas/              ├── evaluators/
│   ├── coach_schemas     │   ├── timing_evaluator
│   ├── midi_session      │   ├── pitch_evaluator
│   ├── action_mapping    │   └── diminished_evaluator
│   ├── practice_assignment│
│   ├── goal_tracking     ├── builders/
│   ├── curriculum_alignment│   ├── session_builder
│   └── runtime_pipeline  │   ├── action_recommender
│                         │   ├── drill_resolver
└── Re-exported by        │   ├── practice_assignment_assembler
    sg_spec.schemas       │   ├── goal_tracking
                          │   └── curriculum_alignment
                          │
                          ├── persistence/
                          │   └── practice_history
                          │
                          ├── runtime/
                          │   └── runtime_pipeline
                          │
                          └── cli.py
```

## Data Flow

### Evaluation Flow

```
MidiSessionInput
    │
    ▼ build_session_from_midi()
SessionRecord
    │
    ▼ evaluate_session()
CoachEvaluation
    │  ├── findings: List[CoachFinding]
    │  ├── focus_recommendation
    │  ├── strengths / weaknesses
    │
    ▼ recommend_actions() [per finding]
List[ActionRecommendationSet]
    │
    ▼ resolve_drills_for_recommendations()
List[DrillResolutionResult]
    │
    ▼ assemble_practice_assignments()
AssembledPracticeAssignmentSet
```

### History Flow

```
RuntimeCoachingResult
    │
    ▼ PracticeHistoryStore.append_session()
PracticeHistoryEntry (persisted to JSONL)
    │
    ▼ build_weakness_progressions()
List[WeaknessProgression]
    │
    ▼ generate_practice_goals()
List[PracticeGoal]
    │
    ▼ build_goal_driven_assignments()
AssembledPracticeAssignmentSet (curriculum-aligned)
```

## Core Components

### Evaluators

| Evaluator | Input | Output | Diagnosis Codes |
|-----------|-------|--------|-----------------|
| TimingEvaluator | expected_times, performed_times | timing deviations | TIMING_GRID_DEVIATION, RUSHING, DRAGGING |
| PitchEvaluator | expected_pitch_events, performed_pitch_events | pitch accuracy | WRONG_NOTE, PITCH_DEVIATION |
| DiminishedEvaluator | performed_notes, orbit_pattern | orbit violations | DIM_ORBIT_VIOLATION |

### Action Mappings

Static registry mapping DiagnosisCode → actions:

| Diagnosis Code | Default Actions | Escalation Actions |
|----------------|-----------------|-------------------|
| TIMING_GRID_DEVIATION | slow_down, metronome | assign_drill |
| PITCH_DEVIATION | isolate | assign_drill |
| WRONG_NOTE | isolate, slow_down | assign_drill |
| DIM_ORBIT_VIOLATION | pattern_review | assign_drill |

### Drill Catalog

Static catalog mapping (DiagnosisCode, ActionType) → DrillReference:

| Code | Action | Drill ID |
|------|--------|----------|
| TIMING_GRID_DEVIATION | assign_drill | drill:timing_grid_basic |
| PITCH_DEVIATION | assign_drill | drill:pitch_accuracy_basic |
| WRONG_NOTE | assign_drill | drill:note_recognition_basic |
| DIM_ORBIT_VIOLATION | assign_drill | drill:diminished_orbit_basic |

### Goal Tracking

Weakness trend calculation from occurrence history:

| Trend | Condition |
|-------|-----------|
| WORSENING | recent_avg > historical_avg × 1.2 |
| IMPROVING | recent_avg < historical_avg × 0.8 |
| RECURRING | present in ≥3 recent sessions |
| STABLE | none of the above |

## Schema Hierarchy

```
RuntimeCoachingResult
├── session: SessionRecord
│   ├── session_id, instrument_id, program
│   ├── timing: SessionTiming
│   ├── events: SessionEvents
│   └── normalized: NormalizedSessionData
│       ├── timing: TimingEvaluationInput
│       ├── pitch: PitchEvaluationInput
│       └── harmony: HarmonyEvaluationInput
│
├── evaluation: CoachEvaluation
│   ├── findings: List[CoachFinding]
│   ├── focus_recommendation: FocusRecommendation
│   ├── strengths, weaknesses: List[str]
│   └── recommendations: List[ActionRecommendationSet]
│
├── recommendations: List[ActionRecommendationSet]
│   └── actions: List[RecommendedAction]
│
├── assignments: AssembledPracticeAssignmentSet
│   └── assignments: List[PracticeAssignment]
│
├── goals: List[PracticeGoal]
│   ├── diagnosis_code, title, description
│   ├── target_metric, target_value
│   └── status: GoalStatus
│
└── goal_driven_assignments: AssembledPracticeAssignmentSet | None
```

## Persistence Format

### History Entry (JSONL line)

```json
{
  "id": "hist_<uuid>",
  "user_id": "user_123",
  "session": { ... SessionRecord ... },
  "evaluation": { ... CoachEvaluation ... },
  "assignments": { ... AssembledPracticeAssignmentSet ... },
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Version Contracts

| Component | Version | Notes |
|-----------|---------|-------|
| sg-spec | 2.0.0 | Schema package |
| sg-coach | 1.0.0 | Coaching engine |
| Runtime Pipeline | 1.0.0 | Pipeline orchestration |
| Session Builder | sg-coach@1.9.0 | MIDI → Session conversion |

## Deferred Systems

The following are planned but not included in MVP:

1. **sg-curriculum** — Dynamic curriculum content service
2. **sg-agentd** — Scheduling and reminder agent
3. **Teacher Dashboard** — Web UI for review/override
4. **Cloud Persistence** — Remote storage sync
5. **Real-time Streaming** — Live session evaluation
6. **Audio Input** — Raw audio DSP processing
7. **ML Recommendations** — Adaptive coaching based on learning patterns

## Testing Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Schema validation | 161 | sg-spec schemas |
| Evaluators | 89 | timing/pitch/diminished |
| Builders | 150+ | session/recommendation/assignment |
| Goal tracking | 60 | weakness/progression/goals |
| Curriculum alignment | 40 | alignment/resolution |
| Runtime pipeline | 22 | end-to-end |
| Golden fixtures | 8 | reproducibility |
| **Total** | **758** | Full regression |

## File Structure

```
sg-coach/
├── src/sg_coach/
│   ├── __init__.py           # Public API exports
│   ├── cli.py                # CLI entry point
│   ├── runtime_pipeline.py   # Pipeline orchestration
│   ├── session_builder.py    # MIDI → Session
│   ├── coach_policy.py       # Evaluation orchestration
│   ├── timing_evaluator.py
│   ├── pitch_evaluator.py
│   ├── diminished_evaluator.py
│   ├── action_recommender.py
│   ├── drill_resolver.py
│   ├── practice_assignment_assembler.py
│   ├── practice_history.py
│   ├── practice_review.py
│   ├── goal_tracking.py
│   ├── curriculum_alignment.py
│   └── schemas.py            # Re-exports from sg-spec
│
├── tests/
│   ├── test_*.py             # Unit and integration tests
│   └── test_golden_fixtures.py
│
├── fixtures/
│   ├── midi/                 # Input fixtures
│   └── golden/               # Expected output fixtures
│
└── docs/
    ├── ARCHITECTURE_SNAPSHOT_V1.md
    ├── KNOWN_LIMITATIONS.md
    └── MVP_RELEASE_CHECKLIST.md
```
