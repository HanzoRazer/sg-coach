# Sprint 14: Curriculum Alignment & Goal-Driven Assignment Selection

**Date:** 2026-05-07
**Status:** COMPLETE

## Overview

Sprint 14 connects practice goals to curriculum-aware assignment selection:
- Static curriculum alignment registry
- Goal-to-curriculum mapping
- DrillReference conversion
- Goal-driven assignment generation

## Deliverables

### 1. Curriculum Alignment Schemas (sg-spec)

**File:** `sg_spec/schemas/curriculum_alignment.py`

Four schema definitions:
- `CurriculumContentType` — Enum: drill, exercise, lesson, review
- `CurriculumReference` — Reference to curriculum content
- `CurriculumAlignmentRequest` — Request to align a goal
- `CurriculumAlignmentResult` — Alignment result with reference or reason

**Tests:** 28 tests in `tests/test_curriculum_alignment_schema.py`

### 2. Curriculum Alignment Builders (sg-coach)

**File:** `sg_coach/curriculum_alignment.py`

Four builder functions:
- `align_goal_to_curriculum()` — Align goal to curriculum content
- `curriculum_reference_to_drill_reference()` — Convert to DrillReference
- `build_goal_driven_assignment()` — Create assignment from alignment
- `build_goal_driven_assignments()` — Batch assignment generation

Plus static registry:
- `DEFAULT_CURRICULUM_ALIGNMENTS` — Layer 1 diagnosis code mappings

**Tests:** 40 tests in `tests/test_curriculum_alignment.py`

### 3. Governance Documentation

**Files:**
- `docs/curriculum_alignment_governance.md` — Rules and limitations
- `docs/curriculum_alignment_examples.md` — Practical usage examples

## Test Summary

| Module | Tests |
|--------|-------|
| test_curriculum_alignment_schema.py (sg-spec) | 28 |
| test_curriculum_alignment.py (sg-coach) | 40 |
| **Total Sprint 14** | **68** |

## API Summary

### align_goal_to_curriculum

```python
def align_goal_to_curriculum(
    request: CurriculumAlignmentRequest,
    *,
    registry: Mapping[DiagnosisCode, CurriculumReference] | None = None,
) -> CurriculumAlignmentResult:
```

### curriculum_reference_to_drill_reference

```python
def curriculum_reference_to_drill_reference(
    reference: CurriculumReference,
) -> DrillReference:
```

### build_goal_driven_assignment

```python
def build_goal_driven_assignment(
    *,
    goal: PracticeGoal,
    alignment_result: CurriculumAlignmentResult,
) -> AssembledPracticeAssignment:
```

### build_goal_driven_assignments

```python
def build_goal_driven_assignments(
    *,
    goals: Sequence[PracticeGoal],
    preferred_difficulty: DrillDifficulty | None = None,
    registry: Mapping[DiagnosisCode, CurriculumReference] | None = None,
) -> AssembledPracticeAssignmentSet:
```

## Architecture Position

```
Sprint 13 (Goal Tracking)
├── build_weakness_progressions() → list[WeaknessProgression]
├── generate_practice_goals() → list[PracticeGoal]
└── update_goal_status() → PracticeGoal
        ↓
Sprint 14 (Curriculum Alignment)
├── align_goal_to_curriculum() → CurriculumAlignmentResult
├── curriculum_reference_to_drill_reference() → DrillReference
├── build_goal_driven_assignment() → AssembledPracticeAssignment
└── build_goal_driven_assignments() → AssembledPracticeAssignmentSet
```

## Key Design Decisions

1. **Static registry** — sg-coach owns temporary alignment registry
2. **Deterministic** — No ML or probabilistic matching
3. **Graceful degradation** — Missing alignment → unresolved assignment
4. **Registry immutability** — Never mutate registry objects
5. **Goal status filtering** — Skip completed/abandoned goals
6. **Difficulty override** — preferred_difficulty wins over registry default
7. **Deterministic IDs** — Assignment IDs from goal IDs

## Default Registry

| DiagnosisCode | Content ID |
|---------------|------------|
| DIM_ORBIT_VIOLATION | diminished_orbit_navigation_foundation_v1 |
| TIMING_GRID_DEVIATION | timing_grid_alignment_foundation_v1 |
| WRONG_NOTE | single_note_accuracy_foundation_v1 |
| PITCH_DEVIATION | pitch_centering_foundation_v1 |

## Governance Rules

1. Curriculum alignment is deterministic in v1
2. sg-coach registry is temporary
3. sg-curriculum becomes canonical content provider later
4. Goals are aligned by DiagnosisCode
5. Completed/abandoned goals do not generate assignments
6. Missing alignment becomes unresolved assignment, not exception
7. Alignment must preserve goal_id and diagnosis_code

## What Sprint 14 Enables

For the **player**:
- Get drill assignments that target persistent weaknesses
- See why a drill was assigned (linked to goal)
- Progress through goal-driven curriculum

For the **teacher**:
- Review student's goal-aligned assignments
- See connection between weaknesses and practice content
- Override assignments when sg-curriculum available

## Future Work (Sprint 15+)

1. sg-curriculum service integration
2. Dynamic content resolution
3. Exercise/lesson/review content types
4. Personalized content selection
5. Content versioning
6. Teacher assignment overrides
