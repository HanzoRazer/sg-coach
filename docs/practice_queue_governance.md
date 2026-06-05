# Practice Queue Governance

Sprint 23: Assignment scheduling and practice queue management.

## Purpose

Sprint 23 introduces deterministic practice flow management, evolving Smart Guitar from:

```text
"What should the student learn next?"
```

into:

```text
"What should the student practice now?"
```

This creates the first persistent practice workflow engine inside the platform.

## Queue Architecture

### Queue vs. Curriculum

| Concern | Owner |
|---------|-------|
| Learning pathway | Curriculum Progression (Sprint 22) |
| Active execution workload | Practice Queue (Sprint 23) |

Queue state is separate from curriculum state. Do not merge them.

### Data Model

```text
PracticeQueue
├── id: queue_<12hex>
├── student_id: Optional
├── assignments: list[ScheduledPracticeAssignment]
└── generated_at: datetime

ScheduledPracticeAssignment
├── scheduled_id: sq_<12hex>
├── queue_id: reference to parent
├── assignment_id: reference to AssembledPracticeAssignment
├── status: queued|active|completed|deferred|abandoned
├── priority: low|normal|high|critical
├── scheduled_order: int (0-indexed)
├── estimated_minutes: Optional[int]
├── deferred_until: Optional[datetime]
└── metadata: dict
```

## Assignment Lifecycle

```text
                    ┌──────────┐
                    │  queued  │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌─────────┐ ┌──────────┐
         │ active │ │deferred │ │abandoned │
         └───┬────┘ └─────────┘ └──────────┘
             │
             ▼
       ┌───────────┐
       │ completed │
       └───────────┘
```

State transitions:
- `queued` → `active`: assignment_started event
- `queued` → `deferred`: assignment_deferred event
- `queued` → `abandoned`: assignment_abandoned event
- `active` → `completed`: assignment_completed event
- `active` → `deferred`: assignment_deferred event
- `active` → `abandoned`: assignment_abandoned event
- `deferred` → `active`: assignment_started event (when deferred_until passes)

## Priority Rules

Priority is determined from assignment fields only (no CoachFinding lookup):

| Condition | Priority |
|-----------|----------|
| `assignment.status == unresolved` | critical |
| `assignment.params.severity == "primary"` | high |
| `assignment.params.severity == "secondary"` | normal |
| `assignment.params.severity in ["info", "minor"]` | low |
| else | normal |

Priority ranking (highest first):
1. critical
2. high
3. normal
4. low

## Queue Sorting

`sort_practice_queue()` orders assignments by:
1. Priority descending (critical → low)
2. Scheduled order ascending (0, 1, 2...)
3. Created at ascending (oldest first)

Sorting is deterministic and reproducible.

## Persistence Model

### Event Sourcing

Queue state is rebuilt from append-only events:

```text
practice_queue.jsonl
├── assignment_scheduled → create queued item
├── assignment_started → active
├── assignment_completed → completed
├── assignment_deferred → deferred
└── assignment_abandoned → abandoned
```

### Idempotency

Duplicate `assignment_scheduled` events for the same `assignment_id` within a queue are ignored. This allows safe replay of events.

### Store Scope

Single JSONL file can contain multiple students/queues. Filter by `student_id` or `queue_id`.

## Deferred Assignment Handling

Deferred assignments with future `deferred_until`:
- Skipped by `next_queue_assignment()`
- Remain in queue with `status=deferred`

Deferred assignments with past `deferred_until`:
- Eligible for `next_queue_assignment()`
- Status remains `deferred` until explicit event changes it

Eligibility and status are separate concerns.

## Deterministic Scheduling

Queue ordering must remain:
- Explainable
- Inspectable
- Reproducible

No predictive workload models. No ML-based scheduling.

## Governance Rules

1. **Queue ordering remains deterministic.** No randomization or ML-based selection.
2. **Queue entries wrap assignments; they do not replace them.** Assignments remain canonical coaching outputs.
3. **Queue state changes are append-only events.** Never mutate existing events.
4. **Scheduling remains local-first.** No cloud scheduling infrastructure.
5. **Queue priority must remain explainable.** Derived from assignment fields only.
6. **AI scheduling is deferred.** Sprint 23 is deterministic foundation.

## Out of Scope

Sprint 23 does NOT implement:
- Calendar integration
- Reminders/notifications
- Spaced repetition algorithms
- AI scheduling
- Mobile sync
- Teacher scheduling workflows
- Estimated duration optimization
- Auto-generated schedules

These belong to future scheduling work after the deterministic foundation is established.

## Consumer Responsibilities

Callers must:
1. Build queue from assignments using `build_practice_queue()`
2. Get next eligible assignment using `next_queue_assignment()`
3. Update state using `mark_*` helpers or store methods
4. Handle `deferred_until` logic for scheduling UI
5. Store and load queue state using `PracticeQueueStore`

## Version

```python
QUEUE_VERSION = "0.1.0"
PRACTICE_QUEUE_STORE_VERSION = "0.1.0"
```

## Definition of Done

Sprint 23 is complete when:
- Practice queue schemas exist
- Queue builder works
- Queue sorting is deterministic
- Queue store rebuilds state from events
- Queue lifecycle transitions work
- Next assignment selection works
- CLI commands work
- Tests pass
- Docs committed
- Queue remains local-first
