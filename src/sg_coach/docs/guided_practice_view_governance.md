# Guided Practice View Governance

Sprint 34: Guided Practice Session UX Projection

## Overview

Guided Practice View provides UX-ready projection schemas that aggregate canonical coaching objects into compact, display-oriented views. The system is projection-only — it does not load stores, mutate state, or orchestrate workflows.

## Core Rules

1. **Projection-Only**: No mutation of source data; all functions produce new view objects
2. **No Store Loading**: All inputs are pre-built canonical objects, not store handles
3. **Graceful Partial Views**: Missing inputs produce partial views, not failures
4. **Deterministic Notes**: Notes generated via count-based rules (max 5 notes)
5. **Compact UX Schemas**: Sub-views contain summary data, not full canonical objects

## Schema Structure

### GuidedPracticeSessionView (Top-Level)

```
view_id: str (gpsv_<12hex>)
student_id: Optional[str]
runtime_session_id: Optional[str]
queue_id: Optional[str]
generated_at: datetime
assignment: Optional[GuidedPracticeAssignmentView]
playback: Optional[GuidedPracticePlaybackView]
adaptive_guidance: Optional[GuidedPracticeAdaptiveView]
teacher_mediation: Optional[GuidedPracticeTeacherMediationView]
timeline: Optional[PedagogicalTimelineView]
notes: list[str]
metadata: dict
```

### GuidedPracticeAssignmentView

```
assignment_id: str
title: str
assignment_type: PracticeAssignmentType
diagnosis_code: Optional[DiagnosisCode]
priority: Optional[PracticeQueuePriority]
status: Optional[PracticeQueueStatus]
runtime_active: bool (true when runtime session active for this assignment)
adaptive: bool (true when queue assignment has adaptive_scheduling metadata)
teacher_modified: bool (true when mediation action is approve_modified)
instructions_preview: Optional[str] (first 160 chars)
has_success_criteria: bool
has_coach_prompts: bool
metadata: dict
```

### GuidedPracticePlaybackView

```
playback_available: bool
runtime_session_id: Optional[str]
timeline_event_count: int
finding_overlay_count: int
active_finding_ids: list[str]
critical_overlay_count: int
metadata: dict
```

### GuidedPracticeAdaptiveView

```
recommendation_count: int
high_priority_count: int
critical_priority_count: int
active_recommendation_ids: list[str]
evidence_ids: list[str]
notes: list[str]
metadata: dict
```

### GuidedPracticeTeacherMediationView

```
mediation_count: int
latest_mediation_id: Optional[str]
approved_count: int
modified_count: int
rejected_count: int
deferred_count: int
teacher_override_count: int
notes: list[str]
metadata: dict
```

## ID Format

- Session View: `gpsv_<12hex>`

## Builder Functions

### Main Builder

```python
from sg_coach import build_guided_practice_session_view

view = build_guided_practice_session_view(
    queue=queue,                    # Optional[PracticeQueue]
    runtime_session=runtime_session, # Optional[RuntimePracticeSession]
    assignment=assignment,          # Optional[AssembledPracticeAssignment]
    playback=playback,              # Optional[SessionPlaybackData]
    adaptive_plan=adaptive_plan,    # Optional[AdaptiveSchedulingPlan]
    mediations=mediations,          # Sequence[TeacherSchedulingMediation]
    timeline=timeline,              # Optional[PedagogicalTimelineView]
    student_id=student_id,          # Optional[str]
)
```

### Sub-View Builders

```python
from sg_coach import (
    build_assignment_view,
    build_playback_view,
    build_adaptive_view,
    build_mediation_view,
)

assignment_view = build_assignment_view(
    assignment=assignment,
    queue=queue,
    runtime_session=runtime_session,
    mediations=mediations,
)

playback_view = build_playback_view(
    playback=playback,
    runtime_session=runtime_session,
)

adaptive_view = build_adaptive_view(adaptive_plan=adaptive_plan)

mediation_view = build_mediation_view(mediations=mediations)
```

## Projection Rules

### Instructions Preview
- First 160 characters of `assignment.instructions`
- `None` if instructions not present

### Runtime Active
- `True` when `runtime_session.assignment_id == assignment.assignment_id`

### Adaptive Flag
- `True` when `queue_assignment.metadata` contains `"adaptive_scheduling"` key

### Teacher Modified
- `True` when any matching mediation has `action == approve_modified`

### Has Success Criteria
- `True` if `assignment.success_criteria` exists and is non-empty

### Has Coach Prompts
- `True` if `assignment.coach_prompts` exists and is non-empty

## Deterministic Notes

Session-level notes (max 5):

1. No assignment → "No active practice assignment is available."
2. Runtime active → "Practice session is currently active."
3. Teacher modified → "Assignment has been modified by teacher."
4. No playback → "No playback data is available for this session."
5. Mediation active → "Teacher mediation is active for this student."
6. Timeline events → "Pedagogical timeline contains {N} events."

## CLI Usage

```bash
# Minimal view
sg-coach guided-session-view

# With all inputs
sg-coach guided-session-view \
  --queue queue.json \
  --runtime-session runtime_session.json \
  --assignment assignment.json \
  --playback playback.json \
  --adaptive-plan adaptive_plan.json \
  --mediations mediations.json \
  --timeline timeline.json \
  --student-id student_123 \
  --pretty
```

## Empty State Handling

| Missing Input | Behavior |
|---------------|----------|
| No assignment | `assignment = None`, note added |
| No playback | `playback.playback_available = False` |
| No adaptive plan | `adaptive_guidance.recommendation_count = 0` |
| No mediations | `teacher_mediation.mediation_count = 0` |
| No timeline | `timeline = None` |

## Integration Points

- **Inputs**: PracticeQueue, RuntimePracticeSession, AssembledPracticeAssignment, SessionPlaybackData, AdaptiveSchedulingPlan, TeacherSchedulingMediation, PedagogicalTimelineView
- **Output**: GuidedPracticeSessionView
- **Consumers**: Practice UI, student dashboards, teacher review screens
