"""
Recommendation Integration — Attach action recommendations to CoachEvaluation.

Sprint 4: Integration contract between evaluation and recommendation.

This module provides the attach_recommendations() function that populates
the CoachEvaluation.recommendations field with action recommendations
derived from each finding.

Usage:
    from sg_coach import attach_recommendations

    # After evaluation
    evaluation = evaluate_session(session)
    evaluation_with_recs = attach_recommendations(evaluation)

    # Or in one step
    evaluation = attach_recommendations(evaluate_session(session))
"""
from __future__ import annotations

from typing import Mapping, Optional

from sg_spec.schemas.action_mapping import ActionMapping, ActionRecommendationSet
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

from .schemas import CoachEvaluation
from .action_recommender import recommend_actions_batch
from .default_action_mappings import DEFAULT_ACTION_MAPPINGS


def attach_recommendations(
    evaluation: CoachEvaluation,
    mappings: Optional[Mapping[DiagnosisCode, ActionMapping]] = None,
) -> CoachEvaluation:
    """
    Attach action recommendations to a CoachEvaluation.

    This function processes evaluation.findings through the recommendation
    engine and populates evaluation.recommendations with the results.

    Parameters
    ----------
    evaluation:
        The CoachEvaluation to enhance with recommendations.
    mappings:
        Optional mapping registry. If None, uses DEFAULT_ACTION_MAPPINGS.

    Returns
    -------
    A new CoachEvaluation with recommendations populated.

    Notes
    -----
    - Returns a new CoachEvaluation instance (immutable pattern)
    - Preserves all original evaluation fields
    - recommendations list matches findings list order
    - If evaluation has no findings, recommendations will be empty list
    """
    if mappings is None:
        mappings = DEFAULT_ACTION_MAPPINGS

    # Generate recommendations for all findings
    rec_sets = recommend_actions_batch(evaluation.findings, mappings)

    # Create new evaluation with recommendations
    return evaluation.model_copy(update={"recommendations": rec_sets})


__all__ = [
    "attach_recommendations",
]
