"""
Tests for Drill Resolver.

Sprint 8: Tests for drill resolution.
"""
import pytest

from sg_coach.drill_catalog import DEFAULT_DRILL_CATALOG
from sg_coach.drill_resolver import (
    request_from_recommended_action,
    resolve_drill,
    resolve_drills_for_recommendations,
)
from sg_spec.schemas.action_mapping import (
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import TargetSpan
from sg_spec.schemas.drill_resolution import (
    DrillDifficulty,
    DrillReference,
    DrillResolutionRequest,
)
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType


def make_request(
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type: FeedbackActionType = FeedbackActionType.assign_drill,
    user_id: str | None = None,
) -> DrillResolutionRequest:
    """Helper to create test requests."""
    return DrillResolutionRequest(
        diagnosis_code=diagnosis_code,
        action_type=action_type,
        user_id=user_id,
    )


def make_action(
    action_type: FeedbackActionType = FeedbackActionType.assign_drill,
    label: str = "Test action",
    params: dict | None = None,
) -> RecommendedAction:
    """Helper to create test actions."""
    return RecommendedAction(
        action_type=action_type,
        label=label,
        params=params or {},
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


class TestResolveDrillKnownMapping:
    """Test resolving known assign_drill mappings."""

    def test_resolves_timing_grid_deviation(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.assign_drill,
        )

        result = resolve_drill(request)

        assert result.resolved is True
        assert result.drill is not None
        assert result.drill.drill_id == "timing_grid_quarter_note_reset_v1"

    def test_resolves_dim_orbit_violation(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
        )

        result = resolve_drill(request)

        assert result.resolved is True
        assert result.drill.drill_id == "diminished_orbit_isolation_v1"

    def test_resolves_wrong_note(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.WRONG_NOTE,
        )

        result = resolve_drill(request)

        assert result.resolved is True
        assert result.drill.drill_id == "single_note_reference_recall_v1"

    def test_resolves_pitch_deviation(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
        )

        result = resolve_drill(request)

        assert result.resolved is True
        assert result.drill.drill_id == "pitch_centering_sustain_v1"


class TestResolveDrillUnsupportedAction:
    """Test resolving non-assign_drill actions."""

    def test_returns_unsupported_for_slow_down(self):
        request = make_request(
            action_type=FeedbackActionType.slow_down,
        )

        result = resolve_drill(request)

        assert result.resolved is False
        assert result.reason == "unsupported_action_type"
        assert result.drill is None

    def test_returns_unsupported_for_repeat(self):
        request = make_request(
            action_type=FeedbackActionType.repeat,
        )

        result = resolve_drill(request)

        assert result.resolved is False
        assert result.reason == "unsupported_action_type"


class TestResolveDrillMissingMapping:
    """Test resolving when no drill exists."""

    def test_returns_no_matching_drill(self):
        custom_catalog: dict = {}

        request = make_request(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )

        result = resolve_drill(request, catalog=custom_catalog)

        assert result.resolved is False
        assert result.reason == "no_matching_drill"
        assert result.drill is None


class TestResolveDrillPreservesRequest:
    """Test that results preserve the original request."""

    def test_resolved_preserves_request(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            user_id="user_123",
        )

        result = resolve_drill(request)

        assert result.request.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result.request.user_id == "user_123"

    def test_unresolved_preserves_request(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
        )

        result = resolve_drill(request)

        assert result.request.action_type == FeedbackActionType.slow_down


class TestResolveDrillReturnsCopy:
    """Test that resolver returns copies, not originals."""

    def test_does_not_mutate_catalog(self):
        request = make_request(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )

        result = resolve_drill(request)

        # Get original from catalog
        key = (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.assign_drill)
        original = DEFAULT_DRILL_CATALOG[key]

        # Verify they're different objects
        assert result.drill is not original

    def test_returned_drill_is_independent(self):
        request = make_request()

        result1 = resolve_drill(request)
        result2 = resolve_drill(request)

        # Different result objects
        assert result1.drill is not result2.drill


class TestCustomCatalog:
    """Test custom catalog injection."""

    def test_uses_custom_catalog(self):
        custom_drill = DrillReference(
            drill_id="custom_drill_v1",
            title="Custom Drill",
        )
        custom_catalog = {
            (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.assign_drill): custom_drill,
        }

        request = make_request()
        result = resolve_drill(request, catalog=custom_catalog)

        assert result.resolved is True
        assert result.drill.drill_id == "custom_drill_v1"


class TestRequestFromRecommendedAction:
    """Test request creation from actions."""

    def test_creates_valid_request(self):
        action = make_action(action_type=FeedbackActionType.assign_drill)

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
        )

        assert request.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert request.action_type == FeedbackActionType.assign_drill

    def test_preserves_user_id(self):
        action = make_action()

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            user_id="user_abc",
        )

        assert request.user_id == "user_abc"

    def test_preserves_session_id(self):
        action = make_action()

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            session_id="sess_123",
        )

        assert request.session_id == "sess_123"

    def test_preserves_instrument_id(self):
        action = make_action()

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            instrument_id="guitar_456",
        )

        assert request.instrument_id == "guitar_456"

    def test_copies_target_span(self):
        action = make_action()
        span = TargetSpan(start_time_sec=5.0, end_time_sec=10.0)

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            target_span=span,
        )

        assert request.target_span is not None
        assert request.target_span.start_time_sec == 5.0

    def test_includes_action_params_in_context(self):
        action = make_action(params={"tempo": 80, "bars": 4})

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
        )

        assert "action_params" in request.context
        assert request.context["action_params"]["tempo"] == 80

    def test_empty_params_not_in_context(self):
        action = make_action(params={})

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
        )

        assert "action_params" not in request.context

    def test_preserves_additional_context(self):
        action = make_action()

        request = request_from_recommended_action(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action=action,
            context={"extra_key": "extra_value"},
        )

        assert request.context["extra_key"] == "extra_value"


class TestResolveDrillsForRecommendations:
    """Test batch resolution."""

    def test_only_resolves_assign_drill_actions(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow"),
            make_action(FeedbackActionType.assign_drill, label="Drill"),
            make_action(FeedbackActionType.repeat, label="Repeat"),
        ]
        recommendations = make_recommendations(actions)

        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
        )

        assert len(results) == 1
        assert results[0].resolved is True

    def test_returns_expected_count(self):
        actions = [
            make_action(FeedbackActionType.assign_drill),
            make_action(FeedbackActionType.assign_drill),
        ]
        recommendations = make_recommendations(actions)

        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
        )

        assert len(results) == 2

    def test_empty_recommendations(self):
        recommendations = make_recommendations([])

        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
        )

        assert results == []

    def test_no_assign_drill_actions(self):
        actions = [
            make_action(FeedbackActionType.slow_down),
            make_action(FeedbackActionType.repeat),
        ]
        recommendations = make_recommendations(actions)

        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
        )

        assert results == []

    def test_passes_context_to_resolver(self):
        actions = [make_action(FeedbackActionType.assign_drill)]
        recommendations = make_recommendations(actions)

        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
            user_id="user_test",
            session_id="sess_test",
        )

        assert results[0].request.user_id == "user_test"
        assert results[0].request.session_id == "sess_test"


class TestAllLayerOneMappingsExist:
    """Test that all Layer 1 diagnosis codes have mappings."""

    def test_dim_orbit_violation_has_mapping(self):
        request = make_request(DiagnosisCode.DIM_ORBIT_VIOLATION)
        result = resolve_drill(request)
        assert result.resolved is True

    def test_timing_grid_deviation_has_mapping(self):
        request = make_request(DiagnosisCode.TIMING_GRID_DEVIATION)
        result = resolve_drill(request)
        assert result.resolved is True

    def test_wrong_note_has_mapping(self):
        request = make_request(DiagnosisCode.WRONG_NOTE)
        result = resolve_drill(request)
        assert result.resolved is True

    def test_pitch_deviation_has_mapping(self):
        request = make_request(DiagnosisCode.PITCH_DEVIATION)
        result = resolve_drill(request)
        assert result.resolved is True


class TestIntegration:
    """Integration tests for full resolution flow."""

    def test_recommendation_to_drill_flow(self):
        # Create a recommendation with assign_drill
        action = RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Practice timing drill",
            params={"source": "coach_evaluation"},
        )
        recommendations = ActionRecommendationSet(
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            actions=[action],
        )

        # Resolve drills
        results = resolve_drills_for_recommendations(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            recommendations=recommendations,
            user_id="player_123",
        )

        assert len(results) == 1
        result = results[0]
        assert result.resolved is True
        assert result.drill.drill_id == "timing_grid_quarter_note_reset_v1"
        assert result.drill.title == "Quarter Note Timing Reset"
        assert result.request.user_id == "player_123"
        assert "action_params" in result.request.context
