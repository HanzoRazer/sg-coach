# Curriculum Alignment Governance

Sprint 14: Goal-driven curriculum alignment and assignment selection.

## Purpose

The curriculum alignment layer enables:
- Connecting practice goals to concrete curriculum content
- Goal-driven assignment generation
- Static alignment registry (temporary, sg-curriculum later)

It builds on Sprint 13 goal tracking to make assignments target long-term weaknesses.

## Static Alignment v1

**Current state:** sg-coach owns a static alignment registry.

**Future state:** sg-curriculum becomes the canonical content provider.

```
Sprint 14:
  sg-coach/curriculum_alignment.py
  → DEFAULT_CURRICULUM_ALIGNMENTS (static dict)
  → align_goal_to_curriculum()

Future:
  sg-curriculum service
  → catalog API
  → dynamic content resolution
```

## Ownership Boundaries

```
sg-spec
  owns CurriculumReference, CurriculumAlignmentResult contracts

sg-coach (temporary)
  owns static alignment registry
  owns alignment + assignment builders

sg-curriculum (future)
  owns canonical curriculum content
  owns dynamic resolution

sg-agentd (future)
  schedules selected assignments
```

## Goal-Driven Assignment Flow

```
PracticeGoal
│
├── CurriculumAlignmentRequest
│   └── diagnosis_code + preferred_difficulty
│
├── align_goal_to_curriculum()
│   └── lookup in registry by DiagnosisCode
│
├── CurriculumAlignmentResult
│   ├── resolved=True → CurriculumReference
│   └── resolved=False → reason="no_curriculum_alignment"
│
├── curriculum_reference_to_drill_reference()
│   └── CurriculumReference → DrillReference
│
└── build_goal_driven_assignment()
    └── AssembledPracticeAssignment
```

## Unresolved Behavior

Missing alignment produces an unresolved assignment, not an exception:

```
If alignment not found:
    assignment_type = unresolved
    status = unresolved
    reason = "no_curriculum_alignment"
    title = goal.title
    instructions = "No curriculum drill is currently aligned for this goal."
```

This allows the pipeline to continue and the UI to display a graceful message.

## Future sg-curriculum Integration

When sg-curriculum becomes available:

1. Replace `DEFAULT_CURRICULUM_ALIGNMENTS` with API calls
2. `align_goal_to_curriculum()` calls curriculum service
3. CurriculumReference becomes a pointer to catalog content
4. Content versioning handled by sg-curriculum

The contracts (CurriculumReference, CurriculumAlignmentResult) remain stable.

## Limitations

### v1 Limitations

1. **Static registry only** — No dynamic curriculum service
2. **Four codes mapped** — Only Layer 1 diagnosis codes
3. **No content versioning** — Static content IDs
4. **No personalization** — Same content for all users
5. **Drills only** — exercises/lessons/review not yet supported

### Architectural Boundaries

1. Curriculum alignment is deterministic in v1
2. sg-coach registry is temporary
3. Goals are aligned by DiagnosisCode
4. Missing alignment becomes unresolved, not exception
5. Completed/abandoned goals do not generate assignments
6. Registry objects must not be mutated

## Governance Rules

1. **Curriculum alignment is deterministic in v1.**
2. **sg-coach registry is temporary.**
3. **sg-curriculum becomes canonical content provider later.**
4. **Goals are aligned by DiagnosisCode.**
5. **Completed/abandoned goals do not generate assignments.**
6. **Missing alignment becomes unresolved assignment, not exception.**
7. **Alignment must preserve goal_id and diagnosis_code.**

## Definition of Done

Sprint 14 is complete when:

- [x] CurriculumAlignment schemas exist
- [x] Static alignment registry exists
- [x] Goals align to curriculum references
- [x] Curriculum references convert to drill references
- [x] Goal-driven assignments can be generated
- [x] Completed/abandoned goals are skipped
- [x] Unresolved alignments degrade gracefully
- [x] Tests pass
- [x] Docs committed
- [x] No sg-curriculum runtime dependency added yet

## API Reference

### align_goal_to_curriculum

```python
def align_goal_to_curriculum(
    request: CurriculumAlignmentRequest,
    *,
    registry: Mapping[DiagnosisCode, CurriculumReference] | None = None,
) -> CurriculumAlignmentResult:
```

Returns resolved result if diagnosis code found, unresolved otherwise.

### curriculum_reference_to_drill_reference

```python
def curriculum_reference_to_drill_reference(
    reference: CurriculumReference,
) -> DrillReference:
```

Raises ValueError if content_type is not drill.

### build_goal_driven_assignment

```python
def build_goal_driven_assignment(
    *,
    goal: PracticeGoal,
    alignment_result: CurriculumAlignmentResult,
) -> AssembledPracticeAssignment:
```

Returns ready drill assignment if resolved, unresolved assignment otherwise.

### build_goal_driven_assignments

```python
def build_goal_driven_assignments(
    *,
    goals: Sequence[PracticeGoal],
    preferred_difficulty: DrillDifficulty | None = None,
    registry: Mapping[DiagnosisCode, CurriculumReference] | None = None,
) -> AssembledPracticeAssignmentSet:
```

Processes active/improving/regressed goals, skips completed/abandoned.
