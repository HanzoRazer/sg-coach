"""
Adaptive Ranking — Reorder recommendations using learned effectiveness.

Sprint 5 Dev Order 5: Ranking only, no curriculum or UI.

This module provides:
- rank_recommendations(): Reorder actions using effectiveness profiles

Core rule: Ranking may reorder recommended actions,
but it must not add or remove actions.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sg_spec.schemas.action_mapping import (
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.learning_aggregation import (
    ActionEffectivenessProfile,
    LearningSignalAggregateSet,
)


# Confidence threshold for applying learned scores
CONFIDENCE_THRESHOLD = 0.3

# Weight for blending original vs learned scores
ORIGINAL_WEIGHT = 0.5
LEARNED_WEIGHT = 0.5


def _build_profile_lookup(
    profiles: LearningSignalAggregateSet,
) -> Dict[Tuple[DiagnosisCode, FeedbackActionType], ActionEffectivenessProfile]:
    """Build a lookup dict from profiles for fast access."""
    return {
        (p.diagnosis_code, p.action_type): p
        for p in profiles.profiles
    }


def _compute_learned_score(
    profile: Optional[ActionEffectivenessProfile],
) -> float:
    """
    Compute learned score from profile.

    Returns 0.0 if profile is None or confidence below threshold.
    """
    if profile is None:
        return 0.0
    if profile.confidence < CONFIDENCE_THRESHOLD:
        return 0.0
    return profile.average_weight * profile.confidence


def _compute_rank_score(
    original_priority: int,
    learned_score: float,
) -> float:
    """
    Compute blended rank score.

    Formula:
        rank_score = (original_priority * 0.5) + (learned_score * 0.5)
    """
    return (original_priority * ORIGINAL_WEIGHT) + (learned_score * LEARNED_WEIGHT)


def rank_recommendations(
    recommendations: ActionRecommendationSet,
    profiles: LearningSignalAggregateSet,
) -> ActionRecommendationSet:
    """
    Reorder recommendations using learned effectiveness profiles.

    Parameters
    ----------
    recommendations:
        The recommendation set to rank.
    profiles:
        Aggregated effectiveness profiles from user feedback.

    Returns
    -------
    A new ActionRecommendationSet with actions reordered by rank_score.
    Each action's params dict will contain:
    - rank_score: the blended score used for ordering
    - learned_score: the effectiveness-based score
    - original_priority: the original priority value

    Notes
    -----
    - Does not add or remove actions
    - Only applies profiles with confidence >= 0.3
    - Missing profiles treated as learned_score = 0.0
    - If finding_code is missing, returns original order
    """
    if not recommendations.actions:
        return recommendations

    # Build lookup for fast profile access
    profile_lookup = _build_profile_lookup(profiles)
    finding_code = recommendations.finding_code

    # Score each action
    scored_actions: List[Tuple[float, int, RecommendedAction]] = []
    for idx, action in enumerate(recommendations.actions):
        original_priority = action.priority if action.priority is not None else 0

        # Look up profile
        key = (finding_code, action.action_type)
        profile = profile_lookup.get(key)

        learned_score = _compute_learned_score(profile)
        rank_score = _compute_rank_score(original_priority, learned_score)

        # Store debug metadata in params
        new_params = dict(action.params)
        new_params["rank_score"] = rank_score
        new_params["learned_score"] = learned_score
        new_params["original_priority"] = original_priority

        # Create new action with updated params
        ranked_action = RecommendedAction(
            action_type=action.action_type,
            label=action.label,
            rationale=action.rationale,
            priority=action.priority,
            params=new_params,
            target_span_required=action.target_span_required,
        )

        # Store with negative rank_score for descending sort, idx for stability
        scored_actions.append((-rank_score, idx, ranked_action))

    # Sort by rank_score descending (negative for ascending sort), then by original index
    scored_actions.sort(key=lambda x: (x[0], x[1]))

    # Extract reordered actions
    reordered_actions = [action for _, _, action in scored_actions]

    # Return new recommendation set with reordered actions
    return ActionRecommendationSet(
        id=recommendations.id,
        finding_code=recommendations.finding_code,
        finding_id=recommendations.finding_id,
        actions=reordered_actions,
        source=recommendations.source,
        confidence=recommendations.confidence,
        version=recommendations.version,
    )


__all__ = [
    "rank_recommendations",
    "CONFIDENCE_THRESHOLD",
]
