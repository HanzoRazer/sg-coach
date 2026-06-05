# Teacher Review Governance

Sprint 19: Teacher-facing review layer for student practice inspection.

## Purpose

The teacher review layer lets teachers inspect student practice history, annotate sessions, and recommend next steps without changing the coaching core. Teacher input is additive metadata — it never mutates system findings, evaluations, or assignments.

## Teacher Review Model

### TeacherReview

Top-level container for teacher review:

```python
class TeacherReview(BaseModel):
    id: Optional[str]
    teacher_id: Optional[str]
    student_id: Optional[str]
    session_review: Optional[SessionReview]
    dashboard: Optional[PracticeDashboardData]
    playback: Optional[SessionPlaybackData]
    annotations: list[TeacherAnnotation]
    recommendations: list[TeacherRecommendation]
    generated_at: datetime
    version: str = "0.1"
```

### TeacherAnnotation

Teacher annotations on student practice:

```python
class TeacherAnnotation(BaseModel):
    id: str  # ta_<12hex>
    teacher_id: Optional[str]
    student_id: Optional[str]
    session_id: Optional[str]
    finding_id: Optional[str]
    assignment_id: Optional[str]
    annotation_type: TeacherAnnotationType
    text: str  # 1-1000 chars
    target_span: Optional[TargetSpan]
    timestamp: datetime
    metadata: dict[str, Any]
    version: str = "0.1"
```

Annotation types:
- `note` — general observation
- `correction` — technique correction
- `encouragement` — positive feedback
- `warning` — caution about habit/issue
- `assignment_adjustment` — adjustment to assignment

### TeacherRecommendation

Teacher recommendations for student:

```python
class TeacherRecommendation(BaseModel):
    id: str  # tr_<12hex>
    teacher_id: Optional[str]
    student_id: Optional[str]
    session_id: Optional[str]
    recommendation_type: TeacherRecommendationType
    text: str  # 1-1000 chars
    related_goal_id: Optional[str]
    related_assignment_id: Optional[str]
    related_finding_ids: list[str]
    priority: int  # 0-10
    timestamp: datetime
    metadata: dict[str, Any]
    version: str = "0.1"
```

Recommendation types:
- `reinforce_system_assignment` — agree with system assignment
- `modify_assignment` — adjust system assignment
- `add_assignment` — add new assignment
- `defer_goal` — postpone goal
- `mark_resolved` — mark issue as resolved

## Governance Rules

1. **Teacher review is additive.** Teacher annotations and recommendations are append-only metadata that do not modify system data.

2. **Teacher annotations do not mutate system findings.** Annotations reference findings but never change their content, severity, or diagnosis.

3. **Teacher recommendations do not override system recommendations in v1.** Teacher recommendations sit beside system recommendations and are not automatically integrated into ranking.

4. **Teacher input must remain traceable.** All annotations and recommendations include `teacher_id`, `timestamp`, and linkage IDs.

5. **Teacher review is local-first in v1.** Teacher data is stored in local JSONL files, not cloud infrastructure.

6. **Teacher/student identity is lightweight and non-authenticated in v1.** IDs are simple strings with no authentication or permission system.

## Append-Only Principle

Teacher annotations and recommendations are stored in append-only JSONL:

```python
class TeacherReviewStore:
    append_annotation(annotation)
    append_recommendation(recommendation)
    list_annotations(student_id=None, session_id=None)
    list_recommendations(student_id=None, session_id=None)
```

No delete or update operations exist. This preserves full audit trail.

## Teacher/System Separation

Teacher input and system coaching remain separate:

```text
CoachEvaluation → system findings
PracticeAssignment → system assignments
PracticeGoal → system goals

TeacherAnnotation → teacher observations
TeacherRecommendation → teacher suggestions
```

Future sprints may add teacher feedback integration to ranking, but v1 keeps them independent.

## Builder Usage

```python
from sg_coach import (
    build_teacher_review,
    create_teacher_annotation,
    create_teacher_recommendation,
    TeacherReviewStore,
)

# Build review for teacher inspection
review = build_teacher_review(
    history_store=store,
    session_id="session_001",
    student_id="student_001",
    teacher_id="teacher_001",
)

# Create annotation
annotation = create_teacher_annotation(
    annotation_type=TeacherAnnotationType.correction,
    text="Watch the timing on beat 3",
    teacher_id="teacher_001",
    student_id="student_001",
    session_id="session_001",
    finding_id="finding_001",
)

# Store annotation
teacher_store = TeacherReviewStore("teacher_data.jsonl")
teacher_store.append_annotation(annotation)
```

## CLI Usage

```bash
# Build teacher review
sg-coach teacher-review --history history.jsonl --student-id STUDENT --teacher-id TEACHER

# With session details
sg-coach teacher-review --history history.jsonl --session-id SESSION --pretty
```

## Future Dashboard Use

Teacher review data is designed for UI rendering:

```json
{
  "teacher_id": "teacher_001",
  "student_id": "student_001",
  "dashboard": { ... },
  "session_review": { ... },
  "playback": { ... },
  "annotations": [
    {
      "annotation_type": "correction",
      "text": "Watch the timing on beat 3",
      "finding_id": "finding_001"
    }
  ],
  "recommendations": [
    {
      "recommendation_type": "add_assignment",
      "text": "Add metronome drill at 80 BPM",
      "priority": 5
    }
  ]
}
```

## Limitations

- No authentication or permissions (v1)
- No cloud sync (local-first only)
- No automatic override of system recommendations
- No student messaging/notification
- No multi-teacher collaboration
- No curriculum authoring

## Definition of Done

Sprint 19 is complete when:
- TeacherReview schemas exist
- Teacher review builder works
- Annotation helper works with `ta_` prefix
- Recommendation helper works with `tr_` prefix
- TeacherReviewStore persists to JSONL
- `teacher-review` CLI command works
- All tests pass
- No system findings/evaluations/assignments are mutated
- No teacher override logic added
- No auth/cloud infrastructure added
