# Practice Assignment Examples

Sprint 9: Usage patterns for practice assignment assembly.

## Single Assignment Assembly

### Non-Drill Assignment (slow_down)

```python
from sg_coach import assemble_practice_assignment
from sg_spec.schemas.action_mapping import RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachFinding
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Create finding
finding = CoachFinding(
    id="finding_001",
    type="timing",
    severity="primary",
    interpretation="Rushing on beat 2",
    code=DiagnosisCode.TIMING_GRID_DEVIATION,
)

# Create recommendation
action = RecommendedAction(
    action_type=FeedbackActionType.slow_down,
    label="Slow down tempo",
    rationale="Reduce tempo by 10 BPM to improve accuracy",
    priority=1,
)

# Assemble
assignment = assemble_practice_assignment(
    finding=finding,
    recommendation=action,
)

print(f"Type: {assignment.assignment_type}")  # slow_down
print(f"Status: {assignment.status}")  # ready
print(f"Title: {assignment.title}")  # Slow down tempo
print(f"Instructions: {assignment.instructions}")  # Reduce tempo by 10 BPM...
```

### Drill-Backed Assignment (assign_drill)

```python
from sg_coach import assemble_practice_assignment, resolve_drill
from sg_spec.schemas.action_mapping import RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import DrillResolutionRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Create drill resolution request
request = DrillResolutionRequest(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type=FeedbackActionType.assign_drill,
)

# Resolve drill
drill_result = resolve_drill(request)

# Create recommendation
action = RecommendedAction(
    action_type=FeedbackActionType.assign_drill,
    label="Practice timing drill",
    rationale="Work on quarter note accuracy",
    priority=2,
)

# Assemble with drill resolution
assignment = assemble_practice_assignment(
    finding=None,
    recommendation=action,
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    drill_resolution=drill_result,
)

print(f"Type: {assignment.assignment_type}")  # drill
print(f"Status: {assignment.status}")  # ready
print(f"Drill: {assignment.drill.title}")  # Quarter Note Timing Reset
```

### Unresolved Assignment (missing drill)

```python
from sg_coach import assemble_practice_assignment
from sg_spec.schemas.action_mapping import RecommendedAction
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Create assign_drill without resolution
action = RecommendedAction(
    action_type=FeedbackActionType.assign_drill,
    label="Practice drill",
)

# Assemble without drill resolution
assignment = assemble_practice_assignment(
    finding=None,
    recommendation=action,
    drill_resolution=None,  # Missing!
)

print(f"Type: {assignment.assignment_type}")  # unresolved
print(f"Status: {assignment.status}")  # unresolved
print(f"Reason: {assignment.reason}")  # missing_drill_resolution
```

## Batch Assembly

### Multiple Recommendations

```python
from sg_coach import assemble_practice_assignments, resolve_drill
from sg_spec.schemas.action_mapping import ActionRecommendationSet, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachFinding
from sg_spec.schemas.drill_resolution import DrillResolutionRequest
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Create finding
finding = CoachFinding(
    id="finding_timing",
    type="timing",
    severity="primary",
    interpretation="Timing issues detected",
    code=DiagnosisCode.TIMING_GRID_DEVIATION,
)

# Create recommendation set with multiple actions
rec_set = ActionRecommendationSet(
    id="rec_set_001",
    finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    finding_id="finding_timing",
    actions=[
        RecommendedAction(
            action_type=FeedbackActionType.slow_down,
            label="Reduce tempo",
            rationale="Slow down by 10 BPM",
            priority=1,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Timing drill",
            rationale="Practice quarter notes",
            priority=2,
            params={"personalized_rank_score": 0.92},
        ),
    ],
)

# Resolve drill for assign_drill action
request = DrillResolutionRequest(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type=FeedbackActionType.assign_drill,
)
drill_result = resolve_drill(request)

# Assemble all
result = assemble_practice_assignments(
    findings=[finding],
    recommendation_sets=[rec_set],
    drill_results=[drill_result],
)

print(f"Total assignments: {len(result.assignments)}")  # 2

for assignment in result.assignments:
    print(f"  {assignment.assignment_type}: {assignment.title}")
    print(f"    Status: {assignment.status}")
    print(f"    Finding ID: {assignment.finding_id}")
```

Output:
```
Total assignments: 2
  slow_down: Reduce tempo
    Status: ready
    Finding ID: finding_timing
  drill: Quarter Note Timing Reset
    Status: ready
    Finding ID: finding_timing
```

## Full Pipeline Integration

### From Evaluation to Assignments

```python
from sg_coach import (
    evaluate_session,
    attach_recommendations,
    rank_recommendations_personalized,
    resolve_drills_for_recommendations,
    assemble_practice_assignments,
)
from sg_spec.schemas.coach_schemas import SessionRecord, ProgramRef

# 1. Evaluate session
session = SessionRecord(
    session_id="...",
    instrument_id="guitar_001",
    engine_version="zt-band@0.2.0",
    program_ref=ProgramRef(type="ztprog", name="timing_101"),
    timing=SessionTiming(bpm=120, grid=8),
    duration_s=60,
)
evaluation = evaluate_session(session)

# 2. Attach recommendations
evaluation = attach_recommendations(evaluation)

# 3. Rank recommendations (personalized)
for i, rec_set in enumerate(evaluation.recommendations or []):
    ranked = rank_recommendations_personalized(
        recommendations=rec_set,
        user_profile=user_profile,
        global_profile=global_profile,
    )
    evaluation.recommendations[i] = ranked

# 4. Resolve drills
all_drill_results = []
for rec_set in evaluation.recommendations or []:
    results = resolve_drills_for_recommendations(
        diagnosis_code=rec_set.finding_code,
        recommendations=rec_set,
        user_id=str(session.instrument_id),
    )
    all_drill_results.extend(results)

# 5. Assemble practice assignments
assignment_set = assemble_practice_assignments(
    findings=evaluation.findings,
    recommendation_sets=evaluation.recommendations or [],
    drill_results=all_drill_results,
)

# 6. Display next steps
print("What to practice next:")
for assignment in assignment_set.assignments:
    if assignment.status == "ready":
        print(f"- {assignment.title}")
        print(f"  {assignment.instructions}")
        if assignment.drill:
            print(f"  Drill: {assignment.drill.drill_id}")
```

## Handling Edge Cases

### Mixed Resolved and Unresolved

```python
from sg_coach import assemble_practice_assignments
from sg_spec.schemas.action_mapping import ActionRecommendationSet, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import (
    DrillReference,
    DrillResolutionRequest,
    DrillResolutionResult,
)
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

# Two assign_drill actions
rec_set = ActionRecommendationSet(
    finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    actions=[
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Timing drill",
        ),
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Advanced timing drill",
        ),
    ],
)

# Only one drill resolves
resolved_result = DrillResolutionResult(
    resolved=True,
    request=DrillResolutionRequest(
        diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        action_type=FeedbackActionType.assign_drill,
    ),
    drill=DrillReference(
        drill_id="timing_drill_v1",
        title="Timing Drill",
    ),
)

# Assemble - both use the same resolved drill
result = assemble_practice_assignments(
    recommendation_sets=[rec_set],
    drill_results=[resolved_result],
)

# Both assignments get the same drill (v1 behavior)
assert result.assignments[0].drill.drill_id == "timing_drill_v1"
assert result.assignments[1].drill.drill_id == "timing_drill_v1"
```

### Action Type Mapping Reference

| FeedbackActionType | PracticeAssignmentType | Notes |
|-------------------|------------------------|-------|
| `slow_down` | `slow_down` | Direct mapping |
| `repeat` | `repeat` | Direct mapping |
| `isolate` | `isolate` | Direct mapping |
| `retry_section` | `retry_section` | Direct mapping |
| `review_reference` | `review` | Shortened |
| `assign_drill` | `drill` | Requires DrillResolutionResult |
| (unknown) | `unresolved` | Fallback |
