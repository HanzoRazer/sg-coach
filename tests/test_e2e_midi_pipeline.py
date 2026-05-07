"""
End-to-End MIDI Pipeline Test.

Sprint 11: Verifies the complete coaching pipeline from MIDI input to
persisted practice assignments.

Success condition: Given a MIDI-derived SessionRecord, the system produces
a persisted PracticeAssignmentSet using the existing symbolic coaching spine.
"""
from pathlib import Path
from uuid import UUID

import pytest

from sg_coach import (
    build_session_from_midi,
    evaluate_session,
    attach_recommendations,
    assemble_practice_assignments,
    resolve_drill,
    request_from_recommended_action,
    PracticeHistoryStore,
    create_history_entry,
    COACH_VERSION,
    SESSION_BUILDER_VERSION,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachEvaluation
from sg_spec.schemas.drill_resolution import DrillResolutionResult
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.midi_session import (
    MidiEventType,
    MidiNoteEvent,
    MidiSessionInput,
    SessionInputMetadata,
)
from sg_spec.schemas.practice_assignment import PracticeAssignmentStatus


def resolve_drills_for_evaluation(evaluation: CoachEvaluation) -> list[DrillResolutionResult]:
    """Helper to resolve drills for all recommendations in an evaluation."""
    results = []
    if not evaluation.recommendations:
        return results

    for rec_set in evaluation.recommendations:
        diagnosis_code = rec_set.finding_code
        if not diagnosis_code:
            continue

        for action in rec_set.actions:
            if action.action_type != FeedbackActionType.assign_drill:
                continue

            request = request_from_recommended_action(
                diagnosis_code=diagnosis_code,
                action=action,
            )
            result = resolve_drill(request)
            results.append(result)

    return results


def make_timing_session_input() -> MidiSessionInput:
    """
    Create a MIDI session input with timing deviations.

    This session has notes that are consistently late, which should
    trigger TIMING_GRID_DEVIATION findings and timing-related assignments.
    """
    expected_times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    events = []

    for i, expected in enumerate(expected_times):
        late_offset = 0.045
        performed_time = expected + late_offset

        events.append(MidiNoteEvent(
            type=MidiEventType.note_on,
            note=60 + (i % 4),
            velocity=100,
            time_sec=performed_time,
        ))
        events.append(MidiNoteEvent(
            type=MidiEventType.note_off,
            note=60 + (i % 4),
            time_sec=performed_time + 0.4,
        ))

    metadata = SessionInputMetadata(
        session_id="e2e_timing_test_001",
        user_id="test_user",
        instrument_id="test_guitar",
        program_id="timing_exercise_1",
        program_type="ztprog",
        program_title="Timing Exercise 1",
        tempo_bpm=120.0,
        grid=8,
        duration_sec=4,
        expected_times=expected_times,
    )

    return MidiSessionInput(events=events, metadata=metadata)


def make_harmony_session_input() -> MidiSessionInput:
    """
    Create a MIDI session input with harmony context.

    This session has notes in C major context with some pitch class
    coverage for harmony evaluation.
    """
    events = [
        MidiNoteEvent(type=MidiEventType.note_on, note=60, velocity=100, time_sec=0.0),
        MidiNoteEvent(type=MidiEventType.note_off, note=60, time_sec=0.4),
        MidiNoteEvent(type=MidiEventType.note_on, note=64, velocity=100, time_sec=0.5),
        MidiNoteEvent(type=MidiEventType.note_off, note=64, time_sec=0.9),
        MidiNoteEvent(type=MidiEventType.note_on, note=67, velocity=100, time_sec=1.0),
        MidiNoteEvent(type=MidiEventType.note_off, note=67, time_sec=1.4),
        MidiNoteEvent(type=MidiEventType.note_on, note=72, velocity=100, time_sec=1.5),
        MidiNoteEvent(type=MidiEventType.note_off, note=72, time_sec=1.9),
    ]

    metadata = SessionInputMetadata(
        session_id="e2e_harmony_test_001",
        user_id="test_user",
        instrument_id="test_guitar",
        program_id="harmony_exercise_1",
        program_type="ztprog",
        tempo_bpm=120.0,
        grid=8,
        duration_sec=2,
        key="C",
        expected_orbit=[0, 3, 6, 9],
    )

    return MidiSessionInput(events=events, metadata=metadata)


class TestEndToEndMidiPipeline:
    """Test complete MIDI → Session → Evaluation → Assignments pipeline."""

    def test_midi_to_session_record(self):
        """Build SessionRecord from MidiSessionInput."""
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)

        assert isinstance(session.session_id, UUID)
        assert session.instrument_id == "test_guitar"
        assert session.program_ref.name == "timing_exercise_1"
        assert session.timing.bpm == 120.0
        assert session.performance.notes_played == 8
        assert session.normalized is not None
        assert session.normalized.timing is not None
        assert len(session.normalized.timing.expected_times) == 8
        assert len(session.normalized.timing.performed_times) == 8

    def test_session_to_evaluation(self):
        """Evaluate SessionRecord to produce CoachEvaluation."""
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)
        evaluation = evaluate_session(session)

        assert str(evaluation.session_id) == str(session.session_id)
        assert evaluation.coach_version == COACH_VERSION
        assert evaluation.confidence > 0

    def test_evaluation_to_recommendations(self):
        """Attach action recommendations to evaluation."""
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)
        evaluation = evaluate_session(session)
        evaluation_with_recs = attach_recommendations(evaluation)

        assert evaluation_with_recs.recommendations is not None

    def test_recommendations_to_assignments(self):
        """Assemble practice assignments from recommendations."""
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)
        evaluation = evaluate_session(session)
        evaluation_with_recs = attach_recommendations(evaluation)

        drill_results = resolve_drills_for_evaluation(evaluation_with_recs)

        assignments = assemble_practice_assignments(
            findings=evaluation_with_recs.findings,
            recommendation_sets=evaluation_with_recs.recommendations or [],
            drill_results=drill_results,
        )

        assert assignments is not None
        for assignment in assignments.assignments:
            assert assignment.id.startswith("pa_")
            assert assignment.status in [
                PracticeAssignmentStatus.ready,
                PracticeAssignmentStatus.pending,
            ]

    def test_full_pipeline_with_persistence(self, tmp_path: Path):
        """
        Complete pipeline from MIDI input to persisted history.

        This is the Sprint 11 success condition test.
        """
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)

        evaluation = evaluate_session(session)
        evaluation_with_recs = attach_recommendations(evaluation)

        drill_results = resolve_drills_for_evaluation(evaluation_with_recs)

        assignments = assemble_practice_assignments(
            findings=evaluation_with_recs.findings,
            recommendation_sets=evaluation_with_recs.recommendations or [],
            drill_results=drill_results,
        )

        store = PracticeHistoryStore(tmp_path / "practice_history.jsonl")
        entry = store.append_session(
            session=session,
            evaluation=evaluation_with_recs,
            assignments=assignments,
            user_id="test_user",
        )

        entries = store.all()
        assert len(entries) == 1

        persisted = entries[0]
        assert persisted.id == entry.id
        assert persisted.session_id == str(session.session_id)
        assert persisted.user_id == "test_user"
        assert persisted.instrument_id == "test_guitar"
        assert persisted.assignments_count == len(assignments.assignments)

        stats = store.stats()
        assert stats.total_entries == 1

    def test_multiple_sessions_persistence(self, tmp_path: Path):
        """Store multiple session evaluations."""
        store = PracticeHistoryStore(tmp_path / "practice_history.jsonl")

        for i, make_input in enumerate([
            make_timing_session_input,
            make_harmony_session_input,
        ]):
            midi_input = make_input()
            session = build_session_from_midi(midi_input)
            evaluation = evaluate_session(session)
            evaluation_with_recs = attach_recommendations(evaluation)
            drill_results = resolve_drills_for_evaluation(evaluation_with_recs)
            assignments = assemble_practice_assignments(
                findings=evaluation_with_recs.findings,
                recommendation_sets=evaluation_with_recs.recommendations or [],
                drill_results=drill_results,
            )

            store.append_session(
                session=session,
                evaluation=evaluation_with_recs,
                assignments=assignments,
                user_id="test_user",
            )

        entries = store.all()
        assert len(entries) == 2

        stats = store.stats()
        assert stats.total_entries == 2

    def test_pipeline_with_harmony_input(self):
        """Test pipeline with harmony context."""
        midi_input = make_harmony_session_input()
        session = build_session_from_midi(midi_input)

        assert session.key == "C"
        assert session.normalized.harmony is not None
        assert session.normalized.harmony.key == "C"
        assert session.normalized.harmony.expected_orbit == [0, 3, 6, 9]
        assert session.normalized.harmony.performed_notes == [0, 4, 7, 0]

        evaluation = evaluate_session(session)
        assert evaluation is not None

    def test_query_by_session_id(self, tmp_path: Path):
        """Retrieve specific session from history."""
        midi_input = make_timing_session_input()
        session = build_session_from_midi(midi_input)
        evaluation = evaluate_session(session)
        evaluation_with_recs = attach_recommendations(evaluation)
        drill_results = resolve_drills_for_evaluation(evaluation_with_recs)
        assignments = assemble_practice_assignments(
            findings=evaluation_with_recs.findings,
            recommendation_sets=evaluation_with_recs.recommendations or [],
            drill_results=drill_results,
        )

        store = PracticeHistoryStore(tmp_path / "practice_history.jsonl")
        store.append_session(
            session=session,
            evaluation=evaluation_with_recs,
            assignments=assignments,
        )

        retrieved = store.get_by_session_id(str(session.session_id))
        assert retrieved is not None
        assert retrieved.session_id == str(session.session_id)

        not_found = store.get_by_session_id("nonexistent_session")
        assert not_found is None


class TestCLIIntegration:
    """Test CLI evaluate command integration."""

    def test_cli_help(self):
        """CLI shows help without error."""
        from sg_coach.cli import main
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_cli_version(self):
        """CLI shows version."""
        from sg_coach.cli import main
        result = main(["--version"])
        assert result == 0

    def test_cli_evaluate_missing_file(self):
        """CLI handles missing file gracefully."""
        from sg_coach.cli import main
        result = main(["evaluate", "nonexistent.json"])
        assert result == 1

    def test_cli_evaluate_midi_file(self, tmp_path: Path):
        """CLI evaluates MIDI input file."""
        import json
        from sg_coach.cli import main

        midi_input = make_timing_session_input()
        input_path = tmp_path / "midi_input.json"
        with open(input_path, "w") as f:
            json.dump(midi_input.model_dump(mode="json"), f)

        result = main(["evaluate", "--midi", str(input_path)])
        assert result == 0

    def test_cli_evaluate_with_persistence(self, tmp_path: Path):
        """CLI evaluates and persists to history."""
        import json
        from sg_coach.cli import main

        midi_input = make_timing_session_input()
        input_path = tmp_path / "midi_input.json"
        with open(input_path, "w") as f:
            json.dump(midi_input.model_dump(mode="json"), f)

        history_path = tmp_path / "history.jsonl"

        result = main([
            "evaluate",
            "--midi",
            str(input_path),
            "--persist", str(history_path),
            "--user-id", "cli_test_user",
        ])
        assert result == 0

        store = PracticeHistoryStore(history_path)
        entries = store.all()
        assert len(entries) == 1
        assert entries[0].user_id == "cli_test_user"
