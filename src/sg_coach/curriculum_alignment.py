"""
Curriculum Alignment — Goal-driven curriculum mapping and assignment selection.

Sprint 14: Static curriculum alignment.
Sprint 21: Migrated to use sg-curriculum as canonical authority.
Sprint 22: Added build_progression_recommendation() for curriculum sequencing.

This module provides:
- align_goal_to_curriculum(): Align a goal to curriculum content
- curriculum_reference_to_drill_reference(): Convert to DrillReference
- build_goal_driven_assignment(): Create assignment from alignment
- build_goal_driven_assignments(): Batch assignment generation
- build_progression_recommendation(): Get next curriculum step for a diagnosis

Core rules:
- Alignment is deterministic in v1
- sg-curriculum is the canonical curriculum authority
- Goals are aligned by DiagnosisCode
- Missing alignment becomes unresolved assignment, not exception
- Progression recommendations are deterministic (no ML)

Ownership: sg-coach (alignment logic)
Curriculum: sg-curriculum (canonical content)
Schemas: sg-spec (CurriculumReference, CurriculumAlignmentResult, CurriculumRecommendation)
"""
from __future__ import annotations

from typing import List, Mapping, Optional, Sequence

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.curriculum_alignment import (
    CurriculumAlignmentRequest,
    CurriculumAlignmentResult,
    CurriculumContentType,
    CurriculumReference,
)
from sg_spec.schemas.curriculum_progression import (
    CurriculumProgressState,
    CurriculumRecommendation,
)
from sg_spec.schemas.drill_resolution import DrillDifficulty, DrillReference
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.goal_tracking import GoalStatus, PracticeGoal
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)

from sg_curriculum import get_curriculum_for_diagnosis, get_next_curriculum_step


def align_goal_to_curriculum(
    request: CurriculumAlignmentRequest,
    *,
    registry: Optional[Mapping[DiagnosisCode, CurriculumReference]] = None,
) -> CurriculumAlignmentResult:
    """
    Align a practice goal to curriculum content.

    Parameters
    ----------
    request:
        The alignment request containing the goal.
    registry:
        Optional custom registry. If None, uses sg-curriculum canonical lookup.

    Returns
    -------
    CurriculumAlignmentResult with resolved=True if alignment found.

    Notes
    -----
    - Looks up by request.goal.diagnosis_code
    - Returns a deep copy of the registry reference (never mutates registry)
    - Sets goal_id on copied reference if goal has an id
    - Applies preferred_difficulty if provided in request
    """
    diagnosis_code = request.goal.diagnosis_code

    if registry is not None:
        # Custom registry provided (for testing)
        if diagnosis_code not in registry:
            return CurriculumAlignmentResult(
                resolved=False,
                request=request,
                reason="no_curriculum_alignment",
            )
        registry_ref = registry[diagnosis_code]
        copied_ref = registry_ref.model_copy(deep=True)
    else:
        # Use canonical sg-curriculum lookup
        refs = get_curriculum_for_diagnosis(diagnosis_code)
        if not refs:
            return CurriculumAlignmentResult(
                resolved=False,
                request=request,
                reason="no_curriculum_alignment",
            )
        # get_curriculum_for_diagnosis already returns deep copies
        copied_ref = refs[0]

    if request.goal.id is not None:
        copied_ref = CurriculumReference(
            content_id=copied_ref.content_id,
            title=copied_ref.title,
            content_type=copied_ref.content_type,
            source=copied_ref.source,
            diagnosis_code=copied_ref.diagnosis_code,
            goal_id=request.goal.id,
            difficulty=copied_ref.difficulty,
            tags=copied_ref.tags.copy(),
            params=copied_ref.params.copy(),
            version=copied_ref.version,
        )

    if request.preferred_difficulty is not None:
        copied_ref = CurriculumReference(
            content_id=copied_ref.content_id,
            title=copied_ref.title,
            content_type=copied_ref.content_type,
            source=copied_ref.source,
            diagnosis_code=copied_ref.diagnosis_code,
            goal_id=copied_ref.goal_id,
            difficulty=request.preferred_difficulty,
            tags=copied_ref.tags.copy(),
            params=copied_ref.params.copy(),
            version=copied_ref.version,
        )

    return CurriculumAlignmentResult(
        resolved=True,
        request=request,
        curriculum_reference=copied_ref,
    )


def curriculum_reference_to_drill_reference(
    reference: CurriculumReference,
) -> DrillReference:
    """
    Convert a CurriculumReference to a DrillReference.

    Parameters
    ----------
    reference:
        The curriculum reference to convert.

    Returns
    -------
    DrillReference with mapped fields.

    Raises
    ------
    ValueError:
        If reference.content_type is not CurriculumContentType.drill.

    Notes
    -----
    Field mapping:
    - content_id → drill_id
    - title → title
    - source → source
    - diagnosis_code → diagnosis_code
    - difficulty → difficulty
    - tags → tags
    - params → params
    - params["description"] → description (if present)
    """
    if reference.content_type != CurriculumContentType.drill:
        raise ValueError(
            f"Cannot convert non-drill content type to DrillReference: "
            f"{reference.content_type.value}"
        )

    description = reference.params.get("description")

    return DrillReference(
        drill_id=reference.content_id,
        title=reference.title,
        source=reference.source,
        description=description,
        diagnosis_code=reference.diagnosis_code,
        action_type=FeedbackActionType.assign_drill,
        difficulty=reference.difficulty,
        tags=reference.tags.copy(),
        params=reference.params.copy(),
    )


def _generate_assignment_id(goal: PracticeGoal) -> str:
    """Generate deterministic assignment ID from goal."""
    if goal.id is not None:
        return f"pa_{goal.id}"
    return f"pa_goal_{goal.diagnosis_code.value}"


def build_goal_driven_assignment(
    *,
    goal: PracticeGoal,
    alignment_result: CurriculumAlignmentResult,
) -> AssembledPracticeAssignment:
    """
    Build a practice assignment from a goal and alignment result.

    Parameters
    ----------
    goal:
        The practice goal.
    alignment_result:
        The curriculum alignment result.

    Returns
    -------
    AssembledPracticeAssignment, either ready (if resolved drill)
    or unresolved (if alignment failed or non-drill content).

    Notes
    -----
    - Assignment ID is deterministic from goal.id
    - Preserves goal_id and diagnosis_code in params
    - Unresolved alignments create unresolved assignments
    """
    assignment_id = _generate_assignment_id(goal)

    if not alignment_result.resolved:
        return AssembledPracticeAssignment(
            id=assignment_id,
            assignment_type=PracticeAssignmentType.unresolved,
            status=PracticeAssignmentStatus.unresolved,
            title=goal.title,
            instructions="No curriculum drill is currently aligned for this goal.",
            diagnosis_code=goal.diagnosis_code,
            reason=alignment_result.reason,
            params={
                "goal_id": goal.id,
                "source": "goal_driven_assignment",
            },
        )

    reference = alignment_result.curriculum_reference
    if reference is None or reference.content_type != CurriculumContentType.drill:
        return AssembledPracticeAssignment(
            id=assignment_id,
            assignment_type=PracticeAssignmentType.unresolved,
            status=PracticeAssignmentStatus.unresolved,
            title=goal.title,
            instructions="Aligned curriculum content is not a drill.",
            diagnosis_code=goal.diagnosis_code,
            reason="non_drill_content_type",
            params={
                "goal_id": goal.id,
                "content_type": reference.content_type.value if reference else None,
                "source": "goal_driven_assignment",
            },
        )

    drill = curriculum_reference_to_drill_reference(reference)

    return AssembledPracticeAssignment(
        id=assignment_id,
        assignment_type=PracticeAssignmentType.drill,
        status=PracticeAssignmentStatus.ready,
        title=reference.title,
        instructions=f"Practice this drill to address: {goal.title}",
        diagnosis_code=goal.diagnosis_code,
        action_type=FeedbackActionType.assign_drill,
        drill=drill,
        params={
            "goal_id": goal.id,
            "curriculum_content_id": reference.content_id,
            "source": "goal_driven_assignment",
        },
    )


def build_goal_driven_assignments(
    *,
    goals: Sequence[PracticeGoal],
    preferred_difficulty: Optional[DrillDifficulty] = None,
    registry: Optional[Mapping[DiagnosisCode, CurriculumReference]] = None,
) -> AssembledPracticeAssignmentSet:
    """
    Build practice assignments from multiple goals.

    Parameters
    ----------
    goals:
        List of practice goals.
    preferred_difficulty:
        Optional difficulty preference applied to all alignments.
    registry:
        Optional custom registry. If None, uses sg-curriculum canonical lookup.

    Returns
    -------
    AssembledPracticeAssignmentSet with assignments for actionable goals.

    Notes
    -----
    - Skips completed and abandoned goals
    - Includes active, improving, and regressed goals
    - Each goal produces one assignment (resolved or unresolved)
    """
    actionable_statuses = {
        GoalStatus.active,
        GoalStatus.improving,
        GoalStatus.regressed,
    }

    assignments: List[AssembledPracticeAssignment] = []

    for goal in goals:
        if goal.status not in actionable_statuses:
            continue

        request = CurriculumAlignmentRequest(
            goal=goal,
            preferred_difficulty=preferred_difficulty,
        )
        alignment_result = align_goal_to_curriculum(request, registry=registry)
        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assignments.append(assignment)

    return AssembledPracticeAssignmentSet(
        assignments=assignments,
        source="goal_driven_assignment_builder",
    )


def build_progression_recommendation(
    *,
    diagnosis_code: DiagnosisCode,
    progress_state: CurriculumProgressState,
) -> Optional[CurriculumRecommendation]:
    """
    Get the next curriculum step recommendation for a diagnosis.

    Parameters
    ----------
    diagnosis_code:
        The diagnosis code to get next step for.
    progress_state:
        Current student progress state (from caller's persistence).

    Returns
    -------
    CurriculumRecommendation if a next step exists, None otherwise.

    Notes
    -----
    This is the sg-coach wrapper for sg-curriculum's get_next_curriculum_step.
    It provides a consistent interface for curriculum progression within the
    coaching pipeline.

    Rules:
    1. Find progression path for diagnosis
    2. Skip completed content_ids
    3. Skip deferred content_ids (first pass)
    4. Return first incomplete step with prerequisite status
    5. Fall back to deferred content if nothing else available
    6. Return None if all content completed

    The caller is responsible for:
    - Constructing CurriculumProgressState from their persistence layer
    - Handling prerequisite_satisfied=False cases
    - Updating progress state when content is completed
    """
    return get_next_curriculum_step(
        diagnosis_code=diagnosis_code,
        progress_state=progress_state,
    )


__all__ = [
    "align_goal_to_curriculum",
    "curriculum_reference_to_drill_reference",
    "build_goal_driven_assignment",
    "build_goal_driven_assignments",
    "build_progression_recommendation",
]
