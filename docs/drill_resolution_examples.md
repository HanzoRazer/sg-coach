# Drill Resolution Examples

Sprint 8: Usage patterns for drill resolution.

## Basic Resolution

### Resolve a Single Drill

```python
from sg_coach import resolve_drill
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import DrillResolutionRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Create resolution request
request = DrillResolutionRequest(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type=FeedbackActionType.assign_drill,
    user_id="player_123",
)

# Resolve
result = resolve_drill(request)

if result.resolved:
    print(f"Drill: {result.drill.title}")
    print(f"Duration: {result.drill.estimated_duration_sec}s")
    print(f"Params: {result.drill.params}")
else:
    print(f"Resolution failed: {result.reason}")
```

Output:
```
Drill: Quarter Note Timing Reset
Duration: 120s
Params: {'tempo_bpm': 80, 'duration_bars': 8, 'threshold_ms': 30}
```

## Integration with Action Recommendations

### From Finding to Drills

```python
from sg_coach import (
    recommend_actions,
    resolve_drills_for_recommendations,
)
from sg_spec.schemas.coach_schemas import CoachFinding
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

# Assume we have a finding from evaluation
finding = CoachFinding(
    code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    severity="warn",
    message="Orbit drift detected",
)

# Get recommended actions
recommendations = recommend_actions(finding)

# Resolve drills for assign_drill actions
results = resolve_drills_for_recommendations(
    diagnosis_code=finding.code,
    recommendations=recommendations,
    user_id="player_123",
    session_id="sess_456",
)

for result in results:
    if result.resolved:
        print(f"Assigned: {result.drill.title}")
        print(f"  ID: {result.drill.drill_id}")
        print(f"  Tags: {result.drill.tags}")
```

Output:
```
Assigned: Diminished Orbit Isolation
  ID: diminished_orbit_isolation_v1
  Tags: ['diminished', 'arpeggio', 'orbit', 'isolation']
```

## Converting Actions to Requests

### Using request_from_recommended_action()

```python
from sg_coach import request_from_recommended_action, resolve_drill
from sg_spec.schemas.action_mapping import RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import TargetSpan
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Action with parameters
action = RecommendedAction(
    action_type=FeedbackActionType.assign_drill,
    label="Practice timing drill",
    params={"source": "coach_evaluation", "tempo": 80},
)

# Create request with full context
request = request_from_recommended_action(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action=action,
    user_id="player_123",
    session_id="sess_789",
    target_span=TargetSpan(start_time_sec=10.0, end_time_sec=15.0),
    context={"exercise_id": "ex_001"},
)

# Action params are copied to context
print(request.context)
# {'exercise_id': 'ex_001', 'action_params': {'source': 'coach_evaluation', 'tempo': 80}}

result = resolve_drill(request)
```

## Handling Non-Drill Actions

### Mixed Action Sets

```python
from sg_coach import resolve_drills_for_recommendations
from sg_spec.schemas.action_mapping import ActionRecommendationSet, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Recommendation set with mixed actions
recommendations = ActionRecommendationSet(
    finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    actions=[
        RecommendedAction(
            action_type=FeedbackActionType.slow_down,
            label="Reduce tempo",
        ),
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Timing drill",
        ),
        RecommendedAction(
            action_type=FeedbackActionType.repeat,
            label="Try again",
        ),
    ],
)

# Only assign_drill actions are resolved
results = resolve_drills_for_recommendations(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    recommendations=recommendations,
)

print(f"Total actions: {len(recommendations.actions)}")  # 3
print(f"Resolved drills: {len(results)}")  # 1
```

## Custom Catalog Testing

### Injecting Test Drills

```python
from sg_coach import resolve_drill
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import DrillReference, DrillResolutionRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Custom test catalog
test_catalog = {
    (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.assign_drill): DrillReference(
        drill_id="test_timing_v1",
        title="Test Timing Drill",
        difficulty="beginner",
        estimated_duration_sec=60,
    ),
}

request = DrillResolutionRequest(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type=FeedbackActionType.assign_drill,
)

# Uses test catalog instead of default
result = resolve_drill(request, catalog=test_catalog)

assert result.drill.drill_id == "test_timing_v1"
```

## Checking Catalog Coverage

### Verify Layer 1 Mappings Exist

```python
from sg_coach import resolve_drill
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import DrillResolutionRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

LAYER_1_CODES = [
    DiagnosisCode.DIM_ORBIT_VIOLATION,
    DiagnosisCode.TIMING_GRID_DEVIATION,
    DiagnosisCode.WRONG_NOTE,
    DiagnosisCode.PITCH_DEVIATION,
]

for code in LAYER_1_CODES:
    request = DrillResolutionRequest(
        diagnosis_code=code,
        action_type=FeedbackActionType.assign_drill,
    )
    result = resolve_drill(request)
    
    assert result.resolved, f"Missing drill for {code}"
    print(f"{code.value}: {result.drill.drill_id}")
```

Output:
```
dim_orbit_violation: diminished_orbit_isolation_v1
timing_grid_deviation: timing_grid_quarter_note_reset_v1
wrong_note: single_note_reference_recall_v1
pitch_deviation: pitch_centering_sustain_v1
```

## Full Pipeline Example

### Session → Findings → Drills

```python
from sg_coach import (
    evaluate_session,
    attach_recommendations,
    resolve_drills_for_recommendations,
)
from sg_spec.schemas.coach_schemas import SessionRecord, ProgramRef

# Create session
session = SessionRecord(
    session_id="sess_abc",
    user_id="player_123",
    program=ProgramRef(
        program_id="timing_101",
        program_type="rhythm",
        title="Timing Fundamentals",
    ),
)

# Evaluate session
evaluation = evaluate_session(session)

# Attach action recommendations to each finding
evaluation = attach_recommendations(evaluation)

# Resolve drills for each finding's recommendations
for finding in evaluation.findings:
    if finding.recommendations:
        results = resolve_drills_for_recommendations(
            diagnosis_code=finding.code,
            recommendations=finding.recommendations,
            user_id=session.user_id,
            session_id=session.session_id,
        )
        
        for result in results:
            if result.resolved:
                print(f"Finding: {finding.code.value}")
                print(f"  Drill: {result.drill.title}")
                print(f"  ID: {result.drill.drill_id}")
```
