"""
Tests for Learning Store.

Sprint 6: Tests for LearningSignalStore and aggregation helpers.
"""
import json
import pytest
from pathlib import Path

from sg_coach.learning_store import (
    LearningSignalStore,
    aggregate_global_effectiveness,
    aggregate_user_effectiveness,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.learning_store import LearningSignalQuery
from sg_spec.schemas.user_feedback import (
    LearningSignal,
    PracticeOutcome,
    UserFeedbackResponseType,
)


def make_signal(
    user_id: str | None = None,
    session_id: str | None = None,
    instrument_id: str | None = None,
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type: FeedbackActionType = FeedbackActionType.slow_down,
    weight: float = 1.0,
) -> LearningSignal:
    """Helper to create test signals."""
    return LearningSignal(
        source_finding_code=diagnosis_code,
        action_type=action_type,
        user_response=UserFeedbackResponseType.helped,
        outcome=PracticeOutcome.improved,
        weight=weight,
        user_id=user_id,
        session_id=session_id,
        instrument_id=instrument_id,
    )


class TestStoreCreation:
    """Test store initialization and file creation."""

    def test_creates_file_on_append(self, tmp_path: Path):
        store_path = tmp_path / "signals.jsonl"
        store = LearningSignalStore(store_path)

        assert not store_path.exists()
        store.append(make_signal())
        assert store_path.exists()

    def test_creates_parent_dirs(self, tmp_path: Path):
        store_path = tmp_path / "deep" / "nested" / "signals.jsonl"
        store = LearningSignalStore(store_path)

        store.append(make_signal())
        assert store_path.exists()

    def test_path_property(self, tmp_path: Path):
        store_path = tmp_path / "signals.jsonl"
        store = LearningSignalStore(store_path)

        assert store.path == store_path


class TestAppend:
    """Test append operations."""

    def test_append_writes_one_signal(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        signal = make_signal()

        store.append(signal)

        lines = store.path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_append_returns_signal(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        signal = make_signal()

        result = store.append(signal)

        assert result is signal

    def test_append_many_writes_multiple(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        signals = [make_signal() for _ in range(3)]

        store.append_many(signals)

        lines = store.path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_append_many_returns_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        signals = [make_signal() for _ in range(3)]

        result = store.append_many(signals)

        assert result == signals

    def test_append_many_empty_list(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        result = store.append_many([])

        assert result == []
        assert not store.path.exists()

    def test_append_does_not_overwrite(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        store.append(make_signal(user_id="first"))
        store.append(make_signal(user_id="second"))

        signals = store.all()
        assert len(signals) == 2
        assert signals[0].user_id == "first"
        assert signals[1].user_id == "second"


class TestAll:
    """Test reading all signals."""

    def test_all_returns_stored_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_1"))
        store.append(make_signal(user_id="user_2"))

        signals = store.all()

        assert len(signals) == 2
        assert signals[0].user_id == "user_1"
        assert signals[1].user_id == "user_2"

    def test_all_empty_store(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        signals = store.all()

        assert signals == []

    def test_blank_lines_ignored(self, tmp_path: Path):
        store_path = tmp_path / "signals.jsonl"
        store = LearningSignalStore(store_path)

        # Write with blank lines
        store.append(make_signal())
        with open(store_path, "a") as f:
            f.write("\n\n")
        store.append(make_signal())

        signals = store.all()
        assert len(signals) == 2


class TestInvalidJSON:
    """Test error handling for invalid JSON."""

    def test_invalid_json_raises_error(self, tmp_path: Path):
        store_path = tmp_path / "signals.jsonl"
        store = LearningSignalStore(store_path)

        # Write invalid JSON
        store_path.write_text("not valid json\n")

        with pytest.raises(ValueError) as exc_info:
            store.all()

        assert "Invalid JSON at line 1" in str(exc_info.value)

    def test_invalid_json_includes_path(self, tmp_path: Path):
        store_path = tmp_path / "signals.jsonl"
        store = LearningSignalStore(store_path)
        store_path.write_text("bad json\n")

        with pytest.raises(ValueError) as exc_info:
            store.all()

        assert str(store_path) in str(exc_info.value)


class TestQueryEmpty:
    """Test query with no filters."""

    def test_query_none_returns_all(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append_many([make_signal() for _ in range(3)])

        signals = store.query(None)

        assert len(signals) == 3

    def test_query_empty_returns_all(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append_many([make_signal() for _ in range(3)])

        signals = store.query(LearningSignalQuery())

        assert len(signals) == 3


class TestQueryByUserId:
    """Test query filtering by user_id."""

    def test_filters_by_user_id(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a"))
        store.append(make_signal(user_id="user_b"))
        store.append(make_signal(user_id="user_a"))

        query = LearningSignalQuery(user_id="user_a", include_global=False)
        signals = store.query(query)

        assert len(signals) == 2
        assert all(s.user_id == "user_a" for s in signals)

    def test_include_global_true_includes_null_user(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a"))
        store.append(make_signal(user_id=None))  # global
        store.append(make_signal(user_id="user_b"))

        query = LearningSignalQuery(user_id="user_a", include_global=True)
        signals = store.query(query)

        assert len(signals) == 2
        user_ids = {s.user_id for s in signals}
        assert "user_a" in user_ids
        assert None in user_ids

    def test_include_global_false_excludes_null_user(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a"))
        store.append(make_signal(user_id=None))
        store.append(make_signal(user_id="user_a"))

        query = LearningSignalQuery(user_id="user_a", include_global=False)
        signals = store.query(query)

        assert len(signals) == 2
        assert all(s.user_id == "user_a" for s in signals)


class TestQueryBySessionId:
    """Test query filtering by session_id."""

    def test_filters_by_session_id(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(session_id="sess_1"))
        store.append(make_signal(session_id="sess_2"))
        store.append(make_signal(session_id="sess_1"))

        query = LearningSignalQuery(session_id="sess_1")
        signals = store.query(query)

        assert len(signals) == 2
        assert all(s.session_id == "sess_1" for s in signals)


class TestQueryByInstrumentId:
    """Test query filtering by instrument_id."""

    def test_filters_by_instrument_id(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(instrument_id="guitar_1"))
        store.append(make_signal(instrument_id="guitar_2"))

        query = LearningSignalQuery(instrument_id="guitar_1")
        signals = store.query(query)

        assert len(signals) == 1
        assert signals[0].instrument_id == "guitar_1"


class TestQueryByDiagnosisCode:
    """Test query filtering by diagnosis_code."""

    def test_filters_by_diagnosis_code(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION))
        store.append(make_signal(diagnosis_code=DiagnosisCode.WRONG_NOTE))
        store.append(make_signal(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION))

        query = LearningSignalQuery(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION
        )
        signals = store.query(query)

        assert len(signals) == 2
        assert all(
            s.source_finding_code == DiagnosisCode.TIMING_GRID_DEVIATION
            for s in signals
        )


class TestQueryByActionType:
    """Test query filtering by action_type."""

    def test_filters_by_action_type(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(action_type=FeedbackActionType.slow_down))
        store.append(make_signal(action_type=FeedbackActionType.repeat))
        store.append(make_signal(action_type=FeedbackActionType.slow_down))

        query = LearningSignalQuery(action_type=FeedbackActionType.slow_down)
        signals = store.query(query)

        assert len(signals) == 2
        assert all(s.action_type == FeedbackActionType.slow_down for s in signals)


class TestQueryLimit:
    """Test query limit."""

    def test_limit_applies_after_filtering(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        for i in range(10):
            store.append(make_signal(user_id="user_a"))

        query = LearningSignalQuery(user_id="user_a", include_global=False, limit=3)
        signals = store.query(query)

        assert len(signals) == 3

    def test_limit_with_fewer_results(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append_many([make_signal() for _ in range(2)])

        query = LearningSignalQuery(limit=10)
        signals = store.query(query)

        assert len(signals) == 2


class TestStats:
    """Test store statistics."""

    def test_stats_empty_store(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        stats = store.stats()

        assert stats.total_signals == 0
        assert stats.user_signal_count == 0
        assert stats.global_signal_count == 0

    def test_stats_counts_correctly(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a"))
        store.append(make_signal(user_id="user_b"))
        store.append(make_signal(user_id=None))  # global
        store.append(make_signal(user_id=None))  # global

        stats = store.stats()

        assert stats.total_signals == 4
        assert stats.user_signal_count == 2
        assert stats.global_signal_count == 2


class TestAggregateUserEffectiveness:
    """Test user-specific aggregation."""

    def test_uses_only_user_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a", weight=1.0))
        store.append(make_signal(user_id="user_b", weight=0.5))
        store.append(make_signal(user_id=None, weight=0.8))  # global

        result = aggregate_user_effectiveness(store, "user_a")

        assert result.total_signals == 1
        assert len(result.profiles) == 1
        assert result.profiles[0].average_weight == 1.0

    def test_excludes_global_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a", weight=1.0))
        store.append(make_signal(user_id=None, weight=-1.0))

        result = aggregate_user_effectiveness(store, "user_a")

        # Should only include user_a's signal
        assert result.total_signals == 1
        assert result.profiles[0].average_weight == 1.0

    def test_empty_for_unknown_user(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a"))

        result = aggregate_user_effectiveness(store, "unknown_user")

        assert result.total_signals == 0
        assert result.profiles == []


class TestAggregateGlobalEffectiveness:
    """Test global aggregation."""

    def test_uses_only_global_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id=None, weight=0.8))
        store.append(make_signal(user_id=None, weight=0.6))
        store.append(make_signal(user_id="user_a", weight=1.0))

        result = aggregate_global_effectiveness(store)

        assert result.total_signals == 2
        assert len(result.profiles) == 1
        assert result.profiles[0].average_weight == pytest.approx(0.7)

    def test_excludes_user_signals(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")
        store.append(make_signal(user_id="user_a", weight=1.0))
        store.append(make_signal(user_id="user_b", weight=0.5))

        result = aggregate_global_effectiveness(store)

        assert result.total_signals == 0
        assert result.profiles == []

    def test_empty_store(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        result = aggregate_global_effectiveness(store)

        assert result.total_signals == 0
        assert result.profiles == []


class TestIntegration:
    """Integration tests for full store flow."""

    def test_full_flow(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        # Add signals for different users and global
        store.append(make_signal(
            user_id="user_a",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
            weight=1.2,
        ))
        store.append(make_signal(
            user_id="user_a",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
            weight=0.8,
        ))
        store.append(make_signal(
            user_id=None,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            action_type=FeedbackActionType.slow_down,
            weight=0.5,
        ))

        # Check stats
        stats = store.stats()
        assert stats.total_signals == 3
        assert stats.user_signal_count == 2
        assert stats.global_signal_count == 1

        # User aggregation (excludes global)
        user_agg = aggregate_user_effectiveness(store, "user_a")
        assert user_agg.total_signals == 2
        assert user_agg.profiles[0].average_weight == pytest.approx(1.0)

        # Global aggregation
        global_agg = aggregate_global_effectiveness(store)
        assert global_agg.total_signals == 1
        assert global_agg.profiles[0].average_weight == pytest.approx(0.5)

    def test_multiple_diagnosis_codes(self, tmp_path: Path):
        store = LearningSignalStore(tmp_path / "signals.jsonl")

        store.append(make_signal(
            user_id="user_a",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            weight=1.0,
        ))
        store.append(make_signal(
            user_id="user_a",
            diagnosis_code=DiagnosisCode.WRONG_NOTE,
            weight=0.5,
        ))

        result = aggregate_user_effectiveness(store, "user_a")

        assert result.total_signals == 2
        assert len(result.profiles) == 2

        codes = {p.diagnosis_code for p in result.profiles}
        assert DiagnosisCode.TIMING_GRID_DEVIATION in codes
        assert DiagnosisCode.WRONG_NOTE in codes
