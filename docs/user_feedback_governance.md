# User Feedback Loop Governance

Sprint 5: Layer 2 foundation for learning whether coaching helped.

## Core Principle

```
Layer 2 records whether coaching helped.
Layer 2 does not change coaching behavior immediately.
```

This sprint defines contracts for user feedback. No learning logic is implemented.

## Schema Overview

### Enums

| Type | Values | Purpose |
|------|--------|---------|
| `UserFeedbackResponseType` | accepted, rejected, helped, did_not_help, too_easy, too_hard, misunderstood, user_marked_issue | How user responded |
| `PracticeOutcome` | repeated, improved, worsened, abandoned, completed | What happened after coaching |

### Models

| Type | Purpose |
|------|---------|
| `UserFeedbackEvent` | Append-only record of user feedback on a finding/recommendation |
| `LearningSignal` | Derived signal for future learning (schema only, not computed yet) |

## Field Semantics

### UserFeedbackEvent

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Optional[str]` | Stable identifier for this event |
| `session_id` | `Optional[str]` | Links to practice session |
| `finding_id` | `Optional[str]` | Links to CoachFinding.id |
| `recommendation_id` | `Optional[str]` | Links to ActionRecommendationSet.id |
| `response_type` | `UserFeedbackResponseType` | User's response category |
| `confidence` | `Optional[float]` | User's confidence in response (0.0-1.0) |
| `comment` | `Optional[str]` | Free-text explanation (max 500 chars) |
| `corrected_result` | `Optional[dict]` | Structured correction data |
| `timestamp` | `datetime` | When feedback was recorded |

### LearningSignal

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Optional[str]` | Stable identifier |
| `source_finding_code` | `DiagnosisCode` | Original diagnosis that triggered finding |
| `action_type` | `FeedbackActionType` | Action that was recommended |
| `user_response` | `UserFeedbackResponseType` | User's response |
| `outcome` | `PracticeOutcome` | What happened after |
| `weight` | `float` | Relative importance (0.0-10.0, default 1.0) |

## Recording Rules

### Append-Only

```
Feedback events are APPEND-ONLY.
Never mutate an existing UserFeedbackEvent.
Never delete feedback history.
```

### No Mutation of Source

```
Do NOT mutate original findings when recording feedback.
Do NOT overwrite recommendations based on feedback.
Findings and recommendations are immutable once created.
```

### Absence Is Not Rejection

```
Absence of feedback does NOT mean rejection.
Users may not provide feedback for most findings.
The system must not interpret silence as negative signal.
```

### Linkage Requirements

```
UserFeedbackEvent should link to at least one of:
- session_id
- finding_id
- recommendation_id

Orphan feedback (no links) is valid but less useful.
```

## corrected_result Structure

The `corrected_result` field is flexible structured data. Expected use cases:

```python
# Corrected note
{"corrected_note": "C#4", "original_note": "C4"}

# Corrected timing
{"corrected_beat": 2.5, "original_beat": 2.0, "unit": "beat"}

# User-marked span
{"start_bar": 3, "end_bar": 4, "issue": "fingering"}

# Perceived cause
{"cause": "string_buzz", "fret": 5, "string": 3}
```

Do not enforce rigid structure yet. Allow experimentation.

## Integration Points

### sg-agentd (Future)

```
Records UserFeedbackEvent when user provides feedback.
Does NOT compute LearningSignal — that's sg-coach's job.
Stores events in append-only log.
```

### sg-coach (Future)

```
Interprets feedback patterns.
Computes LearningSignal from events + outcomes.
Does NOT modify recommendations based on single events.
```

### sg-curriculum (Future)

```
Uses LearningSignal to adjust drill assignments.
Personalizes difficulty based on feedback history.
Does NOT access raw UserFeedbackEvent — uses signals only.
```

## ID Generation

IDs are `Optional[str]` in this sprint. Generation strategy:

```
- Use UUID4 string when creating events
- Format: "uf_" prefix for feedback events
- Format: "ls_" prefix for learning signals
- Do NOT require IDs — they're optional for backwards compatibility
```

Example:
```python
event = UserFeedbackEvent(
    id="uf_a1b2c3d4",
    session_id="sess_xyz",
    finding_id="find_123",
    response_type=UserFeedbackResponseType.helped,
)
```

## Response Type Semantics

| Type | User Intent | System Implication |
|------|-------------|-------------------|
| `accepted` | "Yes, this is correct" | Finding was accurate |
| `rejected` | "No, this is wrong" | Finding may be inaccurate |
| `helped` | "This helped my practice" | Recommendation was useful |
| `did_not_help` | "This didn't help" | Recommendation may need adjustment |
| `too_easy` | "This was below my level" | Difficulty calibration signal |
| `too_hard` | "This was above my level" | Difficulty calibration signal |
| `misunderstood` | "System misunderstood me" | Recognition/analysis issue |
| `user_marked_issue` | "I'm flagging this" | Requires human review |

## Practice Outcome Semantics

| Outcome | Meaning | Signal Strength |
|---------|---------|-----------------|
| `repeated` | User practiced again | Neutral |
| `improved` | Measurable improvement | Positive |
| `worsened` | Measurable decline | Negative |
| `abandoned` | User stopped | Strong negative |
| `completed` | User succeeded | Strong positive |

## What This Sprint Does NOT Do

1. **No learning logic** — LearningSignal is a schema, not computed
2. **No behavior change** — Recommendations don't adapt yet
3. **No UI** — No feedback collection interface
4. **No curriculum integration** — No drill adjustment
5. **No persistence** — No storage implementation

## Canonical Import Paths

```python
# From sg-spec
from sg_spec.schemas.user_feedback import (
    UserFeedbackResponseType,
    PracticeOutcome,
    UserFeedbackEvent,
    LearningSignal,
)

# Or via sg_spec.schemas
from sg_spec.schemas import UserFeedbackEvent, LearningSignal
```
