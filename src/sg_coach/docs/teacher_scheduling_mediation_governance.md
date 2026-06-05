# Teacher Scheduling Mediation Governance

Sprint 31: Teacher-Adaptive Scheduling Mediation
Sprint 32: Teacher-Governed Adaptive Scheduling

## Overview

Teacher Scheduling Mediation provides human-in-the-loop governance over adaptive scheduling recommendations. Teachers have final authority over which recommendations apply to their students, with full audit trail preservation.

## Core Rules

1. **Teacher Authority is Final**: Teachers can approve, modify, reject, or defer any adaptive scheduling recommendation
2. **Mediations are Append-Only**: Re-mediation creates a new record with `prior_mediation_id` linking to the previous decision
3. **Queue Mutation is Caller-Controlled**: `apply_mediation_to_queue()` returns a new queue; callers decide whether to persist
4. **Full Audit Trail**: All mediations preserve original recommendation values in metadata

## Mediation Actions

| Action | Rationale Required | Override Required | Effect |
|--------|-------------------|-------------------|--------|
| `approve` | No | No | Apply recommendation as-is |
| `approve_modified` | Yes | Yes | Apply with teacher overrides |
| `reject` | Yes | No | Do not apply; record decision |
| `defer` | Yes | No | Delay decision; record deferral |

## ID Formats

- Recommendations: `asr_<12hex>` (from adaptive_scheduling)
- Mediations: `tsm_<12hex>`

## Usage

### Creating a Mediation

```python
from sg_coach import create_teacher_scheduling_mediation
from sg_spec.schemas.teacher_scheduling_mediation import MediationAction, TeacherSchedulingOverride
from sg_spec.schemas.practice_queue import PracticeQueuePriority

# Approve recommendation as-is
mediation = create_teacher_scheduling_mediation(
    recommendation=recommendation,
    teacher_id="teacher_001",
    action=MediationAction.approve,
)

# Approve with modifications
override = TeacherSchedulingOverride(
    recommended_priority=PracticeQueuePriority.critical,
    recommended_repetition_count=5,
)
mediation = create_teacher_scheduling_mediation(
    recommendation=recommendation,
    teacher_id="teacher_001",
    action=MediationAction.approve_modified,
    override=override,
    rationale="Student has upcoming recital",
)

# Reject recommendation
mediation = create_teacher_scheduling_mediation(
    recommendation=recommendation,
    teacher_id="teacher_001",
    action=MediationAction.reject,
    rationale="Student already working on this skill",
)
```

### Getting Effective Recommendation

```python
from sg_coach import effective_recommendation_from_mediation

# Returns modified recommendation for approve/approve_modified
# Returns None for reject/defer
effective = effective_recommendation_from_mediation(
    mediation=mediation,
    original_recommendation=recommendation,
)
```

### Applying to Queue

```python
from sg_coach import apply_mediation_to_queue

updated_queue = apply_mediation_to_queue(
    queue=queue,
    mediation=mediation,
    original_recommendation=recommendation,
)

# Caller decides whether to persist updated_queue
```

### CLI Commands

```bash
# Submit a mediation
sg-coach mediation submit \
  --recommendation rec.json \
  --teacher-id teacher_001 \
  --action approve

sg-coach mediation submit \
  --recommendation rec.json \
  --teacher-id teacher_001 \
  --action approve_modified \
  --rationale "Increased priority for recital prep" \
  --override-priority critical \
  --override-repetition 5

# Apply mediation to queue
sg-coach mediation apply \
  --mediation mediation.json \
  --recommendation rec.json \
  --queue queue.json
```

## Effective Scheduling Decision

For governance and audit purposes, use the `EffectiveSchedulingDecision` wrapper:

```python
from sg_coach import effective_scheduling_decision_from_mediation

decision = effective_scheduling_decision_from_mediation(
    recommendation=recommendation,
    mediation=mediation,
)

# Explicit governance flags
decision.approved    # True for approve/approve_modified
decision.rejected    # True for reject
decision.deferred    # True for defer

# Effective values (None for rejected/deferred)
decision.effective_priority
decision.effective_repetition_count
decision.effective_delay_days
```

## Mediation Store

Append-only persistence for mediations:

```python
from sg_coach import TeacherSchedulingMediationStore

store = TeacherSchedulingMediationStore("mediations.jsonl")

# Append mediation (immutable)
store.append_mediation(mediation)

# Query mediations
all_mediations = store.list_mediations()
teacher_mediations = store.list_mediations(teacher_id="teacher_001")
student_mediations = store.list_mediations(student_id="student_123")

# Get latest for recommendation
latest = store.latest_mediation_for_recommendation("asr_xyz789")
```

## Ledger Integration

Mediations create entries in the pedagogical evidence ledger:

```python
from sg_coach import ledger_entry_from_teacher_scheduling_mediation

entry = ledger_entry_from_teacher_scheduling_mediation(mediation)
# entry.source == PedagogicalEvidenceSource.teacher_scheduling_mediation
```

Severity mapping:

| Action | Severity |
|--------|----------|
| `approve` | informational |
| `approve_modified` | warning |
| `reject` | critical |
| `defer` | warning |

## Metadata Structure

Each mediation stores original values for audit:

```json
{
  "original_priority_adjustment": "increase",
  "original_recommended_priority": "high",
  "original_recommended_repetition_count": 3,
  "original_recommended_delay_days": null
}
```

When applied to queue assignments:

```json
{
  "teacher_scheduling_mediation": {
    "mediation_id": "tsm_abc123def456",
    "mediation_action": "approve_modified",
    "teacher_id": "teacher_001",
    "recommendation_id": "asr_xyz789",
    "rationale": "Adjusted for recital prep",
    "effective_priority": "critical",
    "effective_repetition_count": 5,
    "effective_delay_days": null
  }
}
```

## Re-mediation

To revise a prior decision:

```python
new_mediation = create_teacher_scheduling_mediation(
    recommendation=recommendation,
    teacher_id="teacher_001",
    action=MediationAction.approve,
    prior_mediation_id=old_mediation.id,  # Links to previous decision
    rationale="Changed approach after discussing with student",
)
```

## Versions

| Component | Version |
|-----------|---------|
| `TEACHER_SCHEDULING_MEDIATION_VERSION` | 0.1.0 |
| `TEACHER_SCHEDULING_MEDIATION_STORE_VERSION` | 0.1.0 |

## Governance Rules

1. Teacher mediation never mutates original recommendations
2. Teacher authority remains final
3. Queue mutation remains explicit (caller-controlled)
4. Mediation decisions become canonical evidence
5. Prior mediations are never overwritten
6. Hidden scheduling mutation is prohibited
