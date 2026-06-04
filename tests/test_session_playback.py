"""
Tests for Session Playback Builder.

Sprint 18: Session playback and inspection.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sg_spec.schemas.coach_finding import DiagnosisCode
from sg_spec.schemas.coach_schemas import (
    ClaveKind,
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    Severity,
    TargetSpan,
)
from sg_spec.schemas.midi_session import MidiEventType, MidiNoteEvent
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.session_playback import (
    PlaybackEventType,
    PlaybackTimelineEvent,
)

from sg_coach import COACH_VERSION
from sg_coach.session_playback import (
    PLAYBACK_VERSION,
    DEFAULT_FINDING_WINDOW_MS,
    build_session_playback,
    _extract_finding_timestamp_ms,
    _generate_finding_id,
    _sort_timeline_events,
)


TEST_UUID = uuid4()


def _make_session(duration_s: int = 60) -> SessionRecord:
    """Create a minimal session record for testing."""
    return SessionRecord(
        session_id=TEST_UUID,
        instrument_id="sg-test",
        engine_version="test@1.0.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="test_program",
        ),
        timing=SessionTiming(bpm=120, grid=16),
        duration_s=duration_s,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=10,
            notes_played=10,
            notes_dropped=0,
        ),
    )


def _make_finding(
    code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    severity: Severity = Severity.primary,
    interpretation: str = "Test finding",
    message: str | None = None,
    start_time_sec: float | None = None,
) -> CoachFinding:
    """Create a minimal finding for testing."""
    target_span = None
    if start_time_sec is not None:
        target_span = TargetSpan(start_time_sec=start_time_sec)

    return CoachFinding(
        type="timing",
        code=code,
        severity=severity,
        interpretation=interpretation,
        message=message,
        target_span=target_span,
        evidence=FindingEvidence(),
    )


def _make_evaluation(
    findings: list[CoachFinding] | None = None,
    session_id: str | None = None,
) -> CoachEvaluation:
    """Create a minimal evaluation for testing."""
    return CoachEvaluation(
        session_id=session_id or str(TEST_UUID),
        coach_version=COACH_VERSION,
        findings=findings or [],
        focus_recommendation=FocusRecommendation(
            concept="Test",
            reason="Test recommendation",
        ),
        strengths=[],
        weaknesses=[],
        confidence=1.0,
    )


def _make_assignment(
    assignment_id: str = "assign_001",
    title: str = "Test Assignment",
    diagnosis_code: DiagnosisCode | None = None,
    instructions: str = "Test instructions",
) -> AssembledPracticeAssignment:
    """Create a minimal assignment for testing."""
    return AssembledPracticeAssignment(
        id=assignment_id,
        assignment_type=PracticeAssignmentType.drill,
        status=PracticeAssignmentStatus.ready,
        title=title,
        instructions=instructions,
        diagnosis_code=diagnosis_code,
    )


def _make_assignment_set(
    assignments: list[AssembledPracticeAssignment] | None = None,
) -> AssembledPracticeAssignmentSet:
    """Create an assignment set for testing."""
    return AssembledPracticeAssignmentSet(
        assignments=assignments or [],
    )


def _make_midi_events(notes: list[tuple[int, float]]) -> list[MidiNoteEvent]:
    """Create MIDI note-on events from (pitch, time_sec) tuples."""
    return [
        MidiNoteEvent(
            type=MidiEventType.note_on,
            note=pitch,
            velocity=100,
            time_sec=time_sec,
        )
        for pitch, time_sec in notes
    ]


class TestExtractFindingTimestampMs:
    """Test _extract_finding_timestamp_ms helper."""

    def test_from_start_time_sec(self):
        finding = _make_finding(start_time_sec=5.5)
        assert _extract_finding_timestamp_ms(finding) == 5500

    def test_no_target_span_returns_zero(self):
        finding = _make_finding()
        assert _extract_finding_timestamp_ms(finding) == 0

    def test_no_start_time_returns_zero(self):
        finding = CoachFinding(
            type="timing",
            code=DiagnosisCode.WRONG_NOTE,
            severity=Severity.primary,
            interpretation="Test",
            target_span=TargetSpan(),
            evidence=FindingEvidence(),
        )
        assert _extract_finding_timestamp_ms(finding) == 0


class TestGenerateFindingId:
    """Test _generate_finding_id helper."""

    def test_generates_expected_format(self):
        finding_id = _generate_finding_id(0, DiagnosisCode.TIMING_GRID_DEVIATION)
        assert finding_id == "playback_finding_0_timing_grid_deviation"

    def test_different_indices(self):
        id0 = _generate_finding_id(0, DiagnosisCode.WRONG_NOTE)
        id1 = _generate_finding_id(1, DiagnosisCode.WRONG_NOTE)
        assert id0 != id1
        assert id0 == "playback_finding_0_wrong_note"
        assert id1 == "playback_finding_1_wrong_note"

    def test_different_codes(self):
        id_timing = _generate_finding_id(0, DiagnosisCode.TIMING_GRID_DEVIATION)
        id_wrong = _generate_finding_id(0, DiagnosisCode.WRONG_NOTE)
        assert id_timing != id_wrong


class TestSortTimelineEvents:
    """Test _sort_timeline_events helper."""

    def test_sorts_by_timestamp_ascending(self):
        events = [
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.note,
                timestamp_ms=5000,
                label="Late note",
            ),
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.note,
                timestamp_ms=1000,
                label="Early note",
            ),
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.note,
                timestamp_ms=3000,
                label="Middle note",
            ),
        ]
        sorted_events = _sort_timeline_events(events)
        assert [e.timestamp_ms for e in sorted_events] == [1000, 3000, 5000]

    def test_sorts_by_event_type_when_same_timestamp(self):
        events = [
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.assignment,
                timestamp_ms=1000,
                label="Assignment",
            ),
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.note,
                timestamp_ms=1000,
                label="Note",
            ),
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.finding,
                timestamp_ms=1000,
                label="Finding",
            ),
        ]
        sorted_events = _sort_timeline_events(events)
        assert [e.event_type for e in sorted_events] == [
            PlaybackEventType.note,
            PlaybackEventType.finding,
            PlaybackEventType.assignment,
        ]

    def test_marker_comes_last(self):
        events = [
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.marker,
                timestamp_ms=1000,
                label="Marker",
            ),
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.note,
                timestamp_ms=1000,
                label="Note",
            ),
        ]
        sorted_events = _sort_timeline_events(events)
        assert sorted_events[0].event_type == PlaybackEventType.note
        assert sorted_events[1].event_type == PlaybackEventType.marker


class TestBuildSessionPlayback:
    """Test build_session_playback function."""

    def test_minimal_playback(self):
        session = _make_session()
        evaluation = _make_evaluation()

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        assert playback.session_id == str(session.session_id)
        assert playback.user_id is None
        assert playback.duration_ms == 60000
        assert playback.timeline_events == []
        assert playback.finding_overlays == []
        assert playback.assignments == []
        assert playback.version == PLAYBACK_VERSION

    def test_with_user_id(self):
        session = _make_session()
        evaluation = _make_evaluation()

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            user_id="user_123",
        )

        assert playback.user_id == "user_123"

    def test_generated_at_is_set(self):
        session = _make_session()
        evaluation = _make_evaluation()

        before = datetime.now(timezone.utc)
        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )
        after = datetime.now(timezone.utc)

        assert before <= playback.generated_at <= after

    def test_builds_note_events_from_midi(self):
        session = _make_session()
        evaluation = _make_evaluation()
        midi_events = _make_midi_events([(60, 0.5), (62, 1.0), (64, 1.5)])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            midi_events=midi_events,
        )

        note_events = [e for e in playback.timeline_events if e.event_type == PlaybackEventType.note]
        assert len(note_events) == 3
        assert note_events[0].timestamp_ms == 500
        assert note_events[0].note == "60"
        assert note_events[1].timestamp_ms == 1000
        assert note_events[2].timestamp_ms == 1500

    def test_builds_finding_events(self):
        session = _make_session()
        findings = [
            _make_finding(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                interpretation="Timing issue at beat 2",
                start_time_sec=2.0,
            ),
            _make_finding(
                code=DiagnosisCode.WRONG_NOTE,
                interpretation="Wrong note played",
                start_time_sec=5.0,
            ),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        finding_events = [e for e in playback.timeline_events if e.event_type == PlaybackEventType.finding]
        assert len(finding_events) == 2
        assert finding_events[0].timestamp_ms == 2000
        assert finding_events[0].finding_id == "playback_finding_0_timing_grid_deviation"
        assert finding_events[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert finding_events[1].timestamp_ms == 5000
        assert finding_events[1].finding_id == "playback_finding_1_wrong_note"

    def test_builds_finding_overlays(self):
        session = _make_session(duration_s=60)
        findings = [
            _make_finding(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                severity=Severity.primary,
                interpretation="Timing issue",
                start_time_sec=5.0,
            ),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        assert len(playback.finding_overlays) == 1
        overlay = playback.finding_overlays[0]
        assert overlay.finding_id == "playback_finding_0_timing_grid_deviation"
        assert overlay.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert overlay.severity == Severity.primary
        assert overlay.start_timestamp_ms == 5000
        assert overlay.end_timestamp_ms == 5000 + DEFAULT_FINDING_WINDOW_MS

    def test_overlay_clamped_to_session_duration(self):
        session = _make_session(duration_s=6)
        findings = [
            _make_finding(start_time_sec=5.5),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        overlay = playback.finding_overlays[0]
        assert overlay.start_timestamp_ms == 5500
        assert overlay.end_timestamp_ms == 6000

    def test_builds_assignment_events(self):
        session = _make_session()
        findings = [
            _make_finding(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                start_time_sec=3.0,
            ),
        ]
        evaluation = _make_evaluation(findings=findings)
        assignments = _make_assignment_set([
            _make_assignment(
                assignment_id="assign_001",
                title="Metronome Drill",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
        ])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
        )

        assign_events = [e for e in playback.timeline_events if e.event_type == PlaybackEventType.assignment]
        assert len(assign_events) == 1
        assert assign_events[0].assignment_id == "assign_001"
        assert assign_events[0].label == "Metronome Drill"

    def test_builds_assignment_references(self):
        session = _make_session()
        findings = [
            _make_finding(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                start_time_sec=3.0,
            ),
            _make_finding(
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                start_time_sec=7.0,
            ),
        ]
        evaluation = _make_evaluation(findings=findings)
        assignments = _make_assignment_set([
            _make_assignment(
                assignment_id="assign_timing",
                title="Timing Drill",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
        ])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
        )

        assert len(playback.assignments) == 1
        ref = playback.assignments[0]
        assert ref.assignment_id == "assign_timing"
        assert ref.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert len(ref.linked_finding_ids) == 2
        assert "playback_finding_0_timing_grid_deviation" in ref.linked_finding_ids
        assert "playback_finding_1_timing_grid_deviation" in ref.linked_finding_ids
        assert 3000 in ref.linked_timestamps_ms
        assert 7000 in ref.linked_timestamps_ms

    def test_timeline_events_sorted(self):
        session = _make_session()
        midi_events = _make_midi_events([(60, 0.5), (62, 2.5)])
        findings = [
            _make_finding(start_time_sec=1.0),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            midi_events=midi_events,
        )

        timestamps = [e.timestamp_ms for e in playback.timeline_events]
        assert timestamps == sorted(timestamps)

    def test_no_assignments_produces_empty_refs(self):
        session = _make_session()
        evaluation = _make_evaluation()

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=None,
        )

        assert playback.assignments == []

    def test_empty_assignments_produces_empty_refs(self):
        session = _make_session()
        evaluation = _make_evaluation()
        assignments = _make_assignment_set([])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
        )

        assert playback.assignments == []

    def test_assignment_without_matching_finding(self):
        session = _make_session()
        findings = [
            _make_finding(code=DiagnosisCode.TIMING_GRID_DEVIATION),
        ]
        evaluation = _make_evaluation(findings=findings)
        assignments = _make_assignment_set([
            _make_assignment(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
            ),
        ])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
        )

        ref = playback.assignments[0]
        assert ref.linked_finding_ids == []
        assert ref.linked_timestamps_ms == []

    def test_uses_message_over_interpretation(self):
        session = _make_session()
        findings = [
            _make_finding(
                interpretation="Interpretation text",
                message="Message text",
            ),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        event = playback.timeline_events[0]
        assert event.label == "Message text"

    def test_falls_back_to_interpretation(self):
        session = _make_session()
        findings = [
            _make_finding(
                interpretation="Interpretation text",
                message=None,
            ),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        event = playback.timeline_events[0]
        assert event.label == "Interpretation text"

    def test_long_message_truncated(self):
        session = _make_session()
        long_message = "x" * 300
        findings = [
            _make_finding(message=long_message),
        ]
        evaluation = _make_evaluation(findings=findings)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        event = playback.timeline_events[0]
        assert len(event.label) == 200

    def test_skips_findings_without_code(self):
        session = _make_session()
        finding_with_code = _make_finding(code=DiagnosisCode.TIMING_GRID_DEVIATION)
        finding_without_code = CoachFinding(
            type="timing",
            code=None,
            severity=Severity.primary,
            interpretation="Legacy finding",
            evidence=FindingEvidence(),
        )
        evaluation = _make_evaluation(findings=[finding_with_code, finding_without_code])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
        )

        assert len(playback.timeline_events) == 1
        assert len(playback.finding_overlays) == 1

    def test_serializes_to_json(self):
        session = _make_session()
        midi_events = _make_midi_events([(60, 0.5)])
        findings = [
            _make_finding(start_time_sec=1.0),
        ]
        evaluation = _make_evaluation(findings=findings)
        assignments = _make_assignment_set([
            _make_assignment(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION),
        ])

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            midi_events=midi_events,
        )

        json_data = playback.model_dump(mode="json")
        assert isinstance(json_data, dict)
        assert "session_id" in json_data
        assert "timeline_events" in json_data
        assert "finding_overlays" in json_data
        assert "assignments" in json_data


class TestModuleExports:
    """Test that session playback is exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            PLAYBACK_VERSION,
            DEFAULT_FINDING_WINDOW_MS,
            build_session_playback,
        )
        assert PLAYBACK_VERSION == "0.1"
        assert DEFAULT_FINDING_WINDOW_MS == 2000
        assert callable(build_session_playback)
