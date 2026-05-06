"""
Practice Assignment Assembler — Assemble next-step objects from coaching pipeline.

Sprint 9: Assembly behavior for practice assignments.

This module provides:
- assemble_practice_assignment(): Single assignment assembly
- assemble_practice_assignments(): Batch assembly from recommendation sets

Core rules:
1. Assignment assembly does not evaluate performance
2. Assignment assembly does not rank recommendations
3. Assignment assembly does not resolve drills itself
4. assign_drill requires a DrillResolutionResult
5. Missing drill resolution becomes unresolved assignment, not exception
6. Original recommendations are not mutated
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from sg_spec.schemas.action_mapping import (
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachFinding, TargetSpan
from sg_spec.schemas.drill_resolution import DrillResolutionResult
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
    generate_assignment_id,
)


def _assignment_type_from_action(
    action_type: FeedbackActionType,
) -> PracticeAssignmentType:
    """
    Map FeedbackActionType to PracticeAssignmentType.

    Parameters
    ----------
    action_type:
        The action type to map.

    Returns
    -------
    Corresponding PracticeAssignmentType, or unresolved if unknown.
    """
    mapping = {
        FeedbackActionType.assign_drill: PracticeAssignmentType.drill,
        FeedbackActionType.repeat: PracticeAssignmentType.repeat,
        FeedbackActionType.slow_down: PracticeAssignmentType.slow_down,
        FeedbackActionType.retry_section: PracticeAssignmentType.retry_section,
        FeedbackActionType.isolate: PracticeAssignmentType.isolate,
        FeedbackActionType.review_reference: PracticeAssignmentType.review,
    }
    return mapping.get(action_type, PracticeAssignmentType.unresolved)


def assemble_practice_assignment(
    *,
    finding: Optional[CoachFinding],
    recommendation: RecommendedAction,
    diagnosis_code: Optional[DiagnosisCode] = None,
    recommendation_set_id: Optional[str] = None,
    drill_resolution: Optional[DrillResolutionResult] = None,
) -> AssembledPracticeAssignment:
    """
    Assemble a single practice assignment from a recommendation.

    Parameters
    ----------
    finding:
        The source finding, if available.
    recommendation:
        The recommended action to convert.
    diagnosis_code:
        Explicit diagnosis code (overrides finding.code).
    recommendation_set_id:
        ID of the recommendation set (used as recommendation_id fallback).
    drill_resolution:
        Resolution result for assign_drill actions.

    Returns
    -------
    AssembledPracticeAssignment ready for rendering.

    Notes
    -----
    - assign_drill with resolved drill: status=ready, type=drill
    - assign_drill with unresolved drill: status=unresolved, type=unresolved
    - assign_drill with missing resolution: status=unresolved, reason=missing_drill_resolution
    - Other actions: status=ready, type=mapped from action_type
    """
    # Determine diagnosis code
    resolved_diagnosis_code: Optional[DiagnosisCode] = diagnosis_code
    if resolved_diagnosis_code is None and finding is not None:
        resolved_diagnosis_code = finding.code

    # Extract linkage IDs
    finding_id = finding.id if finding else None
    recommendation_id = recommendation_set_id

    # Extract target span from finding
    target_span = finding.target_span if finding else None

    # Extract ranking metadata from recommendation params (copy, don't mutate)
    params: Dict[str, Any] = dict(recommendation.params)
    personalized_rank_score = params.pop("personalized_rank_score", None)
    base_rank_score = params.pop("rank_score", None)
    rank_score = personalized_rank_score if personalized_rank_score is not None else base_rank_score

    # Handle assign_drill action
    if recommendation.action_type == FeedbackActionType.assign_drill:
        return _assemble_drill_assignment(
            recommendation=recommendation,
            drill_resolution=drill_resolution,
            resolved_diagnosis_code=resolved_diagnosis_code,
            finding_id=finding_id,
            recommendation_id=recommendation_id,
            target_span=target_span,
            rank_score=rank_score,
            params=params,
        )

    # Handle non-drill actions
    assignment_type = _assignment_type_from_action(recommendation.action_type)
    title = recommendation.label
    instructions = recommendation.rationale or recommendation.label

    return AssembledPracticeAssignment(
        id=generate_assignment_id(),
        assignment_type=assignment_type,
        status=PracticeAssignmentStatus.ready,
        title=title,
        instructions=instructions,
        diagnosis_code=resolved_diagnosis_code,
        action_type=recommendation.action_type,
        finding_id=finding_id,
        recommendation_id=recommendation_id,
        target_span=target_span,
        priority=recommendation.priority,
        rank_score=rank_score,
        params=params,
    )


def _assemble_drill_assignment(
    *,
    recommendation: RecommendedAction,
    drill_resolution: Optional[DrillResolutionResult],
    resolved_diagnosis_code: Optional[DiagnosisCode],
    finding_id: Optional[str],
    recommendation_id: Optional[str],
    target_span: Optional[TargetSpan],
    rank_score: Optional[float],
    params: Dict[str, Any],
) -> AssembledPracticeAssignment:
    """
    Assemble a drill-backed assignment.

    Handles three cases:
    1. drill_resolution is None: unresolved with missing_drill_resolution
    2. drill_resolution.resolved is False: unresolved with drill's reason
    3. drill_resolution.resolved is True: ready drill assignment
    """
    # Case 1: No drill resolution provided
    if drill_resolution is None:
        return AssembledPracticeAssignment(
            id=generate_assignment_id(),
            assignment_type=PracticeAssignmentType.unresolved,
            status=PracticeAssignmentStatus.unresolved,
            title=recommendation.label,
            instructions=recommendation.rationale or recommendation.label,
            diagnosis_code=resolved_diagnosis_code,
            action_type=recommendation.action_type,
            finding_id=finding_id,
            recommendation_id=recommendation_id,
            target_span=target_span,
            priority=recommendation.priority,
            rank_score=rank_score,
            reason="missing_drill_resolution",
            params=params,
        )

    # Case 2: Drill resolution failed
    if not drill_resolution.resolved:
        params_with_reason = dict(params)
        params_with_reason["drill_resolution_reason"] = drill_resolution.reason

        return AssembledPracticeAssignment(
            id=generate_assignment_id(),
            assignment_type=PracticeAssignmentType.unresolved,
            status=PracticeAssignmentStatus.unresolved,
            title=recommendation.label,
            instructions=recommendation.rationale or recommendation.label,
            diagnosis_code=resolved_diagnosis_code,
            action_type=recommendation.action_type,
            finding_id=finding_id,
            recommendation_id=recommendation_id,
            target_span=target_span,
            priority=recommendation.priority,
            rank_score=rank_score,
            reason=drill_resolution.reason or "drill_unresolved",
            params=params_with_reason,
        )

    # Case 3: Drill resolved successfully
    drill = drill_resolution.drill
    title = drill.title if drill else recommendation.label
    instructions = (
        drill.description
        if drill and drill.description
        else recommendation.rationale or recommendation.label
    )

    return AssembledPracticeAssignment(
        id=generate_assignment_id(),
        assignment_type=PracticeAssignmentType.drill,
        status=PracticeAssignmentStatus.ready,
        title=title,
        instructions=instructions,
        diagnosis_code=resolved_diagnosis_code,
        action_type=recommendation.action_type,
        finding_id=finding_id,
        recommendation_id=recommendation_id,
        drill=drill.model_copy(deep=True) if drill else None,
        target_span=target_span,
        priority=recommendation.priority,
        rank_score=rank_score,
        params=params,
    )


def _find_matching_drill_result(
    diagnosis_code: DiagnosisCode,
    action_type: FeedbackActionType,
    drill_results: Sequence[DrillResolutionResult],
) -> Optional[DrillResolutionResult]:
    """
    Find the first matching drill result for a diagnosis code and action type.

    In v1, the same DrillResolutionResult is used for all actions with the
    same (diagnosis_code, action_type) tuple.
    """
    for result in drill_results:
        if (
            result.request.diagnosis_code == diagnosis_code
            and result.request.action_type == action_type
        ):
            return result
    return None


def _find_matching_finding(
    finding_code: DiagnosisCode,
    findings: Sequence[CoachFinding],
) -> Optional[CoachFinding]:
    """Find the first matching finding for a diagnosis code."""
    for finding in findings:
        if finding.code == finding_code:
            return finding
    return None


def assemble_practice_assignments(
    *,
    findings: Optional[Sequence[CoachFinding]] = None,
    recommendation_sets: Sequence[ActionRecommendationSet],
    drill_results: Optional[Sequence[DrillResolutionResult]] = None,
) -> AssembledPracticeAssignmentSet:
    """
    Assemble practice assignments from recommendation sets.

    Parameters
    ----------
    findings:
        Source findings for linkage (optional).
    recommendation_sets:
        Recommendation sets to process.
    drill_results:
        Drill resolution results for assign_drill actions (optional).

    Returns
    -------
    AssembledPracticeAssignmentSet with all assembled assignments.

    Notes
    -----
    - Processes all actions in each recommendation set
    - Matches findings by finding_code
    - Matches drill results by (diagnosis_code, action_type)
    - Does not fail if no matching finding
    - Order matches original recommendation order
    """
    findings_list = list(findings) if findings else []
    drill_results_list = list(drill_results) if drill_results else []

    assignments: List[AssembledPracticeAssignment] = []

    for rec_set in recommendation_sets:
        # Find matching finding
        finding = _find_matching_finding(rec_set.finding_code, findings_list)

        for action in rec_set.actions:
            # Find matching drill result for assign_drill actions
            drill_result: Optional[DrillResolutionResult] = None
            if action.action_type == FeedbackActionType.assign_drill:
                drill_result = _find_matching_drill_result(
                    rec_set.finding_code,
                    action.action_type,
                    drill_results_list,
                )

            assignment = assemble_practice_assignment(
                finding=finding,
                recommendation=action,
                diagnosis_code=rec_set.finding_code,
                recommendation_set_id=rec_set.id,
                drill_resolution=drill_result,
            )
            assignments.append(assignment)

    return AssembledPracticeAssignmentSet(assignments=assignments)


__all__ = [
    "assemble_practice_assignment",
    "assemble_practice_assignments",
]
