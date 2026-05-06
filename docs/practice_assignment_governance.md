# Practice Assignment Governance

Sprint 9: Practice Assignment Assembly Contract

## Overview

The practice assignment assembler turns coached findings and recommendations into concrete "next step" objects. This document defines the contract between `sg_coach.practice_assignment_assembler` and consumers.

## Core Principles

1. **Assembly Only**: Does not evaluate performance
2. **No Ranking**: Does not rank recommendations (uses existing rank_score)
3. **No Resolution**: Does not resolve drills itself (requires DrillResolutionResult)
4. **Mutation Safety**: Never mutates input recommendations
5. **Graceful Degradation**: Missing drill resolution becomes unresolved, not exception

## Pipeline Position

```
CoachEvaluation
→ ActionRecommendationSet (Sprint 4)
→ Ranked ActionRecommendationSet (Sprint 5/7)
→ DrillResolutionResult (Sprint 8)
→ PracticeAssignment (Sprint 9) ← YOU ARE HERE
```

## Schemas (sg_spec)

### PracticeAssignmentType

Enum of assignment kinds:
- `drill` — Backed by curriculum drill
- `repeat` — Repeat the passage
- `review` — Review reference material
- `slow_down` — Reduce tempo
- `retry_section` — Retry marked section
- `isolate` — Isolate difficult passage
- `unresolved` — Action could not be converted

### PracticeAssignmentStatus

Enum of assignment states:
- `ready` — Assignment is actionable
- `unresolved` — Drill resolution failed or missing
- `skipped` — Assignment was skipped (future)

### AssembledPracticeAssignment

A concrete next-step assignment:
- `id: str | None` — Auto-generated `pa_<12hex>`
- `assignment_type: PracticeAssignmentType` — Kind of assignment
- `status: PracticeAssignmentStatus` — Current state
- `title: str` — Display title
- `instructions: str` — What to do
- `diagnosis_code: DiagnosisCode | None` — Source finding code
- `action_type: FeedbackActionType | None` — Source action type
- `finding_id: str | None` — Linkage to source finding
- `recommendation_id: str | None` — Linkage to recommendation set
- `drill_resolution_id: str | None` — Linkage to drill resolution
- `drill: DrillReference | None` — Resolved drill (if drill-backed)
- `target_span: TargetSpan | None` — Location in exercise
- `priority: int` — From recommendation
- `rank_score: float | None` — Personalized ranking score
- `reason: str | None` — Why unresolved
- `params: dict` — Action parameters (minus rank scores)

### AssembledPracticeAssignmentSet

Container for batch assembly output:
- `assignments: list[AssembledPracticeAssignment]`
- `source: str` — Always "practice_assignment_assembler"
- `version: str` — Schema version

## Assembly Functions

### assemble_practice_assignment()

```python
def assemble_practice_assignment(
    *,
    finding: CoachFinding | None,
    recommendation: RecommendedAction,
    diagnosis_code: DiagnosisCode | None = None,
    recommendation_set_id: str | None = None,
    drill_resolution: DrillResolutionResult | None = None,
) -> AssembledPracticeAssignment
```

**Assignment Type Mapping:**

| FeedbackActionType | PracticeAssignmentType |
|-------------------|------------------------|
| assign_drill | drill |
| repeat | repeat |
| slow_down | slow_down |
| retry_section | retry_section |
| isolate | isolate |
| review_reference | review |
| (unknown) | unresolved |

### assemble_practice_assignments()

```python
def assemble_practice_assignments(
    *,
    findings: Sequence[CoachFinding] | None = None,
    recommendation_sets: Sequence[ActionRecommendationSet],
    drill_results: Sequence[DrillResolutionResult] | None = None,
) -> AssembledPracticeAssignmentSet
```

**Matching Behavior:**
- Findings matched by `finding_code`
- Drill results matched by `(diagnosis_code, action_type)`
- Same drill result used for all matching actions

## Drill-Backed Assignments

### Resolved Drill

When `action_type == assign_drill` and drill resolution succeeds:
- `status = ready`
- `assignment_type = drill`
- `drill = drill_resolution.drill` (deep copy)
- `title = drill.title`
- `instructions = drill.description or action.rationale`

### Unresolved Drill (Resolution Failed)

When drill resolution returns `resolved=False`:
- `status = unresolved`
- `assignment_type = unresolved`
- `reason = drill_resolution.reason`
- `params["drill_resolution_reason"] = reason`

### Unresolved Drill (Resolution Missing)

When `assign_drill` but no `drill_resolution` provided:
- `status = unresolved`
- `assignment_type = unresolved`
- `reason = "missing_drill_resolution"`

## Metadata Propagation

### Diagnosis Code

Priority order:
1. Explicit `diagnosis_code` parameter
2. `finding.code` if finding provided
3. `None`

### Finding Linkage

- `finding_id = finding.id` (if finding provided)
- `recommendation_id = recommendation_set_id` (RecommendedAction has no id)
- `target_span = finding.target_span` (if finding provided)

### Ranking Metadata

- `priority = recommendation.priority`
- `rank_score` extracted from params:
  1. `params["personalized_rank_score"]` (preferred)
  2. `params["rank_score"]` (fallback)
  3. `None`
- Both rank score keys removed from final `params`

## Invariants

1. Assignment ID always starts with `pa_`
2. `status=ready` implies assignment is actionable
3. `status=unresolved` implies `reason` is set
4. `assignment_type=drill` with `status=ready` implies `drill` is not None
5. Original recommendation params are never mutated
6. Action order is preserved in batch output

## Governance Rules

1. PracticeAssignment is a renderable next-step object
2. Assignment assembly must not evaluate performance
3. Assignment assembly must not rank recommendations
4. Assignment assembly must not resolve drills itself
5. assign_drill requires a DrillResolutionResult
6. Missing drill resolution becomes unresolved assignment, not exception
7. Assignments must preserve finding/recommendation linkage when available
8. Original recommendations must not be mutated

## Ownership Boundaries

```
sg-spec       — Owns schemas
sg-coach      — Owns assembly behavior
sg-curriculum — Later owns drill content
sg-agentd     — Later schedules/executes assignments
UI            — Later renders assignments
```

## Future Extensions

- Assignment scheduling in sg-agentd
- Assignment completion scoring
- Assignment history tracking
- UI rendering contracts
