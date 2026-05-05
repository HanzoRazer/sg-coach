"""
Tests for Learning Weight.

Sprint 5 Dev Order 3: Tests for compute_signal_weight() and derive_learning_signal().
"""
import pytest

from sg_coach.learning_weight import (
    BASE_EFFECTIVENESS,
    OUTCOME_MODIFIER,
    WEIGHT_MIN,
    WEIGHT_MAX,
    WEAK_SIGNAL_THRESHOLD,
    compute_confidence_modifier,
    compute_signal_weight,
    derive_learning_signal,
    is_weak_signal,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.user_feedback import (
    LearningSignal,
    PracticeOutcome,
    UserFeedbackEvent,
    UserFeedbackResponseType,
)


class TestBaseEffectiveness:
    """Test base effectiveness values for all response types."""

    def test_helped_positive(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.helped] == 1.0

    def test_accepted_positive(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.accepted] == 0.6

    def test_did_not_help_negative(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.did_not_help] == -0.8

    def test_rejected_negative(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.rejected] == -1.0

    def test_too_easy_negative(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.too_easy] == -0.3

    def test_too_hard_negative(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.too_hard] == -0.5

    def test_misunderstood_strong_negative(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.misunderstood] == -0.9

    def test_user_marked_issue_positive(self):
        assert BASE_EFFECTIVENESS[UserFeedbackResponseType.user_marked_issue] == 0.7

    def test_all_response_types_covered(self):
        for response_type in UserFeedbackResponseType:
            assert response_type in BASE_EFFECTIVENESS


class TestOutcomeModifier:
    """Test outcome modifier values."""

    def test_improved_amplifies(self):
        assert OUTCOME_MODIFIER[PracticeOutcome.improved] == 1.5

    def test_completed_amplifies(self):
        assert OUTCOME_MODIFIER[PracticeOutcome.completed] == 1.2

    def test_repeated_neutral(self):
        assert OUTCOME_MODIFIER[PracticeOutcome.repeated] == 1.0

    def test_worsened_dampens(self):
        assert OUTCOME_MODIFIER[PracticeOutcome.worsened] == 0.5

    def test_abandoned_dampens(self):
        assert OUTCOME_MODIFIER[PracticeOutcome.abandoned] == 0.3

    def test_all_outcomes_covered(self):
        for outcome in PracticeOutcome:
            assert outcome in OUTCOME_MODIFIER


class TestConfidenceModifier:
    """Test confidence modifier computation."""

    def test_none_uses_default(self):
        modifier = compute_confidence_modifier(None)
        assert modifier == 0.75

    def test_zero_confidence(self):
        modifier = compute_confidence_modifier(0.0)
        assert modifier == 0.5

    def test_half_confidence(self):
        modifier = compute_confidence_modifier(0.5)
        assert modifier == 0.75

    def test_full_confidence(self):
        modifier = compute_confidence_modifier(1.0)
        assert modifier == 1.0

    def test_partial_confidence(self):
        modifier = compute_confidence_modifier(0.8)
        assert modifier == pytest.approx(0.9)


class TestComputeSignalWeight:
    """Test signal weight computation."""

    def test_helped_full_confidence_improved(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=1.0,
            outcome=PracticeOutcome.improved,
        )
        assert weight == pytest.approx(1.5)

    def test_rejected_full_confidence_worsened(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.rejected,
            confidence=1.0,
            outcome=PracticeOutcome.worsened,
        )
        assert weight == pytest.approx(-0.5)

    def test_none_confidence_uses_default(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=None,
            outcome=PracticeOutcome.repeated,
        )
        assert weight == pytest.approx(0.75)

    def test_none_outcome_uses_default(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=1.0,
            outcome=None,
        )
        assert weight == pytest.approx(1.0)

    def test_both_none_uses_defaults(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=None,
            outcome=None,
        )
        assert weight == pytest.approx(0.75)

    def test_clamps_max(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=1.0,
            outcome=PracticeOutcome.improved,
        )
        assert weight <= WEIGHT_MAX

    def test_clamps_min(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.rejected,
            confidence=1.0,
            outcome=PracticeOutcome.improved,
        )
        assert weight >= WEIGHT_MIN

    def test_negative_weight_possible(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.rejected,
            confidence=1.0,
            outcome=PracticeOutcome.repeated,
        )
        assert weight < 0

    def test_example_from_spec(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=0.8,
            outcome=PracticeOutcome.improved,
        )
        assert weight == pytest.approx(1.35)


class TestClampBehavior:
    """Test weight clamping at boundaries."""

    def test_weight_max_value(self):
        assert WEIGHT_MAX == 2.0

    def test_weight_min_value(self):
        assert WEIGHT_MIN == -2.0

    def test_extreme_positive_clamped(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            confidence=1.0,
            outcome=PracticeOutcome.improved,
        )
        assert weight == 1.5
        assert weight <= WEIGHT_MAX

    def test_extreme_negative_clamped(self):
        weight = compute_signal_weight(
            UserFeedbackResponseType.rejected,
            confidence=1.0,
            outcome=PracticeOutcome.improved,
        )
        assert weight == -1.5
        assert weight >= WEIGHT_MIN


class TestIsWeakSignal:
    """Test weak signal detection."""

    def test_threshold_value(self):
        assert WEAK_SIGNAL_THRESHOLD == 0.2

    def test_below_threshold_is_weak(self):
        assert is_weak_signal(0.1)
        assert is_weak_signal(-0.1)
        assert is_weak_signal(0.0)

    def test_at_threshold_not_weak(self):
        assert not is_weak_signal(0.2)
        assert not is_weak_signal(-0.2)

    def test_above_threshold_not_weak(self):
        assert not is_weak_signal(0.5)
        assert not is_weak_signal(-0.5)
        assert not is_weak_signal(1.0)


class TestDeriveLearningSignal:
    """Test LearningSignal derivation from UserFeedbackEvent."""

    def test_returns_learning_signal(self):
        event = UserFeedbackEvent(
            id="uf_test123",
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert isinstance(signal, LearningSignal)

    def test_auto_generates_id(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.id is not None
        assert signal.id.startswith("ls_")

    def test_signal_id_override(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
            signal_id="ls_custom_456",
        )
        assert signal.id == "ls_custom_456"

    def test_populates_source_finding_code(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.WRONG_NOTE,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.source_finding_code == DiagnosisCode.WRONG_NOTE

    def test_populates_action_type(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.repeat,
        )
        assert signal.action_type == FeedbackActionType.repeat

    def test_copies_user_response(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.rejected,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.user_response == UserFeedbackResponseType.rejected

    def test_copies_outcome(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.outcome == PracticeOutcome.improved

    def test_missing_outcome_uses_default(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            outcome=None,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.outcome == PracticeOutcome.repeated

    def test_computes_weight(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            confidence=0.8,
            outcome=PracticeOutcome.improved,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.weight == pytest.approx(1.35)

    def test_links_source_event_id(self):
        event = UserFeedbackEvent(
            id="uf_source_event",
            response_type=UserFeedbackResponseType.helped,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.source_event_id == "uf_source_event"

    def test_negative_weight_derivation(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.misunderstood,
            confidence=1.0,
            outcome=PracticeOutcome.abandoned,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal.weight < 0


class TestAllResponseTypes:
    """Test weight computation for all response types."""

    @pytest.mark.parametrize("response_type", list(UserFeedbackResponseType))
    def test_computes_weight_for_response_type(self, response_type):
        weight = compute_signal_weight(response_type)
        assert isinstance(weight, float)
        assert WEIGHT_MIN <= weight <= WEIGHT_MAX


class TestAllOutcomes:
    """Test weight computation for all outcomes."""

    @pytest.mark.parametrize("outcome", list(PracticeOutcome))
    def test_computes_weight_with_outcome(self, outcome):
        weight = compute_signal_weight(
            UserFeedbackResponseType.helped,
            outcome=outcome,
        )
        assert isinstance(weight, float)
        assert WEIGHT_MIN <= weight <= WEIGHT_MAX


class TestNoAggregation:
    """Test that derivation does not aggregate."""

    def test_single_signal_per_event(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        signal1 = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        signal2 = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert signal1.id != signal2.id


class TestIntegration:
    """Integration tests for the full derivation flow."""

    def test_full_derivation_flow(self):
        event = UserFeedbackEvent(
            id="uf_integration_test",
            session_id="sess_001",
            finding_id="find_002",
            response_type=UserFeedbackResponseType.helped,
            confidence=0.9,
            outcome=PracticeOutcome.completed,
        )

        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )

        assert signal.id.startswith("ls_")
        assert signal.source_finding_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert signal.action_type == FeedbackActionType.slow_down
        assert signal.user_response == UserFeedbackResponseType.helped
        assert signal.outcome == PracticeOutcome.completed
        assert signal.source_event_id == "uf_integration_test"
        expected_weight = 1.0 * (0.5 + 0.9 * 0.5) * 1.2
        assert signal.weight == pytest.approx(expected_weight)

    def test_weak_signal_still_returned(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.too_easy,
            confidence=0.0,
            outcome=PracticeOutcome.abandoned,
        )
        signal = derive_learning_signal(
            event,
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )
        assert is_weak_signal(signal.weight)
        assert signal is not None
