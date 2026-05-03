"""
Tests for session normalizer.

Sprint 3: Session normalization tests.
"""
import uuid

import pytest

from sg_coach.session_normalizer import (
    normalize_session,
    ensure_normalized_session,
    has_timing_input,
    has_pitch_input,
    has_harmony_input,
)
from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    TimingErrorStats,
    ProgramRef,
    ProgramType,
    NormalizedSessionData,
    HarmonyEvaluationInput,
    TimingEvaluationInput,
    PitchEvaluationInput,
)


def make_base_session(program_name: str = "test_exercise.ztprog") -> SessionRecord:
    """Create a valid base session for testing."""
    return SessionRecord(
        session_id=uuid.uuid4(),
        instrument_id="test-guitar",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name=program_name),
        timing=SessionTiming(bpm=120.0, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=8,
            notes_played=8,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=10.0, std=5.0, max=20.0),
        ),
    )


class TestNormalizeSession:
    """Test normalize_session function."""

    def test_empty_session_gets_normalized_container(self):
        session = make_base_session()
        assert session.normalized is None

        result = normalize_session(session)
        assert result.normalized is not None
        assert result.normalized.harmony is None
        assert result.normalized.timing is None
        assert result.normalized.pitch is None

    def test_legacy_timing_params_populate_normalized(self):
        session = make_base_session()
        result = normalize_session(
            session,
            expected_times=[0.0, 0.5, 1.0],
            performed_times=[0.02, 0.51, 1.03],
            timing_threshold_ms=30.0,
        )

        assert result.normalized.timing is not None
        assert result.normalized.timing.expected_times == [0.0, 0.5, 1.0]
        assert result.normalized.timing.performed_times == [0.02, 0.51, 1.03]
        assert result.normalized.timing.threshold_ms == 30.0

    def test_legacy_pitch_params_populate_normalized(self):
        session = make_base_session()
        expected = [{"note": "E4", "midi": 64}]
        performed = [{"note": "Eb4", "midi": 63}]

        result = normalize_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
            pitch_cents_threshold=15.0,
        )

        assert result.normalized.pitch is not None
        assert result.normalized.pitch.expected_pitch_events == expected
        assert result.normalized.pitch.performed_pitch_events == performed
        assert result.normalized.pitch.cents_threshold == 15.0

    def test_legacy_harmony_params_populate_normalized(self):
        session = make_base_session("dim_orbit_C.ztprog")
        session = session.model_copy(update={"key": "C"})

        result = normalize_session(
            session,
            performed_notes=[0, 3, 6, 9],
        )

        assert result.normalized.harmony is not None
        assert result.normalized.harmony.key == "C"
        assert result.normalized.harmony.performed_notes == [0, 3, 6, 9]

    def test_existing_normalized_is_preserved(self):
        session = make_base_session()
        existing_timing = TimingEvaluationInput(
            expected_times=[1.0, 2.0],
            performed_times=[1.01, 2.02],
            threshold_ms=50.0,
        )
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(timing=existing_timing)}
        )

        # Pass different legacy params — should be ignored
        result = normalize_session(
            session,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.5],
            timing_threshold_ms=25.0,
        )

        # Existing normalized wins
        assert result.normalized.timing.expected_times == [1.0, 2.0]
        assert result.normalized.timing.threshold_ms == 50.0

    def test_legacy_does_not_overwrite_existing(self):
        session = make_base_session()
        existing_pitch = PitchEvaluationInput(
            expected_pitch_events=[{"note": "C4"}],
            performed_pitch_events=[{"note": "C4"}],
            cents_threshold=10.0,
        )
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(pitch=existing_pitch)}
        )

        # Pass different legacy params
        result = normalize_session(
            session,
            expected_pitch_events=[{"note": "G4"}],
            performed_pitch_events=[{"note": "G#4"}],
            pitch_cents_threshold=30.0,
        )

        # Existing wins
        assert result.normalized.pitch.expected_pitch_events == [{"note": "C4"}]
        assert result.normalized.pitch.cents_threshold == 10.0

    def test_does_not_mutate_original(self):
        session = make_base_session()
        original_normalized = session.normalized

        result = normalize_session(
            session,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.5],
        )

        # Original unchanged
        assert session.normalized is original_normalized
        # Result is different object
        assert result is not session
        assert result.normalized is not None

    def test_key_extracted_from_program_if_not_set(self):
        session = make_base_session("dim_orbit_G.ztprog")
        assert session.key is None

        result = normalize_session(
            session,
            performed_notes=[7, 10, 1, 4],  # G diminished orbit
        )

        assert result.normalized.harmony is not None
        assert result.normalized.harmony.key == "G"

    def test_session_key_takes_precedence(self):
        session = make_base_session("dim_orbit_G.ztprog")
        session = session.model_copy(update={"key": "C"})

        result = normalize_session(
            session,
            performed_notes=[0, 3, 6, 9],
        )

        # Explicit key wins over extracted
        assert result.normalized.harmony.key == "C"


class TestEnsureNormalizedSession:
    """Test ensure_normalized_session function."""

    def test_returns_same_if_already_normalized(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData()}
        )

        result = ensure_normalized_session(session)
        assert result is session

    def test_adds_empty_normalized_if_missing(self):
        session = make_base_session()
        assert session.normalized is None

        result = ensure_normalized_session(session)
        assert result.normalized is not None
        assert result.normalized.harmony is None
        assert result.normalized.timing is None
        assert result.normalized.pitch is None


class TestHasInputHelpers:
    """Test has_*_input helper functions."""

    def test_has_timing_input_false_without_normalized(self):
        session = make_base_session()
        assert has_timing_input(session) is False

    def test_has_timing_input_false_without_timing(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData()}
        )
        assert has_timing_input(session) is False

    def test_has_timing_input_false_if_empty(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(
                timing=TimingEvaluationInput()
            )}
        )
        assert has_timing_input(session) is False

    def test_has_timing_input_true_when_populated(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(
                timing=TimingEvaluationInput(
                    expected_times=[0.0, 0.5],
                    performed_times=[0.0, 0.5],
                )
            )}
        )
        assert has_timing_input(session) is True

    def test_has_pitch_input_false_without_normalized(self):
        session = make_base_session()
        assert has_pitch_input(session) is False

    def test_has_pitch_input_true_when_populated(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(
                pitch=PitchEvaluationInput(
                    expected_pitch_events=[{"note": "E4"}],
                    performed_pitch_events=[{"note": "E4"}],
                )
            )}
        )
        assert has_pitch_input(session) is True

    def test_has_harmony_input_false_without_normalized(self):
        session = make_base_session()
        assert has_harmony_input(session) is False

    def test_has_harmony_input_true_when_populated(self):
        session = make_base_session()
        session = session.model_copy(
            update={"normalized": NormalizedSessionData(
                harmony=HarmonyEvaluationInput(
                    performed_notes=[0, 3, 6, 9],
                )
            )}
        )
        assert has_harmony_input(session) is True
