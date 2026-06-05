# Runtime Flow Governance

Sprint 25: Queue-to-runtime practice session flow.
Sprint 26: Runtime session evaluation attachment.

## Purpose

Runtime flow orchestrates the connection between:
- Practice queue assignments
- Runtime practice sessions
- Assignment outcomes
- Queue state updates
- Curriculum progression

This is the first fully connected practice execution lifecycle in Smart Guitar.

## Runtime Orchestration Model

### What Runtime Flow Does

1. **start_runtime_session / start_next_queue_assignment**
   - Takes a scheduled assignment from the queue
   - Looks up the assembled assignment
   - Marks queue assignment as active
   - Creates RuntimePracticeSession wrapper
   - Returns updated state for caller to persist

2. **complete_runtime_session**
   - Takes outcome from practice
   - Creates AssignmentOutcomeEvent
   - Calls process_assignment_outcome (Sprint 24)
   - Returns integration result with updated queue and progress
   - Caller persists changes

3. **abandon_runtime_session**
   - Marks session and queue assignment as abandoned
   - Does NOT create outcome event
   - Does NOT affect curriculum progression
   - Returns updated state for caller to persist

4. **attach_session_record** (Sprint 26)
   - Attaches SessionRecord evidence to runtime session
   - Sets session_id reference
   - Returns updated session and attachment event
   - Caller persists changes

5. **attach_evaluation** (Sprint 26)
   - Attaches CoachEvaluation evidence to runtime session
   - Requires session_record attached first
   - Validates session_id match between session_record and evaluation
   - Returns updated session and attachment event

6. **attach_runtime_evidence** (Sprint 26)
   - Combined helper for attaching both SessionRecord and CoachEvaluation
   - Adds "session_evaluation_link_unverified" if session_ids don't match
   - Does not raise — accumulates warnings in reasons
   - Returns RuntimeEvidenceAttachmentResult

7. **runtime_session_has_evidence** (Sprint 26)
   - Check if runtime session has full evidence attached
   - Returns True only if both session_record and evaluation exist

### What Runtime Flow Does NOT Do

- Create or own SessionRecord (evaluation pipeline)
- Persist state automatically
- Schedule future sessions
- Make autonomous curriculum decisions
- Merge multiple persistence layers

## Evidence Attachment (Sprint 26)

### Purpose

Evidence attachment links the execution layer (RuntimePracticeSession) with
the evaluation layer (SessionRecord + CoachEvaluation). This creates a
self-contained snapshot of practice execution with full evidence.

### Attachment Model

```
RuntimePracticeSession (execution wrapper)
├── assignment: AssembledPracticeAssignment (what to practice)
├── session_record: SessionRecord (what happened)
└── evaluation: CoachEvaluation (what it means)
```

Evidence is explicitly attached, not automatically linked:
1. Attach SessionRecord first (sets session_id)
2. Attach CoachEvaluation second (validates session_id match)

### Cross-Validation

Evidence attachment includes light validation:
- attach_evaluation requires session_record attached first
- attach_evaluation validates evaluation.session_id == session_record.session_id
- attach_runtime_evidence adds "session_evaluation_link_unverified" if mismatch

### Immutability

Evidence attachment returns new RuntimePracticeSession instances.
Original sessions remain unchanged. Caller persists updated sessions.

## Queue Integration

Runtime flow uses existing queue infrastructure:

```
PracticeQueue
└── ScheduledPracticeAssignment (status: queued → active → completed/abandoned)
```

Queue state changes flow through:
- `mark_assignment_active()` - on session start
- `mark_assignment_completed()` - via outcome integration
- `mark_assignment_abandoned()` - on explicit abandonment

Queue persistence remains caller-owned via PracticeQueueStore.

## Outcome Integration

Completion flows through Sprint 24's `process_assignment_outcome()`:

```
RuntimePracticeSession + PracticeOutcome
→ AssignmentOutcomeEvent
→ process_assignment_outcome()
→ AssignmentOutcomeProcessingResult
  ├── updated_queue
  ├── updated_progress_state
  ├── queue_event
  └── curriculum_recommendation
```

Abandonment bypasses outcome integration entirely.

## Runtime Lifecycle

```
pending → active → completed
                 → abandoned
                 → failed
```

- **pending**: Created but not started (not used in current implementation)
- **active**: Session in progress
- **completed**: Outcome processed successfully
- **abandoned**: Explicit escape without outcome
- **failed**: Processing error (reserved)

## Persistence Model

### RuntimeFlowStore

Stores RuntimeSessionEvent objects only:
- session_started
- session_completed
- session_abandoned
- outcome_processed
- session_record_attached (Sprint 26)
- evaluation_attached (Sprint 26)

Does NOT store:
- PracticeQueue or PracticeQueueEvent (use PracticeQueueStore)
- RuntimeSessionResult
- CurriculumProgressState

Single file: `runtime_events.jsonl`

### Persistence Responsibility

All runtime_flow.py functions are pure. Caller persists:

| What | Where |
|------|-------|
| PracticeQueueEvent | PracticeQueueStore |
| RuntimeSessionEvent | RuntimeFlowStore |
| CurriculumProgressState | Future store (caller-owned) |
| AssignmentOutcomeEvent | Optional audit store |

## Deterministic Execution

Runtime flow guarantees:

1. **No hidden automation** — Every state change is explicit
2. **No autonomous scheduling** — Caller controls when sessions start
3. **No background processes** — All operations are synchronous
4. **Inspectable state** — All inputs and outputs are serializable
5. **Testable** — Pure functions with no side effects

## Governance Rules

1. Runtime flow orchestrates existing systems only
2. Runtime sessions do not replace SessionRecord
3. Queue state changes remain append-only
4. Runtime completion must remain explicit
5. Autonomous scheduling is deferred to future sprints
6. Runtime orchestration must remain deterministic

## CLI Commands

```bash
# Start next available assignment
sg-coach runtime start-next \
    --queue queue.json \
    --assignments assignments.json \
    --pretty

# Complete with outcome
sg-coach runtime complete \
    --runtime-session runtime.json \
    --outcome completed \
    --queue queue.json \
    --progress progress.json \
    --pretty

# Abandon session
sg-coach runtime abandon \
    --runtime-session runtime.json \
    --queue queue.json \
    --pretty

# Attach evidence (Sprint 26)
sg-coach runtime attach-evidence \
    --runtime-session runtime.json \
    --session session.json \
    --evaluation evaluation.json \
    --pretty
```

## Limitations

Sprint 25 does NOT include:
- Streaming MIDI integration
- Real-time evaluation
- Browser UI
- Multiplayer sync
- Push notifications
- Autonomous scheduling
- Adaptive timing optimization
- Voice assistant workflows

These are deferred to future sprints.

## Version

- runtime_flow.py: 0.2.0 (Sprint 26: evidence attachment)
- runtime_flow_store.py: 0.1.0
- RuntimePracticeSession schema: 0.2 (Sprint 26: session_record, evaluation fields)
- RuntimeSessionResult schema: 0.1
- RuntimeSessionEvent schema: 0.2 (Sprint 26: attachment event types)
- RuntimeEvidenceAttachmentResult schema: 0.1 (Sprint 26)
