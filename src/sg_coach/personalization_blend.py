"""
Personalization Blending — Blend user and global effectiveness for ranking.

Sprint 7: Personalization blending, no curriculum integration.

This module provides:
- compute_blended_effectiveness(): Blend user + global profiles
- compute_personalized_action_score(): Full score breakdown per action
- rank_recommendations_personalized(): Personalized ranking

Core rule: Personalized ranking is an additive layer,
not a replacement for existing ranking.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

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
from sg_spec.schemas.personalization import (
    PersonalizationBlendConfig,
    PersonalizedActionScore,
    PersonalizedRankingResult,
)


# Default config for blending
DEFAULT_CONFIG = PersonalizationBlendConfig()

# Weight for base priority vs blended effectiveness
BASE_PRIORITY_WEIGHT = 0.5
BLENDED_EFFECTIVENESS_WEIGHT = 0.5


def _find_effectiveness_profile(
    profiles: LearningSignalAggregateSet,
    diagnosis_code: DiagnosisCode,
    action_type: FeedbackActionType,
) -> Optional[ActionEffectivenessProfile]:
    """Find a profile matching the given diagnosis code and action type."""
    for profile in profiles.profiles:
        if (profile.diagnosis_code == diagnosis_code and
                profile.action_type == action_type):
            return profile
    return None


def compute_blended_effectiveness(
    *,
    user_profile: Optional[ActionEffectivenessProfile] = None,
    global_profile: Optional[ActionEffectivenessProfile] = None,
    config: Optional[PersonalizationBlendConfig] = None,
) -> float:
    """
    Compute blended effectiveness from user and global profiles.

    Parameters
    ----------
    user_profile:
        User-specific effectiveness profile (or None).
    global_profile:
        Global effectiveness profile (or None).
    config:
        Blending configuration. Uses defaults if None.

    Returns
    -------
    Blended effectiveness score.

    Notes
    -----
    - User profile applied only if confidence >= min_user_confidence
    - Global profile applied only if confidence >= min_global_confidence
    - If both valid: weighted blend
    - If only one valid: that score alone
    - If neither valid: 0.0
    """
    if config is None:
        config = DEFAULT_CONFIG

    user_valid = (
        user_profile is not None and
        user_profile.confidence >= config.min_user_confidence
    )
    global_valid = (
        global_profile is not None and
        global_profile.confidence >= config.min_global_confidence
    )

    user_score = 0.0
    global_score = 0.0

    if user_valid:
        user_score = user_profile.average_weight * user_profile.confidence

    if global_valid:
        global_score = global_profile.average_weight * global_profile.confidence

    if user_valid and global_valid:
        return (user_score * config.user_weight) + (global_score * config.global_weight)
    elif user_valid:
        return user_score
    elif global_valid:
        return global_score
    else:
        return 0.0


def compute_personalized_action_score(
    *,
    diagnosis_code: DiagnosisCode,
    action: RecommendedAction,
    user_profiles: Optional[LearningSignalAggregateSet] = None,
    global_profiles: Optional[LearningSignalAggregateSet] = None,
    config: Optional[PersonalizationBlendConfig] = None,
) -> PersonalizedActionScore:
    """
    Compute detailed personalized score for an action.

    Parameters
    ----------
    diagnosis_code:
        The diagnosis code for lookup.
    action:
        The action to score.
    user_profiles:
        User-specific effectiveness profiles.
    global_profiles:
        Global effectiveness profiles.
    config:
        Blending configuration.

    Returns
    -------
    PersonalizedActionScore with full breakdown.
    """
    if config is None:
        config = DEFAULT_CONFIG

    # Find matching profiles
    user_profile = None
    global_profile = None

    if user_profiles is not None:
        user_profile = _find_effectiveness_profile(
            user_profiles, diagnosis_code, action.action_type
        )

    if global_profiles is not None:
        global_profile = _find_effectiveness_profile(
            global_profiles, diagnosis_code, action.action_type
        )

    # Extract effectiveness and confidence values
    user_effectiveness = 0.0
    user_confidence = 0.0
    global_effectiveness = 0.0
    global_confidence = 0.0

    if user_profile is not None:
        user_effectiveness = user_profile.average_weight
        user_confidence = user_profile.confidence

    if global_profile is not None:
        global_effectiveness = global_profile.average_weight
        global_confidence = global_profile.confidence

    # Compute blended effectiveness
    blended_effectiveness = compute_blended_effectiveness(
        user_profile=user_profile,
        global_profile=global_profile,
        config=config,
    )

    # Compute final rank score
    base_priority = float(action.priority if action.priority is not None else 0)
    final_rank_score = (
        (base_priority * BASE_PRIORITY_WEIGHT) +
        (blended_effectiveness * BLENDED_EFFECTIVENESS_WEIGHT)
    )

    return PersonalizedActionScore(
        diagnosis_code=diagnosis_code,
        action_type=action.action_type,
        base_priority=base_priority,
        user_effectiveness=user_effectiveness,
        user_confidence=user_confidence,
        global_effectiveness=global_effectiveness,
        global_confidence=global_confidence,
        blended_effectiveness=blended_effectiveness,
        final_rank_score=final_rank_score,
    )


def rank_recommendations_personalized(
    recommendations: ActionRecommendationSet,
    *,
    user_profiles: Optional[LearningSignalAggregateSet] = None,
    global_profiles: Optional[LearningSignalAggregateSet] = None,
    config: Optional[PersonalizationBlendConfig] = None,
) -> PersonalizedRankingResult:
    """
    Rank recommendations using personalized blending.

    Parameters
    ----------
    recommendations:
        The recommendation set to rank.
    user_profiles:
        User-specific effectiveness profiles.
    global_profiles:
        Global effectiveness profiles.
    config:
        Blending configuration.

    Returns
    -------
    PersonalizedRankingResult with reordered actions and score breakdowns.

    Notes
    -----
    - Does not add or remove actions
    - Does not mutate original actions
    - Actions include debug params
    - Scores list matches action order after ranking
    """
    if not recommendations.actions:
        return PersonalizedRankingResult(
            recommendation_set=recommendations,
            scores=[],
        )

    diagnosis_code = recommendations.finding_code

    # Compute scores for each action
    scored_actions: List[Tuple[float, int, RecommendedAction, PersonalizedActionScore]] = []

    for idx, action in enumerate(recommendations.actions):
        score = compute_personalized_action_score(
            diagnosis_code=diagnosis_code,
            action=action,
            user_profiles=user_profiles,
            global_profiles=global_profiles,
            config=config,
        )

        # Create new action with debug params
        new_params = dict(action.params)
        new_params["personalized_rank_score"] = score.final_rank_score
        new_params["blended_effectiveness"] = score.blended_effectiveness
        new_params["base_priority"] = score.base_priority
        new_params["user_effectiveness"] = score.user_effectiveness
        new_params["user_confidence"] = score.user_confidence
        new_params["global_effectiveness"] = score.global_effectiveness
        new_params["global_confidence"] = score.global_confidence

        ranked_action = RecommendedAction(
            action_type=action.action_type,
            label=action.label,
            rationale=action.rationale,
            priority=action.priority,
            params=new_params,
            target_span_required=action.target_span_required,
        )

        # Store with negative score for descending sort, idx for stability
        scored_actions.append((-score.final_rank_score, idx, ranked_action, score))

    # Sort by final_rank_score descending, then by original index
    scored_actions.sort(key=lambda x: (x[0], x[1]))

    # Extract reordered actions and scores
    reordered_actions = [action for _, _, action, _ in scored_actions]
    reordered_scores = [score for _, _, _, score in scored_actions]

    # Build reordered recommendation set
    reordered_set = ActionRecommendationSet(
        id=recommendations.id,
        finding_code=recommendations.finding_code,
        finding_id=recommendations.finding_id,
        actions=reordered_actions,
        source=recommendations.source,
        confidence=recommendations.confidence,
        version=recommendations.version,
    )

    return PersonalizedRankingResult(
        recommendation_set=reordered_set,
        scores=reordered_scores,
    )


__all__ = [
    "compute_blended_effectiveness",
    "compute_personalized_action_score",
    "rank_recommendations_personalized",
]
