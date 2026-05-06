"""
Tests for Personalization Blending.

Sprint 7: Tests for blending and personalized ranking.
"""
import pytest

from sg_coach.personalization_blend import (
    compute_blended_effectiveness,
    compute_personalized_action_score,
    rank_recommendations_personalized,
)
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
    PersonalizedRankingResult,
)


def make_profile(
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type: FeedbackActionType = FeedbackActionType.slow_down,
    average_weight: float = 1.0,
    confidence: float = 0.5,
) -> ActionEffectivenessProfile:
    """Helper to create test profiles."""
    return ActionEffectivenessProfile(
        diagnosis_code=diagnosis_code,
        action_type=action_type,
        average_weight=average_weight,
        signal_count=5,
        usable_signal_count=5,
        weak_signal_count=0,
        confidence=confidence,
    )


def make_profiles(
    profiles: list[ActionEffectivenessProfile],
) -> LearningSignalAggregateSet:
    """Helper to create profile sets."""
    return LearningSignalAggregateSet(
        profiles=profiles,
        total_signals=sum(p.signal_count for p in profiles),
    )


def make_action(
    action_type: FeedbackActionType = FeedbackActionType.slow_down,
    label: str = "Test action",
    priority: int = 5,
) -> RecommendedAction:
    """Helper to create test actions."""
    return RecommendedAction(
        action_type=action_type,
        label=label,
        priority=priority,
    )


def make_recommendations(
    actions: list[RecommendedAction],
    finding_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
) -> ActionRecommendationSet:
    """Helper to create test recommendation sets."""
    return ActionRecommendationSet(
        finding_code=finding_code,
        actions=actions,
    )


class TestComputeBlendedEffectiveness:
    """Test blending computation."""

    def test_no_profiles_returns_zero(self):
        result = compute_blended_effectiveness()
        assert result == 0.0

    def test_user_only_returns_user_score(self):
        user = make_profile(average_weight=1.0, confidence=0.5)

        result = compute_blended_effectiveness(user_profile=user)

        # user_score = 1.0 * 0.5 = 0.5
        assert result == pytest.approx(0.5)

    def test_global_only_returns_global_score(self):
        global_p = make_profile(average_weight=0.8, confidence=0.6)

        result = compute_blended_effectiveness(global_profile=global_p)

        # global_score = 0.8 * 0.6 = 0.48
        assert result == pytest.approx(0.48)

    def test_both_profiles_blend_70_30(self):
        user = make_profile(average_weight=1.0, confidence=0.5)
        global_p = make_profile(average_weight=0.6, confidence=0.5)

        result = compute_blended_effectiveness(
            user_profile=user,
            global_profile=global_p,
        )

        # user_score = 1.0 * 0.5 = 0.5
        # global_score = 0.6 * 0.5 = 0.3
        # blended = 0.5 * 0.7 + 0.3 * 0.3 = 0.35 + 0.09 = 0.44
        assert result == pytest.approx(0.44)

    def test_low_confidence_user_ignored(self):
        user = make_profile(average_weight=2.0, confidence=0.2)  # Below threshold
        global_p = make_profile(average_weight=0.5, confidence=0.5)

        result = compute_blended_effectiveness(
            user_profile=user,
            global_profile=global_p,
        )

        # User ignored, only global: 0.5 * 0.5 = 0.25
        assert result == pytest.approx(0.25)

    def test_low_confidence_global_ignored(self):
        user = make_profile(average_weight=1.0, confidence=0.5)
        global_p = make_profile(average_weight=2.0, confidence=0.2)  # Below threshold

        result = compute_blended_effectiveness(
            user_profile=user,
            global_profile=global_p,
        )

        # Global ignored, only user: 1.0 * 0.5 = 0.5
        assert result == pytest.approx(0.5)

    def test_both_low_confidence_returns_zero(self):
        user = make_profile(average_weight=1.0, confidence=0.2)
        global_p = make_profile(average_weight=1.0, confidence=0.1)

        result = compute_blended_effectiveness(
            user_profile=user,
            global_profile=global_p,
        )

        assert result == 0.0

    def test_custom_config_changes_weights(self):
        user = make_profile(average_weight=1.0, confidence=0.5)
        global_p = make_profile(average_weight=1.0, confidence=0.5)

        config = PersonalizationBlendConfig(
            user_weight=0.5,
            global_weight=0.5,
        )

        result = compute_blended_effectiveness(
            user_profile=user,
            global_profile=global_p,
            config=config,
        )

        # Both score = 0.5
        # blended = 0.5 * 0.5 + 0.5 * 0.5 = 0.5
        assert result == pytest.approx(0.5)

    def test_custom_confidence_threshold(self):
        user = make_profile(average_weight=1.0, confidence=0.4)

        config = PersonalizationBlendConfig(min_user_confidence=0.5)

        result = compute_blended_effectiveness(
            user_profile=user,
            config=config,
        )

        # User below custom threshold
        assert result == 0.0


class TestComputePersonalizedActionScore:
    """Test action score computation."""

    def test_computes_final_rank_score(self):
        user_profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.0,
                confidence=0.5,
            ),
        ])
        action = make_action(FeedbackActionType.slow_down, priority=6)

        score = compute_personalized_action_score(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            user_profiles=user_profiles,
        )

        # user_score = 1.0 * 0.5 = 0.5
        # final = 6 * 0.5 + 0.5 * 0.5 = 3.0 + 0.25 = 3.25
        assert score.final_rank_score == pytest.approx(3.25)

    def test_base_priority_contributes(self):
        action = make_action(priority=10)

        score = compute_personalized_action_score(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
        )

        # No profiles, blended = 0
        # final = 10 * 0.5 + 0 * 0.5 = 5.0
        assert score.final_rank_score == pytest.approx(5.0)
        assert score.base_priority == 10.0

    def test_includes_breakdown_fields(self):
        user_profiles = make_profiles([
            make_profile(average_weight=1.2, confidence=0.8),
        ])
        global_profiles = make_profiles([
            make_profile(average_weight=0.6, confidence=0.5),
        ])
        action = make_action()

        score = compute_personalized_action_score(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            user_profiles=user_profiles,
            global_profiles=global_profiles,
        )

        assert score.user_effectiveness == 1.2
        assert score.user_confidence == 0.8
        assert score.global_effectiveness == 0.6
        assert score.global_confidence == 0.5

    def test_missing_profile_zeros(self):
        action = make_action(FeedbackActionType.repeat)
        user_profiles = make_profiles([
            make_profile(action_type=FeedbackActionType.slow_down),
        ])

        score = compute_personalized_action_score(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            user_profiles=user_profiles,
        )

        assert score.user_effectiveness == 0.0
        assert score.user_confidence == 0.0
        assert score.blended_effectiveness == 0.0


class TestRankRecommendationsPersonalized:
    """Test personalized ranking."""

    def test_returns_personalized_ranking_result(self):
        recommendations = make_recommendations([make_action()])

        result = rank_recommendations_personalized(recommendations)

        assert isinstance(result, PersonalizedRankingResult)

    def test_recommendation_set_action_count_unchanged(self):
        actions = [make_action() for _ in range(3)]
        recommendations = make_recommendations(actions)

        result = rank_recommendations_personalized(recommendations)

        assert len(result.recommendation_set.actions) == 3

    def test_scores_count_matches_actions(self):
        actions = [make_action() for _ in range(3)]
        recommendations = make_recommendations(actions)

        result = rank_recommendations_personalized(recommendations)

        assert len(result.scores) == 3

    def test_reorders_by_blended_score(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow", priority=5),
            make_action(FeedbackActionType.repeat, label="Repeat", priority=5),
        ]
        recommendations = make_recommendations(actions)

        user_profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.repeat,
                average_weight=1.5,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations_personalized(
            recommendations,
            user_profiles=user_profiles,
        )

        # repeat has higher effectiveness, should be first
        assert result.recommendation_set.actions[0].label == "Repeat"

    def test_tie_preserves_original_order(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="First", priority=5),
            make_action(FeedbackActionType.repeat, label="Second", priority=5),
        ]
        recommendations = make_recommendations(actions)

        result = rank_recommendations_personalized(recommendations)

        # Same scores, original order preserved
        assert result.recommendation_set.actions[0].label == "First"
        assert result.recommendation_set.actions[1].label == "Second"

    def test_debug_params_attached(self):
        recommendations = make_recommendations([make_action(priority=5)])

        result = rank_recommendations_personalized(recommendations)
        action = result.recommendation_set.actions[0]

        assert "personalized_rank_score" in action.params
        assert "blended_effectiveness" in action.params
        assert "base_priority" in action.params
        assert "user_effectiveness" in action.params
        assert "user_confidence" in action.params
        assert "global_effectiveness" in action.params
        assert "global_confidence" in action.params

    def test_original_actions_not_mutated(self):
        original_action = make_action()
        original_params = dict(original_action.params)
        recommendations = make_recommendations([original_action])

        rank_recommendations_personalized(recommendations)

        assert original_action.params == original_params

    def test_empty_recommendations(self):
        recommendations = make_recommendations([])

        result = rank_recommendations_personalized(recommendations)

        assert result.recommendation_set.actions == []
        assert result.scores == []

    def test_empty_profiles_preserves_order(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="A", priority=3),
            make_action(FeedbackActionType.repeat, label="B", priority=7),
        ]
        recommendations = make_recommendations(actions)

        result = rank_recommendations_personalized(recommendations)

        # Higher priority ranks higher
        assert result.recommendation_set.actions[0].label == "B"
        assert result.recommendation_set.actions[1].label == "A"

    def test_preserves_recommendation_set_metadata(self):
        recommendations = ActionRecommendationSet(
            id="rec_123",
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            finding_id="find_456",
            actions=[make_action()],
            source="test",
            confidence=0.9,
        )

        result = rank_recommendations_personalized(recommendations)

        assert result.recommendation_set.id == "rec_123"
        assert result.recommendation_set.finding_id == "find_456"
        assert result.recommendation_set.source == "test"
        assert result.recommendation_set.confidence == 0.9


class TestIntegration:
    """Integration tests for full personalization flow."""

    def test_full_personalization_flow(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow", priority=5),
            make_action(FeedbackActionType.repeat, label="Repeat", priority=5),
            make_action(FeedbackActionType.isolate, label="Isolate", priority=5),
        ]
        recommendations = make_recommendations(actions)

        user_profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.5,
                confidence=0.8,
            ),
        ])

        global_profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.repeat,
                average_weight=0.8,
                confidence=0.6,
            ),
        ])

        result = rank_recommendations_personalized(
            recommendations,
            user_profiles=user_profiles,
            global_profiles=global_profiles,
        )

        # slow_down: user_score = 1.5 * 0.8 = 1.2
        # repeat: global_score = 0.8 * 0.6 = 0.48
        # isolate: no profiles, blended = 0

        # slow_down: final = 5*0.5 + 1.2*0.5 = 3.1
        # repeat: final = 5*0.5 + 0.48*0.5 = 2.74
        # isolate: final = 5*0.5 + 0*0.5 = 2.5

        labels = [a.label for a in result.recommendation_set.actions]
        assert labels == ["Slow", "Repeat", "Isolate"]

        # Verify scores
        assert result.scores[0].final_rank_score == pytest.approx(3.1)
        assert result.scores[1].final_rank_score == pytest.approx(2.74)
        assert result.scores[2].final_rank_score == pytest.approx(2.5)

    def test_user_and_global_blend(self):
        action = make_action(priority=4)
        recommendations = make_recommendations([action])

        user_profiles = make_profiles([
            make_profile(average_weight=1.0, confidence=0.5),
        ])
        global_profiles = make_profiles([
            make_profile(average_weight=0.6, confidence=0.5),
        ])

        result = rank_recommendations_personalized(
            recommendations,
            user_profiles=user_profiles,
            global_profiles=global_profiles,
        )

        score = result.scores[0]
        # user_score = 1.0 * 0.5 = 0.5
        # global_score = 0.6 * 0.5 = 0.3
        # blended = 0.5 * 0.7 + 0.3 * 0.3 = 0.35 + 0.09 = 0.44
        # final = 4 * 0.5 + 0.44 * 0.5 = 2.0 + 0.22 = 2.22
        assert score.blended_effectiveness == pytest.approx(0.44)
        assert score.final_rank_score == pytest.approx(2.22)

    def test_negative_effectiveness_lowers_rank(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow", priority=5),
            make_action(FeedbackActionType.repeat, label="Repeat", priority=5),
        ]
        recommendations = make_recommendations(actions)

        user_profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=-1.0,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations_personalized(
            recommendations,
            user_profiles=user_profiles,
        )

        # slow_down has negative effectiveness, should rank lower
        assert result.recommendation_set.actions[0].label == "Repeat"
        assert result.recommendation_set.actions[1].label == "Slow"
