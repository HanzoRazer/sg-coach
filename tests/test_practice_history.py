"""
Tests for Practice History Store.

Sprint 11: Tests for JSONL practice history persistence.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from sg_coach.practice_history import (
    PracticeHistoryEntry,
    PracticeHistoryQuery,
    PracticeHistoryStats,
    PracticeHistoryStore,
    create_history_entry,
)
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
)
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)


def make_session(
    session_id: str | None = None,
    instrument_id: str = "guitar_1",
) -> SessionRecord:
    """Helper to create test session."""
    return SessionRecord(
        session_id=uuid4() if session_id is None else session_id,
        instrument_id=instrument_id,
        engine_version="test@1.0.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test_prog"),
        timing=SessionTiming(bpm=120.0, grid=8),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=16,
            notes_played=14,
            notes_dropped=2,
        ),
    )


def make_evaluation(session_id: str | None = None) -> CoachEvaluation:
    """Helper to create test evaluation."""
    return CoachEvaluation(
        session_id=uuid4() if session_id is None else session_id,
        coach_version="test@1.0.0",
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Practice timing accuracy",
        ),
        confidence=0.8,
    )


def make_assignments() -> AssembledPracticeAssignmentSet:
    """Helper to create test assignment set."""
    return AssembledPracticeAssignmentSet(
        assignments=[
            AssembledPracticeAssignment(
                id="pa_test123456",
                assignment_type=PracticeAssignmentType.drill,
                status=PracticeAssignmentStatus.ready,
                title="Test Drill",
                instructions="Practice this drill",
            ),
        ],
    )


class TestPracticeHistoryEntry:
    """Test PracticeHistoryEntry schema."""

    def test_creates_with_defaults(self):
        entry = PracticeHistoryEntry(
            session_id="sess_001",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=0,
            assignments_count=0,
        )
        assert entry.id.startswith("ph_")
        assert entry.session_id == "sess_001"
        assert entry.version == "0.1"

    def test_custom_id(self):
        entry = PracticeHistoryEntry(
            id="ph_custom123456",
            session_id="sess_001",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=0,
            assignments_count=0,
        )
        assert entry.id == "ph_custom123456"

    def test_timestamp_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        entry = PracticeHistoryEntry(
            session_id="sess_001",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=0,
            assignments_count=0,
        )
        after = datetime.now(timezone.utc)
        assert before <= entry.timestamp <= after


class TestCreateHistoryEntry:
    """Test create_history_entry function."""

    def test_creates_entry(self):
        session = make_session()
        evaluation = make_evaluation(session.session_id)
        assignments = make_assignments()

        entry = create_history_entry(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
        )

        assert entry.session_id == str(session.session_id)
        assert entry.instrument_id == session.instrument_id
        assert entry.findings_count == 0
        assert entry.assignments_count == 1
        assert entry.id.startswith("ph_")

    def test_with_user_id(self):
        session = make_session()
        evaluation = make_evaluation(session.session_id)
        assignments = make_assignments()

        entry = create_history_entry(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id="user_123",
        )

        assert entry.user_id == "user_123"

    def test_with_custom_id(self):
        session = make_session()
        evaluation = make_evaluation(session.session_id)
        assignments = make_assignments()

        entry = create_history_entry(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            entry_id="ph_explicit123",
        )

        assert entry.id == "ph_explicit123"


class TestPracticeHistoryStore:
    """Test PracticeHistoryStore."""

    def test_append_and_read(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        entry = PracticeHistoryEntry(
            session_id="sess_001",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=2,
            assignments_count=1,
        )

        store.append(entry)
        entries = store.all()

        assert len(entries) == 1
        assert entries[0].session_id == "sess_001"
        assert entries[0].findings_count == 2

    def test_append_session(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        session = make_session()
        evaluation = make_evaluation(session.session_id)
        assignments = make_assignments()

        entry = store.append_session(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id="user_123",
        )

        entries = store.all()
        assert len(entries) == 1
        assert entries[0].user_id == "user_123"
        assert entries[0].id == entry.id

    def test_multiple_entries(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for i in range(3):
            entry = PracticeHistoryEntry(
                session_id=f"sess_{i:03d}",
                instrument_id="guitar_1",
                session={},
                evaluation={},
                assignments={},
                findings_count=i,
                assignments_count=0,
            )
            store.append(entry)

        entries = store.all()
        assert len(entries) == 3
        assert entries[0].session_id == "sess_000"
        assert entries[2].session_id == "sess_002"

    def test_empty_store(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "nonexistent.jsonl")
        entries = store.all()
        assert entries == []

    def test_creates_parent_dirs(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "nested" / "dir" / "history.jsonl")

        entry = PracticeHistoryEntry(
            session_id="sess_001",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=0,
            assignments_count=0,
        )
        store.append(entry)

        assert store.path.exists()


class TestPracticeHistoryQuery:
    """Test PracticeHistoryStore.query()."""

    def test_query_all(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for i in range(3):
            entry = PracticeHistoryEntry(
                session_id=f"sess_{i:03d}",
                instrument_id="guitar_1",
                session={},
                evaluation={},
                assignments={},
                findings_count=0,
                assignments_count=0,
            )
            store.append(entry)

        results = store.query(None)
        assert len(results) == 3

    def test_query_by_user_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for user in ["user_a", "user_b", "user_a"]:
            entry = PracticeHistoryEntry(
                session_id=f"sess_{user}",
                instrument_id="guitar_1",
                user_id=user,
                session={},
                evaluation={},
                assignments={},
                findings_count=0,
                assignments_count=0,
            )
            store.append(entry)

        query = PracticeHistoryQuery(user_id="user_a")
        results = store.query(query)
        assert len(results) == 2
        assert all(e.user_id == "user_a" for e in results)

    def test_query_by_instrument_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for inst in ["guitar_1", "guitar_2", "guitar_1"]:
            entry = PracticeHistoryEntry(
                session_id=f"sess_{inst}",
                instrument_id=inst,
                session={},
                evaluation={},
                assignments={},
                findings_count=0,
                assignments_count=0,
            )
            store.append(entry)

        query = PracticeHistoryQuery(instrument_id="guitar_2")
        results = store.query(query)
        assert len(results) == 1
        assert results[0].instrument_id == "guitar_2"

    def test_query_by_session_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for sess in ["sess_001", "sess_002", "sess_003"]:
            entry = PracticeHistoryEntry(
                session_id=sess,
                instrument_id="guitar_1",
                session={},
                evaluation={},
                assignments={},
                findings_count=0,
                assignments_count=0,
            )
            store.append(entry)

        query = PracticeHistoryQuery(session_id="sess_002")
        results = store.query(query)
        assert len(results) == 1
        assert results[0].session_id == "sess_002"

    def test_query_with_limit(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for i in range(5):
            entry = PracticeHistoryEntry(
                session_id=f"sess_{i:03d}",
                instrument_id="guitar_1",
                session={},
                evaluation={},
                assignments={},
                findings_count=0,
                assignments_count=0,
            )
            store.append(entry)

        query = PracticeHistoryQuery(limit=2)
        results = store.query(query)
        assert len(results) == 2


class TestPracticeHistoryStats:
    """Test PracticeHistoryStore.stats()."""

    def test_empty_stats(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        stats = store.stats()

        assert stats.total_entries == 0
        assert stats.total_findings == 0
        assert stats.total_assignments == 0

    def test_stats_with_entries(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        for i in range(3):
            entry = PracticeHistoryEntry(
                session_id=f"sess_{i:03d}",
                instrument_id="guitar_1",
                session={},
                evaluation={},
                assignments={},
                findings_count=i + 1,
                assignments_count=i,
            )
            store.append(entry)

        stats = store.stats()
        assert stats.total_entries == 3
        assert stats.total_findings == 6  # 1 + 2 + 3
        assert stats.total_assignments == 3  # 0 + 1 + 2


class TestGetBySessionId:
    """Test PracticeHistoryStore.get_by_session_id()."""

    def test_found(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        entry = PracticeHistoryEntry(
            session_id="sess_target",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=5,
            assignments_count=2,
        )
        store.append(entry)

        result = store.get_by_session_id("sess_target")
        assert result is not None
        assert result.session_id == "sess_target"
        assert result.findings_count == 5

    def test_not_found(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")

        entry = PracticeHistoryEntry(
            session_id="sess_other",
            instrument_id="guitar_1",
            session={},
            evaluation={},
            assignments={},
            findings_count=0,
            assignments_count=0,
        )
        store.append(entry)

        result = store.get_by_session_id("sess_nonexistent")
        assert result is None


class TestSchemaExports:
    """Test that practice history is exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            PracticeHistoryEntry,
            PracticeHistoryQuery,
            PracticeHistoryStats,
            PracticeHistoryStore,
            create_history_entry,
        )
        assert PracticeHistoryEntry is not None
        assert PracticeHistoryQuery is not None
        assert PracticeHistoryStats is not None
        assert PracticeHistoryStore is not None
        assert create_history_entry is not None
