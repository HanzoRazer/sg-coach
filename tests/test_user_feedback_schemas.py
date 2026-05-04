"""
Tests for User Feedback Loop Schemas.

Sprint 5: Validates Layer 2 feedback contracts.
"""
import pytest
from datetime import datetime, timezone

from sg_spec.schemas.user_feedback import (
    UserFeedbackResponseType,
    PracticeOutcome,
    UserFeedbackEvent,
    LearningSignal,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType


class TestUserFeedbackResponseType:
    """Test UserFeedbackResponseType enum."""

    def test_all_values_exist(self):
        assert UserFeedbackResponseType.accepted
        assert UserFeedbackResponseType.rejected
        assert UserFeedbackResponseType.helped
        assert UserFeedbackResponseType.did_not_help
        assert UserFeedbackResponseType.too_easy
        assert UserFeedbackResponseType.too_hard
        assert UserFeedbackResponseType.misunderstood
        assert UserFeedbackResponseType.user_marked_issue

    def test_values_are_strings(self):
        assert UserFeedbackResponseType.accepted.value == "accepted"
        assert UserFeedbackResponseType.did_not_help.value == "did_not_help"


class TestPracticeOutcome:
    """Test PracticeOutcome enum."""

    def test_all_values_exist(self):
        assert PracticeOutcome.repeated
        assert PracticeOutcome.improved
        assert PracticeOutcome.worsened
        assert PracticeOutcome.abandoned
        assert PracticeOutcome.completed

    def test_values_are_strings(self):
        assert PracticeOutcome.improved.value == "improved"
        assert PracticeOutcome.abandoned.value == "abandoned"


class TestUserFeedbackEvent:
    """Test UserFeedbackEvent model."""

    def test_minimal_valid_event(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        assert event.response_type == UserFeedbackResponseType.helped
        assert event.id is None
        assert event.session_id is None
        assert event.finding_id is None
        assert event.recommendation_id is None
        assert event.confidence is None
        assert event.comment is None
        assert event.corrected_result is None
        assert event.timestamp is not None

    def test_full_event(self):
        event = UserFeedbackEvent(
            id="uf_test123",
            session_id="sess_abc",
            finding_id="find_xyz",
            recommendation_id="rec_456",
            response_type=UserFeedbackResponseType.rejected,
            confidence=0.8,
            comment="The note was actually correct",
            corrected_result={"corrected_note": "C#4"},
            timestamp=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert event.id == "uf_test123"
        assert event.session_id == "sess_abc"
        assert event.finding_id == "find_xyz"
        assert event.recommendation_id == "rec_456"
        assert event.confidence == 0.8
        assert event.corrected_result == {"corrected_note": "C#4"}

    def test_confidence_bounds(self):
        # Valid bounds
        event_low = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            confidence=0.0,
        )
        assert event_low.confidence == 0.0

        event_high = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            confidence=1.0,
        )
        assert event_high.confidence == 1.0

    def test_confidence_rejects_out_of_bounds(self):
        with pytest.raises(ValueError):
            UserFeedbackEvent(
                response_type=UserFeedbackResponseType.helped,
                confidence=1.5,
            )

        with pytest.raises(ValueError):
            UserFeedbackEvent(
                response_type=UserFeedbackResponseType.helped,
                confidence=-0.1,
            )

    def test_comment_max_length(self):
        # Valid length
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            comment="x" * 500,
        )
        assert len(event.comment) == 500

        # Too long
        with pytest.raises(ValueError):
            UserFeedbackEvent(
                response_type=UserFeedbackResponseType.helped,
                comment="x" * 501,
            )

    def test_corrected_result_flexible_structure(self):
        # Various structures should be accepted
        event1 = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.rejected,
            corrected_result={"corrected_note": "C#4", "original_note": "C4"},
        )
        assert event1.corrected_result["corrected_note"] == "C#4"

        event2 = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.rejected,
            corrected_result={"cause": "string_buzz", "fret": 5, "string": 3},
        )
        assert event2.corrected_result["fret"] == 5

    def test_timestamp_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        event = UserFeedbackEvent(response_type=UserFeedbackResponseType.helped)
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_serializes_to_json(self):
        event = UserFeedbackEvent(
            id="uf_test",
            response_type=UserFeedbackResponseType.helped,
            confidence=0.9,
        )
        json_str = event.model_dump_json()
        assert "helped" in json_str
        assert "uf_test" in json_str

    def test_deserializes_from_dict(self):
        data = {
            "response_type": "rejected",
            "confidence": 0.5,
            "comment": "Not accurate",
        }
        event = UserFeedbackEvent.model_validate(data)
        assert event.response_type == UserFeedbackResponseType.rejected
        assert event.confidence == 0.5


class TestLearningSignal:
    """Test LearningSignal model."""

    def test_valid_signal(self):
        signal = LearningSignal(
            source_finding_code=DiagnosisCode.WRONG_NOTE,
            action_type=FeedbackActionType.isolate,
            user_response=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
        )
        assert signal.source_finding_code == DiagnosisCode.WRONG_NOTE
        assert signal.action_type == FeedbackActionType.isolate
        assert signal.user_response == UserFeedbackResponseType.helped
        assert signal.outcome == PracticeOutcome.improved
        assert signal.weight == 1.0  # Default
        assert signal.id is None

    def test_with_id_and_weight(self):
        signal = LearningSignal(
            id="ls_abc123",
            source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
            user_response=UserFeedbackResponseType.did_not_help,
            outcome=PracticeOutcome.abandoned,
            weight=2.5,
        )
        assert signal.id == "ls_abc123"
        assert signal.weight == 2.5

    def test_weight_bounds(self):
        # Valid bounds
        signal_low = LearningSignal(
            source_finding_code=DiagnosisCode.WRONG_NOTE,
            action_type=FeedbackActionType.repeat,
            user_response=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
            weight=0.0,
        )
        assert signal_low.weight == 0.0

        signal_high = LearningSignal(
            source_finding_code=DiagnosisCode.WRONG_NOTE,
            action_type=FeedbackActionType.repeat,
            user_response=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
            weight=10.0,
        )
        assert signal_high.weight == 10.0

    def test_weight_rejects_out_of_bounds(self):
        with pytest.raises(ValueError):
            LearningSignal(
                source_finding_code=DiagnosisCode.WRONG_NOTE,
                action_type=FeedbackActionType.repeat,
                user_response=UserFeedbackResponseType.helped,
                outcome=PracticeOutcome.improved,
                weight=10.1,
            )

    def test_requires_all_fields(self):
        with pytest.raises(ValueError):
            LearningSignal(
                source_finding_code=DiagnosisCode.WRONG_NOTE,
                # Missing action_type, user_response, outcome
            )

    def test_serializes_to_json(self):
        signal = LearningSignal(
            id="ls_test",
            source_finding_code=DiagnosisCode.PITCH_DEVIATION,
            action_type=FeedbackActionType.review_reference,
            user_response=UserFeedbackResponseType.too_hard,
            outcome=PracticeOutcome.worsened,
            weight=0.5,
        )
        json_str = signal.model_dump_json()
        assert "pitch_deviation" in json_str
        assert "too_hard" in json_str
        assert "worsened" in json_str


class TestCoachFindingId:
    """Test that CoachFinding now has id field."""

    def test_finding_has_optional_id(self):
        from sg_spec.schemas.coach_schemas import CoachFinding, Severity

        # Without ID (backward compatible)
        finding = CoachFinding(
            type="harmony",
            severity=Severity.secondary,
            interpretation="Test finding",
        )
        assert finding.id is None

        # With ID
        finding_with_id = CoachFinding(
            id="find_abc123",
            type="harmony",
            severity=Severity.secondary,
            interpretation="Test finding",
        )
        assert finding_with_id.id == "find_abc123"


class TestActionRecommendationSetId:
    """Test that ActionRecommendationSet now has id field."""

    def test_recommendation_set_has_optional_id(self):
        from sg_spec.schemas.action_mapping import ActionRecommendationSet

        # Without ID (backward compatible)
        rec_set = ActionRecommendationSet(
            finding_code=DiagnosisCode.WRONG_NOTE,
        )
        assert rec_set.id is None
        assert rec_set.finding_id is None

        # With ID
        rec_set_with_id = ActionRecommendationSet(
            id="rec_xyz789",
            finding_code=DiagnosisCode.WRONG_NOTE,
            finding_id="find_abc123",
        )
        assert rec_set_with_id.id == "rec_xyz789"
        assert rec_set_with_id.finding_id == "find_abc123"


class TestIntegration:
    """Integration tests for feedback loop flow."""

    def test_feedback_links_to_finding_and_recommendation(self):
        from sg_spec.schemas.coach_schemas import CoachFinding, Severity
        from sg_spec.schemas.action_mapping import ActionRecommendationSet

        # Create a finding with ID
        finding = CoachFinding(
            id="find_001",
            type="harmony",
            severity=Severity.primary,
            interpretation="Wrong note played",
            code=DiagnosisCode.WRONG_NOTE,
        )

        # Create recommendation set with ID
        rec_set = ActionRecommendationSet(
            id="rec_001",
            finding_code=DiagnosisCode.WRONG_NOTE,
            finding_id=finding.id,
        )

        # Create feedback linking to both
        feedback = UserFeedbackEvent(
            id="uf_001",
            finding_id=finding.id,
            recommendation_id=rec_set.id,
            response_type=UserFeedbackResponseType.helped,
            confidence=0.9,
        )

        assert feedback.finding_id == finding.id
        assert feedback.recommendation_id == rec_set.id

    def test_learning_signal_captures_full_context(self):
        signal = LearningSignal(
            id="ls_001",
            source_finding_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
            action_type=FeedbackActionType.assign_drill,
            user_response=UserFeedbackResponseType.too_hard,
            outcome=PracticeOutcome.abandoned,
            weight=2.0,
        )

        # Signal captures the full learning context
        assert signal.source_finding_code == DiagnosisCode.DIM_ORBIT_VIOLATION
        assert signal.action_type == FeedbackActionType.assign_drill
        assert signal.user_response == UserFeedbackResponseType.too_hard
        assert signal.outcome == PracticeOutcome.abandoned
        assert signal.weight == 2.0
