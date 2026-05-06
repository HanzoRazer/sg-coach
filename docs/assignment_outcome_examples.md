# Assignment Outcome Examples

Sprint 10: Usage patterns for assignment outcome tracking.

## Capturing Outcomes

### Completed Assignment

```python
from sg_coach import capture_assignment_outcome
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeCaptureRequest
from sg_spec.schemas.user_feedback import PracticeOutcome

# Create capture request
request = AssignmentOutcomeCaptureRequest(
    assignment_id="pa_timing123456",
    session_id="sess_001",
    user_id="player_123",
    outcome=PracticeOutcome.completed,
    confidence=1.0,
    comment="Finished all repetitions",
    source="agentd",
)

# Capture outcome
event = capture_assignment_outcome(request)

print(f"Event ID: {event.id}")  # ao_abc123def456
print(f"Outcome: {event.outcome}")  # completed
```

### Improved Assignment

```python
from sg_coach import capture_assignment_outcome
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeCaptureRequest
from sg_spec.schemas.user_feedback import PracticeOutcome

request = AssignmentOutcomeCaptureRequest(
    assignment_id="pa_timing123456",
    session_id="sess_002",
    user_id="player_123",
    outcome=PracticeOutcome.improved,
    confidence=0.9,
    comment="Much better timing accuracy",
    evidence={
        "timing_error_ms_before": 45,
        "timing_error_ms_after": 20,
        "improvement_percent": 55.5,
    },
    source="agentd",
)

event = capture_assignment_outcome(request)

print(f"Evidence: {event.evidence}")
# {'timing_error_ms_before': 45, 'timing_error_ms_after': 20, 'improvement_percent': 55.5}
```

### Abandoned Assignment

```python
from sg_coach import capture_assignment_outcome
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeCaptureRequest
from sg_spec.schemas.user_feedback import PracticeOutcome

request = AssignmentOutcomeCaptureRequest(
    assignment_id="pa_drill456789",
    session_id="sess_003",
    user_id="player_123",
    outcome=PracticeOutcome.abandoned,
    comment="Too difficult at current tempo",
    evidence={
        "attempts": 3,
        "last_error_rate": 0.45,
    },
    source="ui",
    interaction_context={
        "button_clicked": "skip",
        "time_spent_sec": 120,
    },
)

event = capture_assignment_outcome(request)

# Abandoned is coaching signal, not user failure
print(f"Outcome: {event.outcome}")  # abandoned
```

## Bridging to Feedback Pipeline

### Convert Outcome to Feedback Request

```python
from sg_coach import (
    capture_assignment_outcome,
    assignment_outcome_to_feedback_request,
    capture_feedback,
)
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeCaptureRequest
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.user_feedback import PracticeOutcome

# 1. Have an assignment
assignment = AssembledPracticeAssignment(
    id="pa_timing123456",
    assignment_type=PracticeAssignmentType.drill,
    status=PracticeAssignmentStatus.ready,
    title="Timing Drill",
    instructions="Practice quarter notes",
    finding_id="finding_timing_001",
    recommendation_id="rec_set_001",
)

# 2. Capture outcome
capture_request = AssignmentOutcomeCaptureRequest(
    assignment_id="pa_timing123456",
    session_id="sess_practice_001",
    user_id="player_123",
    outcome=PracticeOutcome.improved,
    confidence=0.9,
    evidence={"timing_error_ms": 20},
    source="agentd",
)

outcome_event = capture_assignment_outcome(capture_request)

# 3. Bridge to feedback request
feedback_request = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event,
)

print(f"Response type: {feedback_request.response_type}")  # helped
print(f"Finding ID: {feedback_request.finding_id}")  # finding_timing_001
print(f"Session ID: {feedback_request.session_id}")  # sess_practice_001
print(f"Context: {feedback_request.interaction_context}")
# {'assignment_id': 'pa_timing123456', 'assignment_type': 'drill', 'outcome_event_id': 'ao_...'}

# 4. Feed into existing pipeline
feedback_event = capture_feedback(feedback_request)
```

### Override Response Type

```python
from sg_coach import assignment_outcome_to_feedback_request
from sg_spec.schemas.user_feedback import (
    PracticeOutcome,
    UserFeedbackResponseType,
)

# Sometimes the user may override the auto-mapped response type
outcome_event = make_outcome_event(outcome=PracticeOutcome.completed)

feedback_request = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event,
    response_type=UserFeedbackResponseType.too_easy,  # Override
)

print(f"Response type: {feedback_request.response_type}")  # too_easy
```

## Response Type Mapping Reference

```python
from sg_coach import response_type_from_assignment_outcome
from sg_spec.schemas.user_feedback import PracticeOutcome

# Check all mappings
for outcome in PracticeOutcome:
    response = response_type_from_assignment_outcome(outcome)
    print(f"{outcome.value:12} → {response.value}")
```

Output:
```
repeated     → accepted
improved     → helped
worsened     → did_not_help
abandoned    → did_not_help
completed    → accepted
```

## Full Pipeline Integration

### From Assignment to Learning Signal

```python
from sg_coach import (
    assemble_practice_assignment,
    capture_assignment_outcome,
    assignment_outcome_to_feedback_request,
    capture_feedback,
    derive_learning_signal,
)
from sg_spec.schemas.action_mapping import RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.assignment_outcome import AssignmentOutcomeCaptureRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.user_feedback import PracticeOutcome

# 1. Assembly (Sprint 9)
assignment = assemble_practice_assignment(
    finding=finding,
    recommendation=action,
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    drill_resolution=drill_result,
)

# 2. User practices and we capture outcome (Sprint 10)
outcome_request = AssignmentOutcomeCaptureRequest(
    assignment_id=assignment.id,
    session_id="sess_001",
    user_id="player_123",
    outcome=PracticeOutcome.improved,
    confidence=0.95,
    evidence={"timing_improved": True},
    source="agentd",
)
outcome_event = capture_assignment_outcome(outcome_request)

# 3. Bridge to feedback pipeline
feedback_request = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event,
)

# 4. Continue through existing pipeline (Sprint 5)
feedback_event = capture_feedback(feedback_request)

learning_signal = derive_learning_signal(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type=FeedbackActionType.assign_drill,
    feedback=feedback_event,
)

print(f"Learning signal weight: {learning_signal.weight}")
# Positive weight = assignment was effective
```

## Edge Cases

### Session ID Fallback

```python
# Session ID comes from outcome event first
assignment = make_assignment(params={"session_id": "sess_from_params"})
outcome_event = make_outcome_event(session_id="sess_from_event")

feedback = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event,
)
print(feedback.session_id)  # sess_from_event

# Falls back to assignment.params if event has no session_id
outcome_event_no_session = make_outcome_event(session_id=None)
feedback2 = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event_no_session,
)
print(feedback2.session_id)  # sess_from_params
```

### Missing Linkage

```python
# Missing finding_id/recommendation_id doesn't block capture
assignment = AssembledPracticeAssignment(
    id="pa_test",
    assignment_type=PracticeAssignmentType.slow_down,
    status=PracticeAssignmentStatus.ready,
    title="Slow down",
    instructions="Reduce tempo",
    finding_id=None,  # Missing
    recommendation_id=None,  # Missing
)

feedback = assignment_outcome_to_feedback_request(
    assignment=assignment,
    outcome_event=outcome_event,
)

# Linkage is None but request still works
print(feedback.finding_id)  # None
print(feedback.recommendation_id)  # None
```
