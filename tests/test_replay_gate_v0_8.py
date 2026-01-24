"""
Tests for v0.8 replay gate using vector_006 fixtures.
"""
from __future__ import annotations

from pathlib import Path

from sg_coach.replay_gate_v0_8 import replay_vector_dir


def _fixtures_root() -> Path:
    """Return the path to the vector_006 fixtures directory."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "sg_coach"
        / "fixtures"
        / "golden"
        / "vector_006"
    )


def test_replay_gate_vector_006_sqlite(tmp_path: Path):
    """Test replay gate with SQLite store against vector_006."""
    vec = _fixtures_root()

    db = tmp_path / "coach.db"
    res = replay_vector_dir(vec, db_path=str(db))

    assert res.ok, res.reason


def test_replay_gate_vector_006_memory():
    """Test replay gate with in-memory SQLite."""
    vec = _fixtures_root()

    res = replay_vector_dir(vec, db_path=":memory:")

    assert res.ok, res.reason


def test_replay_gate_missing_fixture(tmp_path: Path):
    """Test replay gate fails gracefully for missing fixtures."""
    # Create empty vector dir
    vec = tmp_path / "empty_vector"
    vec.mkdir()

    res = replay_vector_dir(vec, db_path=":memory:")

    assert not res.ok
    assert "Missing required fixture" in res.reason
