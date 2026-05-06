"""
Drill Resolver — Resolve actions to concrete drills.

Sprint 8: Resolver shell only, no curriculum automation.

This module provides:
- resolve_drill(): Resolve a single request to a drill
- request_from_recommended_action(): Create request from action
- resolve_drills_for_recommendations(): Batch resolve for recommendations

Core rule: Drill resolution should be deterministic, copy-safe,
and limited to assign_drill actions only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from sg_spec.schemas.action_mapping import (
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import TargetSpan
from sg_spec.schemas.drill_resolution import (
    DrillReference,
    DrillResolutionRequest,
    DrillResolutionResult,
)
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

from .drill_catalog import DEFAULT_DRILL_CATALOG


def resolve_drill(
    request: DrillResolutionRequest,
    *,
    catalog: Optional[Mapping[Tuple[DiagnosisCode, FeedbackActionType], DrillReference]] = None,
) -> DrillResolutionResult:
    """
    Resolve a drill request to a concrete drill.

    Parameters
    ----------
    request:
        The resolution request.
    catalog:
        Optional custom catalog. Uses DEFAULT_DRILL_CATALOG if None.

    Returns
    -------
    DrillResolutionResult with resolved drill or reason for failure.

    Notes
    -----
    - Only resolves assign_drill actions
    - Returns copy of catalog drill (not original)
    - Does not throw for missing drills
    """
    if catalog is None:
        catalog = DEFAULT_DRILL_CATALOG

    # Only resolve assign_drill actions
    if request.action_type != FeedbackActionType.assign_drill:
        return DrillResolutionResult(
            resolved=False,
            request=request,
            reason="unsupported_action_type",
        )

    # Lookup drill
    key = (request.diagnosis_code, request.action_type)
    drill = catalog.get(key)

    if drill is None:
        return DrillResolutionResult(
            resolved=False,
            request=request,
            reason="no_matching_drill",
        )

    # Return copy of drill
    return DrillResolutionResult(
        resolved=True,
        request=request,
        drill=drill.model_copy(deep=True),
    )


def request_from_recommended_action(
    *,
    diagnosis_code: DiagnosisCode,
    action: RecommendedAction,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    instrument_id: Optional[str] = None,
    target_span: Optional[TargetSpan] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DrillResolutionRequest:
    """
    Create a DrillResolutionRequest from a RecommendedAction.

    Parameters
    ----------
    diagnosis_code:
        The diagnosis code for the request.
    action:
        The recommended action to convert.
    user_id:
        Optional user ID.
    session_id:
        Optional session ID.
    instrument_id:
        Optional instrument ID.
    target_span:
        Optional target span from the finding.
    context:
        Optional additional context.

    Returns
    -------
    DrillResolutionRequest ready for resolve_drill().
    """
    request_context: Dict[str, Any] = dict(context) if context else {}

    # Copy action params into context if non-empty
    if action.params:
        request_context["action_params"] = action.params

    return DrillResolutionRequest(
        diagnosis_code=diagnosis_code,
        action_type=action.action_type,
        user_id=user_id,
        session_id=session_id,
        instrument_id=instrument_id,
        target_span=target_span,
        context=request_context,
    )


def resolve_drills_for_recommendations(
    *,
    diagnosis_code: DiagnosisCode,
    recommendations: ActionRecommendationSet,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    instrument_id: Optional[str] = None,
    target_span: Optional[TargetSpan] = None,
    catalog: Optional[Mapping[Tuple[DiagnosisCode, FeedbackActionType], DrillReference]] = None,
) -> List[DrillResolutionResult]:
    """
    Resolve drills for all assign_drill actions in a recommendation set.

    Parameters
    ----------
    diagnosis_code:
        The diagnosis code for resolution.
    recommendations:
        The recommendation set to process.
    user_id:
        Optional user ID.
    session_id:
        Optional session ID.
    instrument_id:
        Optional instrument ID.
    target_span:
        Optional target span.
    catalog:
        Optional custom catalog.

    Returns
    -------
    List of DrillResolutionResult for assign_drill actions only.

    Notes
    -----
    - Only processes assign_drill actions (skips others)
    - Order matches original action order
    """
    results: List[DrillResolutionResult] = []

    for action in recommendations.actions:
        # Only resolve assign_drill actions
        if action.action_type != FeedbackActionType.assign_drill:
            continue

        request = request_from_recommended_action(
            diagnosis_code=diagnosis_code,
            action=action,
            user_id=user_id,
            session_id=session_id,
            instrument_id=instrument_id,
            target_span=target_span,
        )

        result = resolve_drill(request, catalog=catalog)
        results.append(result)

    return results


__all__ = [
    "resolve_drill",
    "request_from_recommended_action",
    "resolve_drills_for_recommendations",
]
