"""
Tests for Learning Aggregation.

Sprint 5 Dev Order 4: Tests for aggregate_effectiveness().
"""
import pytest

from sg_coach.learning_aggregation import (
    aggregate_effectiveness,
    aggregate_profile_key,
    compute_aggregate_confidence,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.learning_aggregation import (
    ActionEffectivenessProfile,
    LearningSignalAggregateSet,
)
from sg_spec.schemas.user_feedback import (
    LearningSignal,
    PracticeOutcome,
    UserFeedbackResponseType,
)


def make_signal(
    code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    action: FeedbackActionType = FeedbackActionType.slow_down,
    weight: float = 1.0,
) -> LearningSignal:
    """Helper to create test signals."""
    return LearningSignal(
        source_finding_code=code,
        action_type=action,
        user_response=UserFeedbackResponseType.helped,
        outcome=PracticeOutcome.improved,
        weight=weight,
    )


class TestAggregateProfileKey:
    """Test the key extraction helper."""

    def test_extracts_diagnosis_and_action(self):
        signal = make_signal(
            code=DiagnosisCode.WRONG_NOTE,
            action=FeedbackActionType.isolate,
        )
        key = aggregate_profile_key(signal)
        assert key == (DiagnosisCode.WRONG_NOTE, FeedbackActionType.isolate)


class TestComputeAggregateConfidence:
    """Test confidence calculation."""

    def test_zero_count(self):
        assert compute_aggregate_confidence(0) == 0.0

    def test_five_signals(self):
        assert compute_aggregate_confidence(5) == 0.5

    def test_ten_signals(self):
        assert compute_aggregate_confidence(10) == 1.0

    def test_twenty_signals_caps_at_one(self):
        assert compute_aggregate_confidence(20) == 1.0

    def test_one_signal(self):
        assert compute_aggregate_confidence(1) == 0.1


class TestEmptyInput:
    """Test empty signal list handling."""

    def test_empty_list_returns_empty_set(self):
        result = aggregate_effectiveness([])
        assert isinstance(result, LearningSignalAggregateSet)
        assert result.profiles == []
        assert result.total_signals == 0


class TestSingleSignal:
    """Test single signal aggregation."""

    def test_single_signal_creates_one_profile(self):
        signal = make_signal(weight=1.0)
        result = aggregate_effectiveness([signal])

        assert len(result.profiles) == 1
        assert result.total_signals == 1

    def test_single_signal_profile_values(self):
        signal = make_signal(
            code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=FeedbackActionType.slow_down,
            weight=0.8,
        )
        result = aggregate_effectiveness([signal])
        profile = result.profiles[0]

        assert profile.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert profile.action_type == FeedbackActionType.slow_down
        assert profile.average_weight == 0.8
        assert profile.signal_count == 1
        assert profile.usable_signal_count == 1
        assert profile.weak_signal_count == 0
        assert profile.confidence == 0.1


class TestMultipleSameKey:
    """Test multiple signals with same key."""

    def test_averages_weights_correctly(self):
        signals = [
            make_signal(weight=1.0),
            make_signal(weight=0.8),
        ]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 1
        assert result.profiles[0].average_weight == pytest.approx(0.9)
        assert result.profiles[0].signal_count == 2
        assert result.profiles[0].usable_signal_count == 2

    def test_confidence_reflects_count(self):
        signals = [make_signal(weight=0.5) for _ in range(5)]
        result = aggregate_effectiveness(signals)

        assert result.profiles[0].confidence == 0.5


class TestDifferentDiagnosisCodes:
    """Test signals with different diagnosis codes."""

    def test_creates_separate_profiles(self):
        signals = [
            make_signal(code=DiagnosisCode.TIMING_GRID_DEVIATION, weight=1.0),
            make_signal(code=DiagnosisCode.WRONG_NOTE, weight=0.8),
        ]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 2
        assert result.total_signals == 2

        codes = {p.diagnosis_code for p in result.profiles}
        assert DiagnosisCode.TIMING_GRID_DEVIATION in codes
        assert DiagnosisCode.WRONG_NOTE in codes


class TestDifferentActionTypes:
    """Test signals with different action types."""

    def test_creates_separate_profiles(self):
        signals = [
            make_signal(action=FeedbackActionType.slow_down, weight=1.0),
            make_signal(action=FeedbackActionType.repeat, weight=0.8),
        ]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 2

        actions = {p.action_type for p in result.profiles}
        assert FeedbackActionType.slow_down in actions
        assert FeedbackActionType.repeat in actions


class TestWeakSignals:
    """Test weak signal handling."""

    def test_weak_signals_excluded_by_default(self):
        signals = [
            make_signal(weight=1.0),
            make_signal(weight=0.1),  # weak
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.signal_count == 2
        assert profile.usable_signal_count == 1
        assert profile.weak_signal_count == 1
        assert profile.average_weight == 1.0  # only non-weak

    def test_weak_signal_count_populated(self):
        signals = [
            make_signal(weight=0.05),  # weak
            make_signal(weight=0.15),  # weak
            make_signal(weight=0.5),   # not weak
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.weak_signal_count == 2
        assert profile.usable_signal_count == 1

    def test_usable_signal_count_populated(self):
        signals = [
            make_signal(weight=0.8),
            make_signal(weight=0.6),
            make_signal(weight=0.1),  # weak
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.usable_signal_count == 2
        assert profile.signal_count == 3


class TestAllWeakGroup:
    """Test groups where all signals are weak."""

    def test_all_weak_produces_zero_weight(self):
        signals = [
            make_signal(weight=0.1),
            make_signal(weight=0.05),
            make_signal(weight=-0.1),
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.average_weight == 0.0

    def test_all_weak_produces_zero_confidence(self):
        signals = [
            make_signal(weight=0.1),
            make_signal(weight=0.15),
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.confidence == 0.0

    def test_all_weak_still_in_profiles(self):
        signals = [make_signal(weight=0.1)]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 1
        assert result.profiles[0].signal_count == 1
        assert result.profiles[0].usable_signal_count == 0


class TestIncludeWeak:
    """Test include_weak=True behavior."""

    def test_includes_weak_in_average(self):
        signals = [
            make_signal(weight=1.0),
            make_signal(weight=0.1),  # weak
        ]
        result = aggregate_effectiveness(signals, include_weak=True)
        profile = result.profiles[0]

        assert profile.average_weight == pytest.approx(0.55)
        assert profile.usable_signal_count == 2

    def test_confidence_uses_all_signals(self):
        signals = [
            make_signal(weight=0.1) for _ in range(10)  # all weak
        ]
        result = aggregate_effectiveness(signals, include_weak=True)
        profile = result.profiles[0]

        assert profile.confidence == 1.0
        assert profile.usable_signal_count == 10


class TestNegativeWeights:
    """Test negative weight handling."""

    def test_negative_weights_average_correctly(self):
        signals = [
            make_signal(weight=-0.8),
            make_signal(weight=-0.6),
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.average_weight == pytest.approx(-0.7)

    def test_mixed_positive_negative(self):
        signals = [
            make_signal(weight=1.0),
            make_signal(weight=-0.5),
        ]
        result = aggregate_effectiveness(signals)
        profile = result.profiles[0]

        assert profile.average_weight == pytest.approx(0.25)


class TestSignalsNotMutated:
    """Test that input signals are not mutated."""

    def test_signals_unchanged(self):
        signal = make_signal(weight=0.8)
        original_weight = signal.weight
        original_code = signal.source_finding_code
        original_action = signal.action_type

        aggregate_effectiveness([signal])

        assert signal.weight == original_weight
        assert signal.source_finding_code == original_code
        assert signal.action_type == original_action


class TestTotalSignals:
    """Test total_signals count."""

    def test_counts_all_including_weak(self):
        signals = [
            make_signal(weight=1.0),
            make_signal(weight=0.1),  # weak
            make_signal(weight=0.8),
        ]
        result = aggregate_effectiveness(signals)

        assert result.total_signals == 3


class TestIntegration:
    """Integration tests for full aggregation flow."""

    def test_example_from_spec(self):
        signals = [
            LearningSignal(
                source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action_type=FeedbackActionType.slow_down,
                user_response=UserFeedbackResponseType.helped,
                outcome=PracticeOutcome.improved,
                weight=1.0,
            ),
            LearningSignal(
                source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action_type=FeedbackActionType.slow_down,
                user_response=UserFeedbackResponseType.helped,
                outcome=PracticeOutcome.improved,
                weight=0.8,
            ),
        ]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 1
        profile = result.profiles[0]
        assert profile.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert profile.action_type == FeedbackActionType.slow_down
        assert profile.average_weight == pytest.approx(0.9)
        assert profile.signal_count == 2
        assert profile.usable_signal_count == 2
        assert profile.weak_signal_count == 0
        assert profile.confidence == pytest.approx(0.2)
        assert result.total_signals == 2

    def test_complex_mixed_signals(self):
        signals = [
            make_signal(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action=FeedbackActionType.slow_down,
                weight=1.0,
            ),
            make_signal(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action=FeedbackActionType.slow_down,
                weight=0.1,  # weak
            ),
            make_signal(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action=FeedbackActionType.repeat,
                weight=0.6,
            ),
            make_signal(
                code=DiagnosisCode.WRONG_NOTE,
                action=FeedbackActionType.isolate,
                weight=-0.5,
            ),
        ]
        result = aggregate_effectiveness(signals)

        assert len(result.profiles) == 3
        assert result.total_signals == 4

        # Find specific profiles
        profiles_by_key = {
            (p.diagnosis_code, p.action_type): p for p in result.profiles
        }

        timing_slow = profiles_by_key[
            (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.slow_down)
        ]
        assert timing_slow.average_weight == 1.0  # weak excluded
        assert timing_slow.signal_count == 2
        assert timing_slow.weak_signal_count == 1

        timing_repeat = profiles_by_key[
            (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.repeat)
        ]
        assert timing_repeat.average_weight == 0.6

        wrong_note_isolate = profiles_by_key[
            (DiagnosisCode.WRONG_NOTE, FeedbackActionType.isolate)
        ]
        assert wrong_note_isolate.average_weight == -0.5
