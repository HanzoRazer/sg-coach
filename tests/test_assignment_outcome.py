"""
Tests for Assignment Outcome utilities.

Sprint 10: Tests for outcome capture and feedback bridge.
"""
from datetime import datetime, timezone

import pytest

from sg_coach.assignment_outcome import (
    assignment_outcome_to_feedback_request,
    capture_assignment_outcome,
    generate_outcome_id,
    response_type_from_assignment_outcome,
)
from sg_spec.schemas.assignment_outcome import (
    AssignmentOutcomeCaptureRequest,
    AssignmentOutcomeEvent,
)
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.user_feedback import (
    PracticeOutcome,
    UserFeedbackResponseType,
)


def make_request(
    assignment_id: str = "pa_test123456",
    outcome: PracticeOutcome = PracticeOutcome.completed,
    session_id: str | None = None,
    user_id: str | None = None,
    instrument_id: str | None = None,
    confidence: float | None = None,
    comment: str | None = None,
    evidence: dict | None = None,
    source: str | None = None,
    interaction_context: dict | None = None,
) -> AssignmentOutcomeCaptureRequest:
    """Helper to create test capture requests."""
    return AssignmentOutcomeCaptureRequest(
        assignment_id=assignment_id,
        outcome=outcome,
        session_id=session_id,
        user_id=user_id,
        instrument_id=instrument_id,
        confidence=confidence,
        comment=comment,
        evidence=evidence or {},
        source=source,
        interaction_context=interaction_context or {},
    )


def make_assignment(
    assignment_id: str = "pa_test123456",
    assignment_type: PracticeAssignmentType = PracticeAssignmentType.drill,
    finding_id: str | None = "finding_001",
    recommendation_id: str | None = "rec_set_001",
    params: dict | None = None,
) -> AssembledPracticeAssignment:
    """Helper to create test assignments."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        assignment_type=assignment_type,
        status=PracticeAssignmentStatus.ready,
        title="Test Assignment",
        instructions="Test instructions",
        finding_id=finding_id,
        recommendation_id=recommendation_id,
        params=params or {},
    )


def make_outcome_event(
    assignment_id: str = "pa_test123456",
    outcome: PracticeOutcome = PracticeOutcome.completed,
    event_id: str | None = "ao_event123456",
    session_id: str | None = None,
    confidence: float | None = None,
    comment: str | None = None,
    evidence: dict | None = None,
    source: str | None = None,
    interaction_context: dict | None = None,
) -> AssignmentOutcomeEvent:
    """Helper to create test outcome events."""
    return AssignmentOutcomeEvent(
        id=event_id,
        assignment_id=assignment_id,
        outcome=outcome,
        session_id=session_id,
        confidence=confidence,
        comment=comment,
        evidence=evidence or {},
        source=source,
        interaction_context=interaction_context or {},
    )


class TestGenerateOutcomeId:
    """Test outcome ID generation."""

    def test_starts_with_ao_prefix(self):
        oid = generate_outcome_id()
        assert oid.startswith("ao_")

    def test_has_12_hex_chars_after_prefix(self):
        oid = generate_outcome_id()
        hex_part = oid[3:]
        assert len(hex_part) == 12
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_generates_unique_ids(self):
        ids = [generate_outcome_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestCaptureAssignmentOutcome:
    """Test capture_assignment_outcome function."""

    def test_creates_event(self):
        request = make_request()

        event = capture_assignment_outcome(request)

        assert isinstance(event, AssignmentOutcomeEvent)
        assert event.assignment_id == "pa_test123456"
        assert event.outcome == PracticeOutcome.completed

    def test_auto_generates_id_with_ao_prefix(self):
        request = make_request()

        event = capture_assignment_outcome(request)

        assert event.id is not None
        assert event.id.startswith("ao_")

    def test_uses_provided_event_id(self):
        request = make_request()

        event = capture_assignment_outcome(request, event_id="ao_custom123456")

        assert event.id == "ao_custom123456"

    def test_timestamp_override(self):
        request = make_request()
        custom_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        event = capture_assignment_outcome(request, timestamp=custom_time)

        assert event.timestamp == custom_time

    def test_preserves_assignment_id(self):
        request = make_request(assignment_id="pa_myassign123")

        event = capture_assignment_outcome(request)

        assert event.assignment_id == "pa_myassign123"

    def test_preserves_session_id(self):
        request = make_request(session_id="sess_abc123")

        event = capture_assignment_outcome(request)

        assert event.session_id == "sess_abc123"

    def test_preserves_user_id(self):
        request = make_request(user_id="user_xyz789")

        event = capture_assignment_outcome(request)

        assert event.user_id == "user_xyz789"

    def test_preserves_instrument_id(self):
        request = make_request(instrument_id="guitar_001")

        event = capture_assignment_outcome(request)

        assert event.instrument_id == "guitar_001"

    def test_preserves_outcome(self):
        for outcome in PracticeOutcome:
            request = make_request(outcome=outcome)

            event = capture_assignment_outcome(request)

            assert event.outcome == outcome

    def test_preserves_confidence(self):
        request = make_request(confidence=0.85)

        event = capture_assignment_outcome(request)

        assert event.confidence == 0.85

    def test_preserves_comment(self):
        request = make_request(comment="Great improvement!")

        event = capture_assignment_outcome(request)

        assert event.comment == "Great improvement!"

    def test_preserves_evidence(self):
        request = make_request(evidence={"timing_ms": 25, "notes_correct": 15})

        event = capture_assignment_outcome(request)

        assert event.evidence["timing_ms"] == 25
        assert event.evidence["notes_correct"] == 15

    def test_preserves_source(self):
        request = make_request(source="agentd")

        event = capture_assignment_outcome(request)

        assert event.source == "agentd"

    def test_preserves_interaction_context(self):
        request = make_request(
            interaction_context={"ui_screen": "complete", "button": "done"}
        )

        event = capture_assignment_outcome(request)

        assert event.interaction_context["ui_screen"] == "complete"
        assert event.interaction_context["button"] == "done"

    def test_does_not_require_storage(self):
        request = make_request()

        # Should complete without any storage
        event = capture_assignment_outcome(request)

        assert event is not None


class TestResponseTypeFromAssignmentOutcome:
    """Test response_type_from_assignment_outcome mapping."""

    def test_improved_maps_to_helped(self):
        result = response_type_from_assignment_outcome(PracticeOutcome.improved)
        assert result == UserFeedbackResponseType.helped

    def test_completed_maps_to_accepted(self):
        result = response_type_from_assignment_outcome(PracticeOutcome.completed)
        assert result == UserFeedbackResponseType.accepted

    def test_repeated_maps_to_accepted(self):
        result = response_type_from_assignment_outcome(PracticeOutcome.repeated)
        assert result == UserFeedbackResponseType.accepted

    def test_worsened_maps_to_did_not_help(self):
        result = response_type_from_assignment_outcome(PracticeOutcome.worsened)
        assert result == UserFeedbackResponseType.did_not_help

    def test_abandoned_maps_to_did_not_help(self):
        result = response_type_from_assignment_outcome(PracticeOutcome.abandoned)
        assert result == UserFeedbackResponseType.did_not_help

    def test_all_outcomes_have_mapping(self):
        for outcome in PracticeOutcome:
            result = response_type_from_assignment_outcome(outcome)
            assert isinstance(result, UserFeedbackResponseType)


class TestAssignmentOutcomeToFeedbackRequest:
    """Test assignment_outcome_to_feedback_request bridge."""

    def test_preserves_finding_id(self):
        assignment = make_assignment(finding_id="finding_abc")
        event = make_outcome_event()

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.finding_id == "finding_abc"

    def test_preserves_recommendation_id(self):
        assignment = make_assignment(recommendation_id="rec_xyz")
        event = make_outcome_event()

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.recommendation_id == "rec_xyz"

    def test_uses_outcome_event_session_id(self):
        assignment = make_assignment()
        event = make_outcome_event(session_id="sess_from_event")

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.session_id == "sess_from_event"

    def test_falls_back_to_assignment_params_session_id(self):
        assignment = make_assignment(params={"session_id": "sess_from_params"})
        event = make_outcome_event(session_id=None)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.session_id == "sess_from_params"

    def test_session_id_none_when_both_missing(self):
        assignment = make_assignment(params={})
        event = make_outcome_event(session_id=None)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.session_id is None

    def test_copies_confidence(self):
        assignment = make_assignment()
        event = make_outcome_event(confidence=0.9)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.confidence == 0.9

    def test_copies_comment(self):
        assignment = make_assignment()
        event = make_outcome_event(comment="Much better!")

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.comment == "Much better!"

    def test_sets_outcome(self):
        assignment = make_assignment()
        event = make_outcome_event(outcome=PracticeOutcome.improved)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.outcome == PracticeOutcome.improved

    def test_uses_evidence_as_corrected_result(self):
        assignment = make_assignment()
        event = make_outcome_event(evidence={"timing_error_ms": 15})

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.corrected_result is not None
        assert request.corrected_result["timing_error_ms"] == 15

    def test_empty_evidence_gives_none_corrected_result(self):
        assignment = make_assignment()
        event = make_outcome_event(evidence={})

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.corrected_result is None

    def test_uses_event_source(self):
        assignment = make_assignment()
        event = make_outcome_event(source="agentd")

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.source == "agentd"

    def test_defaults_source_to_assignment_outcome(self):
        assignment = make_assignment()
        event = make_outcome_event(source=None)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.source == "assignment_outcome"

    def test_includes_assignment_id_in_context(self):
        assignment = make_assignment(assignment_id="pa_myassign")
        event = make_outcome_event(assignment_id="pa_myassign")

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.interaction_context["assignment_id"] == "pa_myassign"

    def test_includes_assignment_type_in_context(self):
        assignment = make_assignment(assignment_type=PracticeAssignmentType.drill)
        event = make_outcome_event()

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.interaction_context["assignment_type"] == "drill"

    def test_includes_outcome_event_id_in_context(self):
        assignment = make_assignment()
        event = make_outcome_event(event_id="ao_myevent123")

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.interaction_context["outcome_event_id"] == "ao_myevent123"

    def test_uses_explicit_response_type_override(self):
        assignment = make_assignment()
        event = make_outcome_event(outcome=PracticeOutcome.completed)

        # Override: completed normally maps to accepted, but we override to helped
        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
            response_type=UserFeedbackResponseType.helped,
        )

        assert request.response_type == UserFeedbackResponseType.helped

    def test_auto_maps_response_type_when_not_provided(self):
        assignment = make_assignment()
        event = make_outcome_event(outcome=PracticeOutcome.improved)

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        # improved maps to helped
        assert request.response_type == UserFeedbackResponseType.helped

    def test_handles_missing_finding_id(self):
        assignment = make_assignment(finding_id=None)
        event = make_outcome_event()

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.finding_id is None

    def test_handles_missing_recommendation_id(self):
        assignment = make_assignment(recommendation_id=None)
        event = make_outcome_event()

        request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=event,
        )

        assert request.recommendation_id is None


class TestIntegration:
    """Integration tests for full outcome tracking flow."""

    def test_capture_to_feedback_flow(self):
        # 1. Create assignment
        assignment = AssembledPracticeAssignment(
            id="pa_timing123456",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready,
            title="Timing Drill",
            instructions="Practice quarter notes",
            finding_id="finding_timing_001",
            recommendation_id="rec_set_001",
        )

        # 2. Create capture request
        capture_request = AssignmentOutcomeCaptureRequest(
            assignment_id="pa_timing123456",
            session_id="sess_practice_001",
            user_id="player_123",
            outcome=PracticeOutcome.improved,
            confidence=0.9,
            comment="Much better timing accuracy",
            evidence={"timing_error_ms_before": 45, "timing_error_ms_after": 20},
            source="agentd",
        )

        # 3. Capture outcome
        outcome_event = capture_assignment_outcome(capture_request)

        assert outcome_event.id.startswith("ao_")
        assert outcome_event.outcome == PracticeOutcome.improved

        # 4. Bridge to feedback request
        feedback_request = assignment_outcome_to_feedback_request(
            assignment=assignment,
            outcome_event=outcome_event,
        )

        # Verify feedback request
        assert feedback_request.response_type == UserFeedbackResponseType.helped
        assert feedback_request.finding_id == "finding_timing_001"
        assert feedback_request.recommendation_id == "rec_set_001"
        assert feedback_request.session_id == "sess_practice_001"
        assert feedback_request.outcome == PracticeOutcome.improved
        assert feedback_request.confidence == 0.9
        assert feedback_request.corrected_result["timing_error_ms_after"] == 20
        assert feedback_request.interaction_context["assignment_id"] == "pa_timing123456"
        assert feedback_request.interaction_context["assignment_type"] == "drill"
