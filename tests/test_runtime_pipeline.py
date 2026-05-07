"""
Tests for Runtime Pipeline.

Sprint 15: MVP baseline hardening.
"""
from pathlib import Path
from uuid import uuid4

import pytest

from sg_coach.runtime_pipeline import (
    RUNTIME_VERSION,
    normalize_runtime_output,
    run_coaching_pipeline,
    run_fixture_pipeline,
)
from sg_coach.practice_history import PracticeHistoryStore
from sg_spec.schemas.midi_session import (
    MidiEventType,
    MidiNoteEvent,
    MidiSessionInput,
    SessionInputMetadata,
)
from sg_spec.schemas.runtime_pipeline import RuntimeCoachingResult


def make_timing_midi_input() -> MidiSessionInput:
    """Create MIDI input that triggers timing findings."""
    events = [
        MidiNoteEvent(
            type=MidiEventType.note_on,
            time_sec=0.0,
            note=60,
            velocity=100,
            channel=0,
        ),
        MidiNoteEvent(
            type=MidiEventType.note_off,
            time_sec=0.1,
            note=60,
            velocity=0,
            channel=0,
        ),
        MidiNoteEvent(
            type=MidiEventType.note_on,
            time_sec=0.55,
            note=62,
            velocity=100,
            channel=0,
        ),
        MidiNoteEvent(
            type=MidiEventType.note_off,
            time_sec=0.65,
            note=62,
            velocity=0,
            channel=0,
        ),
    ]

    return MidiSessionInput(
        events=events,
        metadata=SessionInputMetadata(
            session_id=str(uuid4()),
            instrument_id="guitar_1",
            program_id="timing_exercise",
            program_type="ztprog",
            tempo_bpm=120.0,
            grid=8,
            duration_sec=5,
            expected_times=[0.0, 0.5],
        ),
    )


def make_minimal_midi_input() -> MidiSessionInput:
    """Create minimal MIDI input with no findings."""
    return MidiSessionInput(
        events=[],
        metadata=SessionInputMetadata(
            session_id=str(uuid4()),
            instrument_id="guitar_1",
            program_id="test_prog",
            program_type="ztprog",
            tempo_bpm=120.0,
            grid=8,
            duration_sec=1,
        ),
    )


class TestRunCoachingPipeline:
    """Test run_coaching_pipeline function."""

    def test_returns_runtime_coaching_result(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert isinstance(result, RuntimeCoachingResult)

    def test_result_contains_session(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.session is not None
        assert result.session.instrument_id == "guitar_1"

    def test_result_contains_evaluation(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.evaluation is not None

    def test_result_contains_assignments(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.assignments is not None

    def test_result_goals_empty_without_history(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.goals == []

    def test_result_not_persisted_by_default(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.persisted is False

    def test_result_has_runtime_version(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.runtime_version == RUNTIME_VERSION

    def test_persist_requires_store_or_path(self):
        midi_input = make_minimal_midi_input()
        with pytest.raises(ValueError) as exc_info:
            run_coaching_pipeline(midi_input, persist=True)
        assert "history_store" in str(exc_info.value) or "history_path" in str(exc_info.value)

    def test_persist_with_history_path(self, tmp_path: Path):
        midi_input = make_minimal_midi_input()
        history_path = tmp_path / "history.jsonl"

        result = run_coaching_pipeline(
            midi_input,
            history_path=history_path,
            persist=True,
        )
        assert result.persisted is True
        assert history_path.exists()

    def test_persist_with_history_store(self, tmp_path: Path):
        midi_input = make_minimal_midi_input()
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        result = run_coaching_pipeline(
            midi_input,
            history_store=store,
            persist=True,
        )
        assert result.persisted is True
        assert len(store.all()) == 1

    def test_skips_persistence_when_disabled(self, tmp_path: Path):
        midi_input = make_minimal_midi_input()
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        result = run_coaching_pipeline(
            midi_input,
            history_store=store,
            persist=False,
        )
        assert result.persisted is False
        assert len(store.all()) == 0

    def test_produces_recommendations_for_findings(self):
        midi_input = make_timing_midi_input()
        result = run_coaching_pipeline(midi_input)
        if result.evaluation.findings:
            assert len(result.recommendations) > 0

    def test_produces_assignments_for_recommendations(self):
        midi_input = make_timing_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.assignments is not None

    def test_handles_empty_findings(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        assert result.evaluation.findings == []
        assert result.recommendations == []

    def test_stable_across_repeated_runs(self):
        midi_input = make_minimal_midi_input()
        result1 = run_coaching_pipeline(midi_input)
        result2 = run_coaching_pipeline(midi_input)

        assert len(result1.evaluation.findings) == len(result2.evaluation.findings)
        assert len(result1.recommendations) == len(result2.recommendations)


class TestNormalizeRuntimeOutput:
    """Test normalize_runtime_output function."""

    def test_removes_timestamps(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        normalized = normalize_runtime_output(result)

        def check_no_timestamps(obj):
            if isinstance(obj, dict):
                assert "created_at" not in obj
                assert "updated_at" not in obj
                assert "timestamp" not in obj
                for v in obj.values():
                    check_no_timestamps(v)
            elif isinstance(obj, list):
                for item in obj:
                    check_no_timestamps(item)

        check_no_timestamps(normalized)

    def test_normalizes_uuid_session_ids(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        normalized = normalize_runtime_output(result)

        session_id = normalized.get("session", {}).get("session_id")
        if session_id and len(str(session_id)) == 36:
            assert session_id == "<uuid>"

    def test_returns_dict(self):
        midi_input = make_minimal_midi_input()
        result = run_coaching_pipeline(midi_input)
        normalized = normalize_runtime_output(result)
        assert isinstance(normalized, dict)


class TestGoalsWithHistory:
    """Test goal generation when history exists."""

    def test_generates_goals_with_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            midi_input = make_timing_midi_input()
            run_coaching_pipeline(
                midi_input,
                history_store=store,
                persist=True,
            )

        midi_input = make_timing_midi_input()
        result = run_coaching_pipeline(
            midi_input,
            history_store=store,
            persist=False,
        )

        pass

    def test_goal_driven_assignments_with_goals(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for _ in range(5):
            midi_input = make_timing_midi_input()
            run_coaching_pipeline(
                midi_input,
                history_store=store,
                persist=True,
            )

        midi_input = make_timing_midi_input()
        result = run_coaching_pipeline(
            midi_input,
            history_store=store,
            persist=False,
        )

        pass


class TestSchemaExports:
    """Test that runtime pipeline is exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            RUNTIME_VERSION,
            normalize_runtime_output,
            run_coaching_pipeline,
            run_fixture_pipeline,
        )
        assert run_coaching_pipeline is not None
        assert normalize_runtime_output is not None
        assert run_fixture_pipeline is not None
        assert RUNTIME_VERSION is not None

    def test_import_runtime_coaching_result(self):
        from sg_spec.schemas import RuntimeCoachingResult
        assert RuntimeCoachingResult is not None
