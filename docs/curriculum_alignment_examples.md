# Curriculum Alignment Examples

Sprint 14: Practical examples of goal-driven curriculum alignment.

## Example 1: Timing Goal to Drill Assignment

**Scenario:** Player has a timing weakness goal, align to curriculum.

```python
from sg_coach import (
    align_goal_to_curriculum,
    build_goal_driven_assignment,
)
from sg_spec.schemas.curriculum_alignment import CurriculumAlignmentRequest
from sg_spec.schemas.goal_tracking import PracticeGoal, GoalStatus
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

# Create goal from weakness
goal = PracticeGoal(
    id="goal_timing_grid_deviation",
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    title="Reduce timing grid deviations",
    description="Practice timing accuracy",
    status=GoalStatus.active,
)

# Align to curriculum
request = CurriculumAlignmentRequest(goal=goal)
alignment = align_goal_to_curriculum(request)

# Result:
# alignment.resolved = True
# alignment.curriculum_reference.content_id = "timing_grid_alignment_foundation_v1"
# alignment.curriculum_reference.title = "Timing Grid Alignment Foundation"
# alignment.curriculum_reference.goal_id = "goal_timing_grid_deviation"

# Build assignment
assignment = build_goal_driven_assignment(
    goal=goal,
    alignment_result=alignment,
)

# Result:
# assignment.id = "pa_goal_timing_grid_deviation"
# assignment.assignment_type = PracticeAssignmentType.drill
# assignment.status = PracticeAssignmentStatus.ready
# assignment.title = "Timing Grid Alignment Foundation"
# assignment.instructions = "Practice this drill to address: Reduce timing grid deviations"
# assignment.drill.drill_id = "timing_grid_alignment_foundation_v1"
```

## Example 2: Wrong Note Goal to Drill

**Scenario:** Player struggles with pitch accuracy.

```python
goal = PracticeGoal(
    id="goal_wrong_note",
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    title="Improve pitch accuracy",
    description="Practice note selection",
    status=GoalStatus.active,
)

request = CurriculumAlignmentRequest(goal=goal)
alignment = align_goal_to_curriculum(request)

# Result:
# alignment.curriculum_reference.content_id = "single_note_accuracy_foundation_v1"
# alignment.curriculum_reference.title = "Single Note Accuracy Foundation"
```

## Example 3: Completed Goal Skipped

**Scenario:** Player completed a goal, should not generate assignment.

```python
from sg_coach import build_goal_driven_assignments

goals = [
    PracticeGoal(
        id="goal_timing",
        diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        title="Timing goal",
        description="...",
        status=GoalStatus.completed,  # Completed!
    ),
    PracticeGoal(
        id="goal_pitch",
        diagnosis_code=DiagnosisCode.WRONG_NOTE,
        title="Pitch goal",
        description="...",
        status=GoalStatus.active,  # Active
    ),
]

result = build_goal_driven_assignments(goals=goals)

# Result:
# len(result.assignments) == 1  # Only the active goal
# result.assignments[0].diagnosis_code == DiagnosisCode.WRONG_NOTE
```

## Example 4: Missing Alignment (Unresolved)

**Scenario:** Goal has a diagnosis code not in the registry.

```python
goal = PracticeGoal(
    id="goal_rushing",
    diagnosis_code=DiagnosisCode.RUSHING,  # Not in default registry
    title="Stop rushing",
    description="Practice consistent tempo",
    status=GoalStatus.active,
)

request = CurriculumAlignmentRequest(goal=goal)
alignment = align_goal_to_curriculum(request)

# Result:
# alignment.resolved = False
# alignment.reason = "no_curriculum_alignment"
# alignment.curriculum_reference = None

assignment = build_goal_driven_assignment(
    goal=goal,
    alignment_result=alignment,
)

# Result:
# assignment.assignment_type = PracticeAssignmentType.unresolved
# assignment.status = PracticeAssignmentStatus.unresolved
# assignment.reason = "no_curriculum_alignment"
# assignment.instructions = "No curriculum drill is currently aligned for this goal."
```

## Example 5: Preferred Difficulty Override

**Scenario:** Request a harder drill than the default.

```python
from sg_spec.schemas.drill_resolution import DrillDifficulty

goal = PracticeGoal(
    id="goal_dim_orbit",
    diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    title="Stabilize diminished navigation",
    description="...",
    status=GoalStatus.active,
)

# Request advanced difficulty
request = CurriculumAlignmentRequest(
    goal=goal,
    preferred_difficulty=DrillDifficulty.advanced,
)
alignment = align_goal_to_curriculum(request)

# Result:
# Default registry has difficulty=beginner
# But request overrides to advanced
# alignment.curriculum_reference.difficulty == DrillDifficulty.advanced
```

## Example 6: Batch Goal Processing

**Scenario:** Process multiple goals at once.

```python
from sg_coach import (
    build_weakness_progressions,
    generate_practice_goals,
    build_goal_driven_assignments,
)

# Get progressions from history
progressions = build_weakness_progressions(
    history_store=store,
    user_id="student_001",
)

# Generate goals from progressions
goals = generate_practice_goals(progressions=progressions)

# Build assignments for all active goals
assignments = build_goal_driven_assignments(
    goals=goals,
    preferred_difficulty=DrillDifficulty.intermediate,
)

# Result:
# assignments.assignments contains one assignment per actionable goal
# Each assignment is either:
#   - ready drill (if alignment resolved)
#   - unresolved (if no alignment)
```

## Default Registry Contents

| DiagnosisCode | Content ID | Title |
|---------------|------------|-------|
| DIM_ORBIT_VIOLATION | diminished_orbit_navigation_foundation_v1 | Diminished Orbit Navigation Foundation |
| TIMING_GRID_DEVIATION | timing_grid_alignment_foundation_v1 | Timing Grid Alignment Foundation |
| WRONG_NOTE | single_note_accuracy_foundation_v1 | Single Note Accuracy Foundation |
| PITCH_DEVIATION | pitch_centering_foundation_v1 | Pitch Centering Foundation |

All default alignments:
- content_type = drill
- source = sg-coach
- difficulty = beginner

## Architecture Flow

```
Sprint 13 Goal Tracking
│
├── build_weakness_progressions()
│   └── list[WeaknessProgression]
│
├── generate_practice_goals()
│   └── list[PracticeGoal]
│
└── Sprint 14 Curriculum Alignment
    │
    ├── align_goal_to_curriculum()
    │   └── CurriculumAlignmentResult
    │
    ├── curriculum_reference_to_drill_reference()
    │   └── DrillReference
    │
    └── build_goal_driven_assignment()
        └── AssembledPracticeAssignment
```

**Key transformation:**

```
"You struggle with timing"
→
"Practice this timing drill because you struggle with timing."
```
