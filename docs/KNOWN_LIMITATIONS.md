# Known Limitations

Smart Guitar Coaching MVP v1.0.0

## Scope Limitations

### Input Processing

- **MIDI-first only** — Raw audio is not supported. Input must be pre-parsed MIDI events.
- **No audio DSP** — No pitch detection, onset detection, or audio analysis.
- **Post-session only** — Evaluation happens after session completion, not in real-time.
- **No streaming** — Sessions are processed as complete units, not incrementally.

### Persistence

- **Local-first only** — All data stored locally in JSONL files.
- **No cloud sync** — No remote storage or synchronization.
- **Single-machine** — History is not shared across devices.

### Curriculum

- **Static curriculum alignment** — Fixed mapping from diagnosis codes to drills.
- **Four diagnosis codes mapped** — DIM_ORBIT_VIOLATION, TIMING_GRID_DEVIATION, WRONG_NOTE, PITCH_DEVIATION.
- **No dynamic content** — sg-curriculum service not yet integrated.

### User Interface

- **CLI only** — No graphical user interface.
- **JSON output** — Machine-readable output format.
- **No teacher dashboard** — Teacher review is via CLI/API only.

### Scheduling

- **No scheduling engine** — Assignments are generated but not scheduled.
- **No reminders** — No notification or reminder system.
- **Manual progression** — User must manually run evaluations.

## Evaluator Limitations

### Timing Evaluator

- Single threshold (configurable but static per session)
- No tempo curve analysis
- No phrase-level timing assessment

### Pitch Evaluator

- Requires expected pitch data in input
- No automatic transcription
- No intonation trend analysis

### Diminished Evaluator

- Single orbit pattern per evaluation
- No chord progression context
- No voice leading analysis

## Goal Tracking Limitations

- **Goals are ephemeral** — Rebuilt from history on each query.
- **No goal persistence** — GoalStore deferred to future sprint.
- **No teacher override** — Goals cannot be manually adjusted.
- **Single threshold** — Same min_occurrence_threshold for all codes.
- **No severity weighting** — All findings weighted equally.

## Architecture Constraints

- **No new evaluators** — Evaluator set is frozen for MVP.
- **No ML prediction** — All coaching is rule-based/deterministic.
- **No AI curriculum generation** — Static drill mappings only.
- **No real-time adaptation** — Recommendations fixed per session.

## Future Roadmap

See ARCHITECTURE_SNAPSHOT_V1.md for deferred systems:

1. sg-curriculum service integration
2. Teacher dashboard UI
3. Scheduling and reminders (sg-agentd)
4. Cloud persistence
5. Real-time streaming evaluation
6. Audio input processing
7. ML-enhanced recommendations
