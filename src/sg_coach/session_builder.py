"""
Session Builder — Convert MIDI input to SessionRecord.

Sprint 11: Runtime integration.

Converts MidiSessionInput (pre-parsed MIDI events + metadata) into
a SessionRecord suitable for the coaching pipeline.

Ownership: sg-coach (conversion logic)
Input contract: sg-spec (MidiSessionInput)
Output contract: sg-spec (SessionRecord)
"""
from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from sg_spec.schemas.midi_session import (
    MidiEventType,
    MidiNoteEvent,
    MidiSessionInput,
    SessionInputMetadata,
)

from .schemas import (
    HarmonyEvaluationInput,
    NormalizedSessionData,
    PerformanceSummary,
    PitchEvaluationInput,
    ProgramRef,
    ProgramType,
    SessionEvents,
    SessionRecord,
    SessionTiming,
    TimingEvaluationInput,
    TimingErrorStats,
)

ENGINE_VERSION = "sg-coach@1.9.0"


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_note_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 60 -> C4)."""
    octave = (midi // 12) - 1
    note_idx = midi % 12
    return f"{_NOTE_NAMES[note_idx]}{octave}"


def _extract_note_ons(events: List[MidiNoteEvent]) -> List[MidiNoteEvent]:
    """Extract note-on events from event list."""
    return [e for e in events if e.type == MidiEventType.note_on]


def _compute_performed_times(note_ons: List[MidiNoteEvent]) -> List[float]:
    """Extract performed times from note-on events."""
    return [e.time_sec for e in note_ons]


def _compute_performed_pitch_events(note_ons: List[MidiNoteEvent]) -> List[dict]:
    """Convert note-on events to performed pitch event dicts."""
    return [
        {
            "note": _midi_to_note_name(e.note),
            "midi": e.note,
            "time_sec": e.time_sec,
            "velocity": e.velocity,
        }
        for e in note_ons
    ]


def _compute_performed_notes(note_ons: List[MidiNoteEvent]) -> List[int]:
    """Extract pitch classes (0-11) from note-on events."""
    return [e.note % 12 for e in note_ons]


def _compute_timing_errors(
    expected_times: List[float],
    performed_times: List[float],
) -> TimingErrorStats:
    """Compute timing error statistics."""
    if not expected_times or not performed_times:
        return TimingErrorStats()

    min_len = min(len(expected_times), len(performed_times))
    if min_len == 0:
        return TimingErrorStats()

    errors_ms = [
        abs(performed_times[i] - expected_times[i]) * 1000.0
        for i in range(min_len)
    ]

    mean_error = sum(errors_ms) / len(errors_ms)
    max_error = max(errors_ms)

    variance = sum((e - mean_error) ** 2 for e in errors_ms) / len(errors_ms)
    std_error = variance ** 0.5

    return TimingErrorStats(
        mean=round(mean_error, 2),
        std=round(std_error, 2),
        max=round(max_error, 2),
    )


def _program_type_from_string(type_str: str) -> ProgramType:
    """Convert program type string to enum."""
    mapping = {
        "ztprog": ProgramType.ztprog,
        "ztex": ProgramType.ztex,
        "ztplay": ProgramType.ztplay,
    }
    return mapping.get(type_str, ProgramType.ztprog)


def build_session_from_midi(
    midi_input: MidiSessionInput,
    *,
    engine_version: str = ENGINE_VERSION,
    timing_threshold_ms: float = 40.0,
    pitch_cents_threshold: float = 25.0,
) -> SessionRecord:
    """
    Build a SessionRecord from MIDI input.

    Parameters
    ----------
    midi_input:
        Pre-parsed MIDI events + session metadata.
    engine_version:
        Version string for the producing engine.
    timing_threshold_ms:
        Timing deviation threshold for evaluators.
    pitch_cents_threshold:
        Pitch deviation threshold for evaluators.

    Returns
    -------
    SessionRecord ready for evaluate_session().
    """
    events = midi_input.events
    meta = midi_input.metadata

    note_ons = _extract_note_ons(events)
    performed_times = _compute_performed_times(note_ons)
    performed_pitch_events = _compute_performed_pitch_events(note_ons)
    performed_notes = _compute_performed_notes(note_ons)

    timing_input = None
    if meta.expected_times:
        timing_input = TimingEvaluationInput(
            expected_times=list(meta.expected_times),
            performed_times=performed_times,
            threshold_ms=timing_threshold_ms,
        )

    pitch_input = None
    if meta.expected_pitch_events:
        pitch_input = PitchEvaluationInput(
            expected_pitch_events=list(meta.expected_pitch_events),
            performed_pitch_events=performed_pitch_events,
            cents_threshold=pitch_cents_threshold,
        )

    harmony_input = None
    if performed_notes:
        harmony_input = HarmonyEvaluationInput(
            key=meta.key,
            performed_notes=performed_notes,
            expected_orbit=meta.expected_orbit,
        )

    normalized = NormalizedSessionData(
        timing=timing_input,
        pitch=pitch_input,
        harmony=harmony_input,
    )

    timing_errors = _compute_timing_errors(
        meta.expected_times,
        performed_times,
    )

    notes_expected = len(meta.expected_times) if meta.expected_times else 0
    notes_played = len(note_ons)
    notes_dropped = max(0, notes_expected - notes_played)

    performance = PerformanceSummary(
        bars_played=0,
        notes_expected=notes_expected,
        notes_played=notes_played,
        notes_dropped=notes_dropped,
        timing_error_ms=timing_errors,
    )

    program_ref = ProgramRef(
        type=_program_type_from_string(meta.program_type),
        name=meta.program_id,
    )

    session_timing = SessionTiming(
        bpm=meta.tempo_bpm,
        grid=meta.grid,
    )

    try:
        session_id = UUID(meta.session_id)
    except ValueError:
        session_id = UUID(int=hash(meta.session_id) & ((1 << 128) - 1))

    return SessionRecord(
        session_id=session_id,
        instrument_id=meta.instrument_id,
        engine_version=engine_version,
        program_ref=program_ref,
        timing=session_timing,
        duration_s=meta.duration_sec,
        performance=performance,
        events=SessionEvents(),
        key=meta.key,
        normalized=normalized,
    )


__all__ = [
    "build_session_from_midi",
    "ENGINE_VERSION",
]
