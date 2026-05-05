"""
Tests for Feedback Capture.

Sprint 5 Dev Order 2: Tests for capture_feedback() and validate_feedback_linkage().
"""
import pytest
from datetime import datetime, timezone

from sg_coach.feedback_capture import (
    capture_feedback,
    validate_feedback_linkage,
    FeedbackLinkageWarning,
)
from sg_spec.schemas.user_feedback import (
    FeedbackCaptureRequest,
    UserFeedbackEvent,
    UserFeedbackResponseType,
    PracticeOutcome,
)


class TestCaptureFeedback:
    """Test capture_feedback function."""

    def test_creates_user_feedback_event(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)

        assert isinstance(event, UserFeedbackEvent)
        assert event.response_type == UserFeedbackResponseType.helped

    def test_auto_generates_id(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.accepted,
        )
        event = capture_feedback(request)

        assert event.id is not None
        assert event.id.startswith("uf_")
        assert len(event.id) > 3  # More than just the prefix

    def test_auto_generates_unique_ids(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.accepted,
        )
        event1 = capture_feedback(request)
        event2 = capture_feedback(request)

        assert event1.id != event2.id

    def test_event_id_override(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request, event_id="uf_custom_123")

        assert event.id == "uf_custom_123"

    def test_timestamp_auto_populates(self):
        before = datetime.now(timezone.utc)
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_timestamp_override(self):
        fixed_time = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request, timestamp=fixed_time)

        assert event.timestamp == fixed_time

    def test_response_type_preserved(self):
        for response_type in UserFeedbackResponseType:
            request = FeedbackCaptureRequest(response_type=response_type)
            event = capture_feedback(request)
            assert event.response_type == response_type

    def test_session_id_preserved(self):
        request = FeedbackCaptureRequest(
            session_id="sess_abc123",
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)

        assert event.session_id == "sess_abc123"

    def test_finding_id_preserved(self):
        request = FeedbackCaptureRequest(
            finding_id="find_xyz789",
            response_type=UserFeedbackResponseType.rejected,
        )
        event = capture_feedback(request)

        assert event.finding_id == "find_xyz789"

    def test_recommendation_id_preserved(self):
        request = FeedbackCaptureRequest(
            recommendation_id="rec_456",
            response_type=UserFeedbackResponseType.did_not_help,
        )
        event = capture_feedback(request)

        assert event.recommendation_id == "rec_456"

    def test_confidence_preserved(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
            confidence=0.85,
        )
        event = capture_feedback(request)

        assert event.confidence == 0.85

    def test_comment_preserved(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.rejected,
            comment="The system misidentified the note",
        )
        event = capture_feedback(request)

        assert event.comment == "The system misidentified the note"

    def test_corrected_result_preserved(self):
        correction = {"corrected_note": "C#4", "original_note": "C4"}
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.rejected,
            corrected_result=correction,
        )
        event = capture_feedback(request)

        assert event.corrected_result == correction

    def test_outcome_preserved(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
        )
        event = capture_feedback(request)

        assert event.outcome == PracticeOutcome.improved

    def test_source_preserved(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
            source="ui",
        )
        event = capture_feedback(request)

        assert event.source == "ui"

    def test_interaction_context_preserved(self):
        context = {"screen": "practice_view", "exercise_step": 3}
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
            interaction_context=context,
        )
        event = capture_feedback(request)

        assert event.interaction_context == context

    def test_empty_interaction_context_default(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)

        assert event.interaction_context == {}

    def test_full_request_preserved(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            finding_id="find_002",
            recommendation_id="rec_003",
            response_type=UserFeedbackResponseType.too_hard,
            confidence=0.6,
            comment="This was way above my level",
            corrected_result={"perceived_level": "advanced"},
            outcome=PracticeOutcome.abandoned,
            source="agentd",
            interaction_context={"tempo": 120, "bars_played": 4},
        )
        event = capture_feedback(request)

        assert event.session_id == "sess_001"
        assert event.finding_id == "find_002"
        assert event.recommendation_id == "rec_003"
        assert event.response_type == UserFeedbackResponseType.too_hard
        assert event.confidence == 0.6
        assert event.comment == "This was way above my level"
        assert event.corrected_result == {"perceived_level": "advanced"}
        assert event.outcome == PracticeOutcome.abandoned
        assert event.source == "agentd"
        assert event.interaction_context == {"tempo": 120, "bars_played": 4}


class TestValidateFeedbackLinkage:
    """Test validate_feedback_linkage function."""

    def test_no_warnings_when_fully_linked(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            finding_id="find_002",
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        assert warnings == []

    def test_warns_on_missing_session_id(self):
        request = FeedbackCaptureRequest(
            finding_id="find_002",
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        assert len(warnings) == 1
        assert warnings[0].code == "missing_session_id"
        assert warnings[0].field == "session_id"

    def test_warns_on_missing_target_linkage(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        assert len(warnings) == 1
        assert warnings[0].code == "missing_target_linkage"
        assert "finding_id" in warnings[0].field
        assert "recommendation_id" in warnings[0].field

    def test_no_target_warning_with_finding_id(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            finding_id="find_002",
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        # No missing_target_linkage warning
        codes = [w.code for w in warnings]
        assert "missing_target_linkage" not in codes

    def test_no_target_warning_with_recommendation_id(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            recommendation_id="rec_003",
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        codes = [w.code for w in warnings]
        assert "missing_target_linkage" not in codes

    def test_multiple_warnings(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        assert len(warnings) == 2
        codes = [w.code for w in warnings]
        assert "missing_session_id" in codes
        assert "missing_target_linkage" in codes

    def test_warning_has_message(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        for warning in warnings:
            assert warning.message is not None
            assert len(warning.message) > 0

    def test_warning_to_dict(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
        )
        warnings = validate_feedback_linkage(request)

        for warning in warnings:
            d = warning.to_dict()
            assert "field" in d
            assert "code" in d
            assert "message" in d


class TestMissingLinkageDoesNotPreventCapture:
    """Test that missing linkage does not prevent capture."""

    def test_capture_works_without_session_id(self):
        request = FeedbackCaptureRequest(
            finding_id="find_001",
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)

        assert event is not None
        assert event.session_id is None
        assert event.finding_id == "find_001"

    def test_capture_works_without_finding_id_or_recommendation_id(self):
        request = FeedbackCaptureRequest(
            session_id="sess_001",
            response_type=UserFeedbackResponseType.helped,
        )
        event = capture_feedback(request)

        assert event is not None
        assert event.finding_id is None
        assert event.recommendation_id is None

    def test_capture_works_with_no_linkage(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.user_marked_issue,
            comment="General feedback about the session",
        )
        event = capture_feedback(request)

        assert event is not None
        assert event.id.startswith("uf_")
        assert event.response_type == UserFeedbackResponseType.user_marked_issue


class TestFeedbackCaptureRequestValidation:
    """Test FeedbackCaptureRequest model validation."""

    def test_response_type_is_required(self):
        with pytest.raises(ValueError):
            FeedbackCaptureRequest()

    def test_confidence_bounds(self):
        # Valid
        req = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.helped,
            confidence=0.5,
        )
        assert req.confidence == 0.5

        # Out of bounds
        with pytest.raises(ValueError):
            FeedbackCaptureRequest(
                response_type=UserFeedbackResponseType.helped,
                confidence=1.5,
            )


class TestUserFeedbackEventNewFields:
    """Test new fields added to UserFeedbackEvent in Dev Order 2."""

    def test_source_field(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            source="test",
        )
        assert event.source == "test"

    def test_source_defaults_to_none(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        assert event.source is None

    def test_interaction_context_field(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            interaction_context={"view": "practice"},
        )
        assert event.interaction_context == {"view": "practice"}

    def test_interaction_context_defaults_to_empty_dict(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        assert event.interaction_context == {}

    def test_outcome_field(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
            outcome=PracticeOutcome.improved,
        )
        assert event.outcome == PracticeOutcome.improved

    def test_outcome_defaults_to_none(self):
        event = UserFeedbackEvent(
            response_type=UserFeedbackResponseType.helped,
        )
        assert event.outcome is None


class TestIntegration:
    """Integration tests for feedback capture flow."""

    def test_capture_then_validate_flow(self):
        request = FeedbackCaptureRequest(
            session_id="sess_integration",
            finding_id="find_integration",
            response_type=UserFeedbackResponseType.helped,
            confidence=0.95,
            outcome=PracticeOutcome.completed,
            source="test",
        )

        # Validate first
        warnings = validate_feedback_linkage(request)
        assert warnings == []

        # Then capture
        event = capture_feedback(request)

        assert event.id.startswith("uf_")
        assert event.session_id == "sess_integration"
        assert event.finding_id == "find_integration"
        assert event.response_type == UserFeedbackResponseType.helped
        assert event.confidence == 0.95
        assert event.outcome == PracticeOutcome.completed
        assert event.source == "test"

    def test_capture_with_warnings_still_succeeds(self):
        request = FeedbackCaptureRequest(
            response_type=UserFeedbackResponseType.misunderstood,
            comment="The system completely misunderstood",
        )

        # Has warnings
        warnings = validate_feedback_linkage(request)
        assert len(warnings) == 2

        # Capture still works
        event = capture_feedback(request)
        assert event is not None
        assert event.comment == "The system completely misunderstood"
