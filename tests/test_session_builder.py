"""
Tests for Session Builder.

Sprint 11: Tests for MIDI input to SessionRecord conversion.
"""
from uuid import UUID

import pytest

from sg_coach.session_builder import (
    ENGINE_VERSION,
    build_session_from_midi,
    _extract_note_ons,
    _compute_performed_times,
    _compute_performed_pitch_events,
    _compute_performed_notes,
    _compute_timing_errors,
)
from sg_spec.schemas.midi_session import (
    MidiEventType,
    MidiNoteEvent,
    MidiSessionInput,
    SessionInputMetadata,
)
from sg_spec.schemas.coach_schemas import ProgramType


def make_note_on(note: int, time_sec: float, velocity: int = 100) -> MidiNoteEvent:
    """Helper to create note-on event."""
    return MidiNoteEvent(
        type=MidiEventType.note_on,
        note=note,
        velocity=velocity,
        time_sec=time_sec,
    )


def make_note_off(note: int, time_sec: float) -> MidiNoteEvent:
    """Helper to create note-off event."""
    return MidiNoteEvent(
        type=MidiEventType.note_off,
        note=note,
        time_sec=time_sec,
    )


def make_metadata(
    session_id: str = "sess_test_001",
    instrument_id: str = "guitar_1",
    program_id: str = "ztprog_test",
    tempo_bpm: float = 120.0,
    duration_sec: int = 60,
    expected_times: list | None = None,
    expected_pitch_events: list | None = None,
    key: str | None = None,
    expected_orbit: list | None = None,
) -> SessionInputMetadata:
    """Helper to create test metadata."""
    return SessionInputMetadata(
        session_id=session_id,
        instrument_id=instrument_id,
        program_id=program_id,
        tempo_bpm=tempo_bpm,
        duration_sec=duration_sec,
        expected_times=expected_times or [],
        expected_pitch_events=expected_pitch_events or [],
        key=key,
        expected_orbit=expected_orbit,
    )


def make_midi_input(
    events: list | None = None,
    metadata: SessionInputMetadata | None = None,
) -> MidiSessionInput:
    """Helper to create test MIDI input."""
    return MidiSessionInput(
        events=events or [],
        metadata=metadata or make_metadata(),
    )


class TestExtractNoteOns:
    """Test _extract_note_ons helper."""

    def test_empty_events(self):
        result = _extract_note_ons([])
        assert result == []

    def test_only_note_ons(self):
        events = [
            make_note_on(60, 0.0),
            make_note_on(64, 0.5),
        ]
        result = _extract_note_ons(events)
        assert len(result) == 2
        assert all(e.type == MidiEventType.note_on for e in result)

    def test_filters_note_offs(self):
        events = [
            make_note_on(60, 0.0),
            make_note_off(60, 0.4),
            make_note_on(64, 0.5),
            make_note_off(64, 0.9),
        ]
        result = _extract_note_ons(events)
        assert len(result) == 2
        assert result[0].note == 60
        assert result[1].note == 64


class TestComputePerformedTimes:
    """Test _compute_performed_times helper."""

    def test_empty(self):
        result = _compute_performed_times([])
        assert result == []

    def test_extracts_times(self):
        note_ons = [
            make_note_on(60, 0.0),
            make_note_on(64, 0.5),
            make_note_on(67, 1.0),
        ]
        result = _compute_performed_times(note_ons)
        assert result == [0.0, 0.5, 1.0]


class TestComputePerformedPitchEvents:
    """Test _compute_performed_pitch_events helper."""

    def test_empty(self):
        result = _compute_performed_pitch_events([])
        assert result == []

    def test_converts_to_dicts(self):
        note_ons = [
            make_note_on(60, 0.0, velocity=100),
            make_note_on(64, 0.5, velocity=80),
        ]
        result = _compute_performed_pitch_events(note_ons)
        assert len(result) == 2
        assert result[0] == {"note": "C4", "midi": 60, "time_sec": 0.0, "velocity": 100}
        assert result[1] == {"note": "E4", "midi": 64, "time_sec": 0.5, "velocity": 80}


class TestComputePerformedNotes:
    """Test _compute_performed_notes helper."""

    def test_empty(self):
        result = _compute_performed_notes([])
        assert result == []

    def test_computes_pitch_classes(self):
        note_ons = [
            make_note_on(60, 0.0),  # C4 -> 0
            make_note_on(64, 0.5),  # E4 -> 4
            make_note_on(72, 1.0),  # C5 -> 0
        ]
        result = _compute_performed_notes(note_ons)
        assert result == [0, 4, 0]


class TestComputeTimingErrors:
    """Test _compute_timing_errors helper."""

    def test_empty_expected(self):
        result = _compute_timing_errors([], [0.0, 0.5])
        assert result.mean == 0.0
        assert result.std == 0.0
        assert result.max == 0.0

    def test_empty_performed(self):
        result = _compute_timing_errors([0.0, 0.5], [])
        assert result.mean == 0.0
        assert result.std == 0.0
        assert result.max == 0.0

    def test_perfect_timing(self):
        expected = [0.0, 0.5, 1.0]
        performed = [0.0, 0.5, 1.0]
        result = _compute_timing_errors(expected, performed)
        assert result.mean == 0.0
        assert result.std == 0.0
        assert result.max == 0.0

    def test_constant_offset(self):
        expected = [0.0, 0.5, 1.0]
        performed = [0.01, 0.51, 1.01]
        result = _compute_timing_errors(expected, performed)
        assert result.mean == 10.0
        assert result.std == 0.0
        assert result.max == 10.0

    def test_varying_errors(self):
        expected = [0.0, 0.5, 1.0]
        performed = [0.01, 0.52, 1.0]
        result = _compute_timing_errors(expected, performed)
        assert result.mean == pytest.approx(10.0, rel=0.1)
        assert result.std > 0
        assert result.max == 20.0


class TestBuildSessionFromMidi:
    """Test build_session_from_midi function."""

    def test_minimal_input(self):
        midi_input = make_midi_input()
        session = build_session_from_midi(midi_input)

        assert session.instrument_id == "guitar_1"
        assert session.engine_version == ENGINE_VERSION
        assert session.program_ref.name == "ztprog_test"
        assert session.timing.bpm == 120.0
        assert session.duration_s == 60

    def test_session_id_conversion(self):
        meta = make_metadata(session_id="test_session_123")
        midi_input = make_midi_input(metadata=meta)
        session = build_session_from_midi(midi_input)

        assert isinstance(session.session_id, UUID)

    def test_uuid_session_id(self):
        uuid_str = "12345678-1234-5678-1234-567812345678"
        meta = make_metadata(session_id=uuid_str)
        midi_input = make_midi_input(metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.session_id == UUID(uuid_str)

    def test_program_type_mapping(self):
        for type_str, expected in [
            ("ztprog", ProgramType.ztprog),
            ("ztex", ProgramType.ztex),
            ("ztplay", ProgramType.ztplay),
            ("unknown", ProgramType.ztprog),
        ]:
            meta = make_metadata()
            meta = SessionInputMetadata(
                session_id="sess_001",
                instrument_id="guitar_1",
                program_id="prog_001",
                program_type=type_str,
                tempo_bpm=120.0,
                duration_sec=60,
            )
            midi_input = make_midi_input(metadata=meta)
            session = build_session_from_midi(midi_input)
            assert session.program_ref.type == expected

    def test_with_note_events(self):
        events = [
            make_note_on(60, 0.0, velocity=100),
            make_note_off(60, 0.4),
            make_note_on(64, 0.5, velocity=90),
            make_note_off(64, 0.9),
        ]
        midi_input = make_midi_input(events=events)
        session = build_session_from_midi(midi_input)

        assert session.performance.notes_played == 2
        assert session.normalized is not None
        assert session.normalized.harmony is not None
        assert session.normalized.harmony.performed_notes == [0, 4]

    def test_with_expected_times(self):
        events = [
            make_note_on(60, 0.0),
            make_note_on(64, 0.52),
        ]
        meta = make_metadata(expected_times=[0.0, 0.5])
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.normalized.timing is not None
        assert session.normalized.timing.expected_times == [0.0, 0.5]
        assert session.normalized.timing.performed_times == [0.0, 0.52]
        assert session.performance.notes_expected == 2
        assert session.performance.notes_played == 2

    def test_notes_dropped_calculation(self):
        events = [make_note_on(60, 0.0)]
        meta = make_metadata(expected_times=[0.0, 0.5, 1.0])
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.performance.notes_expected == 3
        assert session.performance.notes_played == 1
        assert session.performance.notes_dropped == 2

    def test_with_expected_pitch_events(self):
        events = [
            make_note_on(60, 0.0),
            make_note_on(64, 0.5),
        ]
        expected_pitch = [
            {"note": 60, "time_sec": 0.0},
            {"note": 64, "time_sec": 0.5},
        ]
        meta = make_metadata(expected_pitch_events=expected_pitch)
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.normalized.pitch is not None
        assert len(session.normalized.pitch.expected_pitch_events) == 2
        assert len(session.normalized.pitch.performed_pitch_events) == 2

    def test_with_harmony_context(self):
        events = [make_note_on(60, 0.0)]
        meta = make_metadata(key="C", expected_orbit=[0, 3, 6, 9])
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.key == "C"
        assert session.normalized.harmony is not None
        assert session.normalized.harmony.key == "C"
        assert session.normalized.harmony.expected_orbit == [0, 3, 6, 9]

    def test_timing_error_stats(self):
        events = [
            make_note_on(60, 0.01),
            make_note_on(64, 0.52),
        ]
        meta = make_metadata(expected_times=[0.0, 0.5])
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.performance.timing_error_ms.mean > 0
        assert session.performance.timing_error_ms.max == 20.0

    def test_custom_thresholds(self):
        events = [make_note_on(60, 0.0)]
        meta = make_metadata(expected_times=[0.0])
        expected_pitch = [{"note": 60, "time_sec": 0.0}]
        meta = SessionInputMetadata(
            session_id="sess_001",
            instrument_id="guitar_1",
            program_id="prog_001",
            tempo_bpm=120.0,
            duration_sec=60,
            expected_times=[0.0],
            expected_pitch_events=expected_pitch,
        )
        midi_input = make_midi_input(events=events, metadata=meta)
        session = build_session_from_midi(
            midi_input,
            timing_threshold_ms=50.0,
            pitch_cents_threshold=30.0,
        )

        assert session.normalized.timing.threshold_ms == 50.0
        assert session.normalized.pitch.cents_threshold == 30.0

    def test_grid_value(self):
        meta = SessionInputMetadata(
            session_id="sess_001",
            instrument_id="guitar_1",
            program_id="prog_001",
            tempo_bpm=120.0,
            grid=16,
            duration_sec=60,
        )
        midi_input = make_midi_input(metadata=meta)
        session = build_session_from_midi(midi_input)

        assert session.timing.grid == 16


class TestSchemaExports:
    """Test that session builder is exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import build_session_from_midi, SESSION_BUILDER_VERSION
        assert build_session_from_midi is not None
        assert SESSION_BUILDER_VERSION is not None
