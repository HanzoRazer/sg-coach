"""
Tests for Adaptive Ranking.

Sprint 5 Dev Order 5: Tests for rank_recommendations().
"""
import pytest

from sg_coach.adaptive_ranking import (
    CONFIDENCE_THRESHOLD,
    rank_recommendations,
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
    """Helper to create test profile sets."""
    return LearningSignalAggregateSet(
        profiles=profiles,
        total_signals=sum(p.signal_count for p in profiles),
    )


class TestEmptyInput:
    """Test empty input handling."""

    def test_empty_actions_returns_same(self):
        recommendations = make_recommendations([])
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.actions == []

    def test_empty_profiles_preserves_order(self):
        actions = [
            make_action(FeedbackActionType.slow_down, priority=5),
            make_action(FeedbackActionType.repeat, priority=8),
        ]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert len(result.actions) == 2
        # Higher priority should rank higher (8 > 5)
        assert result.actions[0].action_type == FeedbackActionType.repeat


class TestRankingFormula:
    """Test the ranking formula."""

    def test_learned_score_affects_ranking(self):
        actions = [
            make_action(FeedbackActionType.slow_down, priority=5),
            make_action(FeedbackActionType.repeat, priority=5),
        ]
        recommendations = make_recommendations(actions)

        # slow_down has high effectiveness
        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.5,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)

        # slow_down should rank higher due to learned effectiveness
        assert result.actions[0].action_type == FeedbackActionType.slow_down

    def test_rank_score_computation(self):
        actions = [make_action(FeedbackActionType.slow_down, priority=6)]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.0,
                confidence=0.5,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)
        action = result.actions[0]

        # learned_score = 1.0 * 0.5 = 0.5
        # rank_score = (6 * 0.5) + (0.5 * 0.5) = 3.0 + 0.25 = 3.25
        assert action.params["learned_score"] == pytest.approx(0.5)
        assert action.params["original_priority"] == 6
        assert action.params["rank_score"] == pytest.approx(3.25)


class TestMissingProfile:
    """Test handling of missing profiles."""

    def test_missing_profile_uses_zero_learned_score(self):
        actions = [make_action(FeedbackActionType.slow_down, priority=5)]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)
        action = result.actions[0]

        assert action.params["learned_score"] == 0.0
        assert action.params["original_priority"] == 5
        # rank_score = (5 * 0.5) + (0 * 0.5) = 2.5
        assert action.params["rank_score"] == pytest.approx(2.5)

    def test_missing_profile_no_penalty(self):
        actions = [
            make_action(FeedbackActionType.slow_down, priority=5),
            make_action(FeedbackActionType.repeat, priority=5),
        ]
        recommendations = make_recommendations(actions)

        # Only repeat has a negative profile
        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.repeat,
                average_weight=-0.5,
                confidence=0.5,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)

        # slow_down (no profile, learned=0) should beat repeat (negative)
        assert result.actions[0].action_type == FeedbackActionType.slow_down


class TestConfidenceThreshold:
    """Test confidence threshold behavior."""

    def test_low_confidence_ignored(self):
        actions = [
            make_action(FeedbackActionType.slow_down, priority=5),
            make_action(FeedbackActionType.repeat, priority=5),
        ]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=2.0,
                confidence=0.2,  # Below threshold
            ),
        ])

        result = rank_recommendations(recommendations, profiles)

        # slow_down's profile should be ignored due to low confidence
        assert result.actions[0].params["learned_score"] == 0.0

    def test_at_threshold_applied(self):
        actions = [make_action(FeedbackActionType.slow_down, priority=5)]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.0,
                confidence=CONFIDENCE_THRESHOLD,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)
        action = result.actions[0]

        assert action.params["learned_score"] == pytest.approx(0.3)

    def test_above_threshold_applied(self):
        actions = [make_action(FeedbackActionType.slow_down, priority=5)]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.0,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)
        action = result.actions[0]

        assert action.params["learned_score"] == pytest.approx(0.8)


class TestParamsMetadata:
    """Test that params metadata is populated correctly."""

    def test_rank_score_in_params(self):
        actions = [make_action(priority=5)]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert "rank_score" in result.actions[0].params

    def test_learned_score_in_params(self):
        actions = [make_action(priority=5)]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert "learned_score" in result.actions[0].params

    def test_original_priority_in_params(self):
        actions = [make_action(priority=7)]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.actions[0].params["original_priority"] == 7

    def test_existing_params_preserved(self):
        action = RecommendedAction(
            action_type=FeedbackActionType.slow_down,
            label="Test",
            priority=5,
            params={"existing_key": "existing_value"},
        )
        recommendations = make_recommendations([action])
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.actions[0].params["existing_key"] == "existing_value"
        assert "rank_score" in result.actions[0].params


class TestActionPreservation:
    """Test that actions are not added or removed."""

    def test_same_action_count(self):
        actions = [
            make_action(FeedbackActionType.slow_down),
            make_action(FeedbackActionType.repeat),
            make_action(FeedbackActionType.isolate),
        ]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert len(result.actions) == 3

    def test_all_action_types_present(self):
        actions = [
            make_action(FeedbackActionType.slow_down),
            make_action(FeedbackActionType.repeat),
        ]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        action_types = {a.action_type for a in result.actions}
        assert FeedbackActionType.slow_down in action_types
        assert FeedbackActionType.repeat in action_types


class TestRecommendationSetPreservation:
    """Test that recommendation set metadata is preserved."""

    def test_id_preserved(self):
        recommendations = ActionRecommendationSet(
            id="rec_123",
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            actions=[make_action()],
        )
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.id == "rec_123"

    def test_finding_code_preserved(self):
        recommendations = make_recommendations(
            [make_action()],
            finding_code=DiagnosisCode.WRONG_NOTE,
        )
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.finding_code == DiagnosisCode.WRONG_NOTE

    def test_finding_id_preserved(self):
        recommendations = ActionRecommendationSet(
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            finding_id="find_456",
            actions=[make_action()],
        )
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.finding_id == "find_456"

    def test_source_preserved(self):
        recommendations = ActionRecommendationSet(
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            actions=[make_action()],
            source="adaptive",
        )
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        assert result.source == "adaptive"


class TestNegativeWeights:
    """Test handling of negative effectiveness weights."""

    def test_negative_weight_lowers_rank(self):
        actions = [
            make_action(FeedbackActionType.slow_down, priority=5),
            make_action(FeedbackActionType.repeat, priority=5),
        ]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=-1.0,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)

        # slow_down has negative effectiveness, should rank lower
        assert result.actions[1].action_type == FeedbackActionType.slow_down


class TestStableSorting:
    """Test that sorting is stable for equal scores."""

    def test_equal_scores_preserve_original_order(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="First", priority=5),
            make_action(FeedbackActionType.repeat, label="Second", priority=5),
        ]
        recommendations = make_recommendations(actions)
        profiles = make_profiles([])

        result = rank_recommendations(recommendations, profiles)

        # Both have same rank_score, original order preserved
        assert result.actions[0].label == "First"
        assert result.actions[1].label == "Second"


class TestDifferentFindingCodes:
    """Test that profiles are matched by finding code."""

    def test_wrong_finding_code_not_applied(self):
        actions = [make_action(FeedbackActionType.slow_down, priority=5)]
        recommendations = make_recommendations(
            actions,
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )

        # Profile for different finding code
        profiles = make_profiles([
            make_profile(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                action_type=FeedbackActionType.slow_down,
                average_weight=2.0,
                confidence=0.8,
            ),
        ])

        result = rank_recommendations(recommendations, profiles)

        # Profile should not match
        assert result.actions[0].params["learned_score"] == 0.0


class TestIntegration:
    """Integration tests for full ranking flow."""

    def test_complex_ranking_scenario(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow", priority=3),
            make_action(FeedbackActionType.repeat, label="Repeat", priority=5),
            make_action(FeedbackActionType.isolate, label="Isolate", priority=7),
        ]
        recommendations = make_recommendations(actions)

        profiles = make_profiles([
            make_profile(
                action_type=FeedbackActionType.slow_down,
                average_weight=1.5,
                confidence=0.8,
            ),
            make_profile(
                action_type=FeedbackActionType.repeat,
                average_weight=-0.5,
                confidence=0.6,
            ),
            # isolate has no profile
        ])

        result = rank_recommendations(recommendations, profiles)

        # Calculate expected scores:
        # slow_down: (3 * 0.5) + (1.5 * 0.8 * 0.5) = 1.5 + 0.6 = 2.1
        # repeat: (5 * 0.5) + (-0.5 * 0.6 * 0.5) = 2.5 - 0.15 = 2.35
        # isolate: (7 * 0.5) + (0 * 0.5) = 3.5

        # Expected order: isolate (3.5), repeat (2.35), slow_down (2.1)
        assert result.actions[0].label == "Isolate"
        assert result.actions[1].label == "Repeat"
        assert result.actions[2].label == "Slow"

        # Verify scores
        assert result.actions[0].params["rank_score"] == pytest.approx(3.5)
        assert result.actions[1].params["rank_score"] == pytest.approx(2.35)
        assert result.actions[2].params["rank_score"] == pytest.approx(2.1)
