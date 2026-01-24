"""
Tests for v0.8 SQLite store.
"""
from __future__ import annotations

from pathlib import Path

from sg_coach.assignment_v0_6 import CommitMode, CommitStateV0
from sg_coach.evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0
from sg_coach.sqlite_store_v0_8 import SQLiteCoachStoreV0_8, SqliteStoreConfigV0_8


def test_sqlite_store_creates_tables(tmp_path: Path):
    """Test that SQLite store creates required tables."""
    db_path = tmp_path / "test.db"
    store = SQLiteCoachStoreV0_8(SqliteStoreConfigV0_8(db_path=str(db_path)))

    # Check tables exist
    cur = store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]

    assert "sessions" in tables
    assert "evaluations" in tables
    assert "assignments" in tables

    store.close()


def test_sqlite_store_session_lifecycle(tmp_path: Path):
    """Test session creation and commit state persistence."""
    db_path = tmp_path / "test.db"
    store = SQLiteCoachStoreV0_8(SqliteStoreConfigV0_8(db_path=str(db_path)))

    # Create session
    store.get_or_create_session("sess-001", "SG-2026-001")

    # Default commit state
    cs = store.get_commit_state("sess-001")
    assert cs.mode == CommitMode.none
    assert cs.cycles_remaining == 0

    # Update commit state
    new_cs = CommitStateV0(mode=CommitMode.hold, cycles_remaining=3, note="test")
    store.set_commit_state("sess-001", new_cs)

    # Verify persistence
    cs2 = store.get_commit_state("sess-001")
    assert cs2.mode == CommitMode.hold
    assert cs2.cycles_remaining == 3
    assert cs2.note == "test"

    store.close()


def test_sqlite_store_next_assignment(tmp_path: Path):
    """Test next_assignment flow with SQLite store."""
    db_path = tmp_path / "test.db"
    store = SQLiteCoachStoreV0_8(SqliteStoreConfigV0_8(db_path=str(db_path)))

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.90,
        drift_ppm=200.0,
        density=0.5,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=100,
        tempo_nudge_bpm=1,
        density_cap=0.70,
        allow_probe=True,
        probe_reason="stable",
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.9,
        consistency_score=0.85,
        flags={},
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="All good.",
        hints=[],
    )

    assignment = store.next_assignment(ev, fb)

    assert assignment.session_id == "test-session"
    assert assignment.target_tempo_bpm == 100

    # Check history was persisted
    evals = store.get_recent_evaluations("test-session", 10)
    assigns = store.get_recent_assignments("test-session", 10)

    assert len(evals) == 1
    assert len(assigns) == 1

    store.close()


def test_sqlite_store_memory_mode():
    """Test in-memory SQLite store."""
    store = SQLiteCoachStoreV0_8(SqliteStoreConfigV0_8(db_path=":memory:"))

    store.get_or_create_session("mem-sess", "SG-MEM-001")

    cs = store.get_commit_state("mem-sess")
    assert cs.mode == CommitMode.none

    store.close()
