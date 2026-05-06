# Assignment Outcome Governance

Sprint 10: Assignment Outcome Tracking Contract

## Overview

The assignment outcome system tracks what happened after a practice assignment was delivered. Outcomes are recorded as events, not mutations to the original assignment. This document defines the contract between `sg_coach.assignment_outcome` and consumers.

## Core Principles

1. **Event-Based**: Outcomes are append-only events, not assignment mutations
2. **No Evaluation**: Capture does not evaluate performance
3. **No Ranking**: Capture does not update rankings directly
4. **Bridge to Feedback**: Outcomes convert to FeedbackCaptureRequest
5. **Coaching Signal**: Abandoned/worsened outcomes are signal, not user failure

## Pipeline Position

```
PracticeAssignment
→ AssignmentOutcomeEvent (Sprint 10) ← YOU ARE HERE
→ FeedbackCaptureRequest
→ UserFeedbackEvent
→ LearningSignal
```

## Schemas (sg_spec)

### AssignmentOutcomeEvent

A durable record of what happened after assignment delivery:
- `id: str | None` — Event ID (`ao_<12hex>`)
- `assignment_id: str` — ID of the source assignment
- `session_id: str | None` — Practice session ID
- `user_id: str | None` — User ID
- `instrument_id: str | None` — Instrument ID
- `outcome: PracticeOutcome` — What happened
- `confidence: float | None` — Confidence in outcome [0.0, 1.0]
- `comment: str | None` — Optional comment
- `evidence: dict` — Structured evidence
- `source: str | None` — Capture source
- `interaction_context: dict` — Flexible context
- `timestamp: datetime` — When recorded
- `version: str` — Schema version

### AssignmentOutcomeCaptureRequest

Input for capture before event creation:
- Same fields as event except no `id`, `timestamp`, or `version`

## Utility Functions

### capture_assignment_outcome()

```python
def capture_assignment_outcome(
    request: AssignmentOutcomeCaptureRequest,
    *,
    event_id: str | None = None,
    timestamp: datetime | None = None,
) -> AssignmentOutcomeEvent
```

**Behavior:**
- Generates `ao_<12hex>` ID if not provided
- Accepts explicit event_id for idempotency
- Accepts timestamp override
- Does not store anything
- Does not mutate any assignment

### response_type_from_assignment_outcome()

```python
def response_type_from_assignment_outcome(
    outcome: PracticeOutcome,
) -> UserFeedbackResponseType
```

**Mapping:**

| PracticeOutcome | UserFeedbackResponseType |
|-----------------|--------------------------|
| improved | helped |
| completed | accepted |
| repeated | accepted |
| worsened | did_not_help |
| abandoned | did_not_help |

### assignment_outcome_to_feedback_request()

```python
def assignment_outcome_to_feedback_request(
    *,
    assignment: AssembledPracticeAssignment,
    outcome_event: AssignmentOutcomeEvent,
    response_type: UserFeedbackResponseType | None = None,
) -> FeedbackCaptureRequest
```

**Behavior:**
- Preserves `finding_id`, `recommendation_id` from assignment
- Uses `outcome_event.session_id`, else `assignment.params.get("session_id")`
- Evidence becomes `corrected_result` if non-empty
- Adds `assignment_id`, `assignment_type`, `outcome_event_id` to context
- Explicit `response_type` overrides auto-mapping completely

## Invariants

1. Outcome events have unique IDs starting with `ao_`
2. Assignments are never mutated by outcome capture
3. Missing linkage (finding_id, recommendation_id) falls back to None
4. Empty evidence becomes None corrected_result
5. All PracticeOutcome values have a response type mapping

## Governance Rules

1. Assignment outcomes are events; assignments are not mutated
2. Outcome capture does not evaluate performance
3. Outcome capture does not update rankings directly
4. Outcome events may be converted into FeedbackCaptureRequest
5. Assignment outcome evidence must be structured
6. Abandoned/worsened outcomes are not user failure; they are coaching signal
7. Missing linkage should not block capture

## Ownership Boundaries

```
sg-spec     — Owns schemas
sg-coach    — Owns capture/conversion utilities
sg-agentd   — Later records outcome events during practice
sg-curriculum — Later uses outcomes for assignment progression
UI          — Later lets user confirm outcome
```

## Feedback Pipeline Integration

After capture, outcomes flow through the existing pipeline:

```
AssignmentOutcomeEvent
→ assignment_outcome_to_feedback_request()
→ FeedbackCaptureRequest
→ capture_feedback()
→ UserFeedbackEvent
→ derive_learning_signal()
→ LearningSignal
→ aggregate_effectiveness()
→ rank_recommendations_personalized()
```

This closes the loop from "Here is what to practice next" back into "Did that practice help?"

## Future Extensions

- Outcome storage in sg-agentd
- Automatic performance re-evaluation
- Assignment progression based on outcomes
- UI for outcome confirmation
