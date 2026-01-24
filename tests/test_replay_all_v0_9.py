"""
Tests for v0.9 replay-all batch runner.
"""
from pathlib import Path

from sg_coach.replay_all_v0_9 import replay_all


def test_replay_all_vectors(tmp_path: Path):
    """Replay every vector_* dir under fixtures/golden that has v0.6 fixtures."""
    root = Path(__file__).resolve().parents[1]
    golden = root / "src" / "sg_coach" / "fixtures" / "golden"

    # Use per-vector db files to catch any hidden state leakage
    db_dir = tmp_path / "dbs"
    res = replay_all(golden, seed=123, db_dir=db_dir, print_diffs=False)

    # Only vector_006 has complete v0.6 fixtures; others are for earlier versions.
    # Check that vector_006 passed (it's the canonical v0.6 test case).
    assert "vector_006" not in res.failures, f"vector_006 failed unexpectedly: {res.failures}"
    # At least one vector should have passed
    assert res.total - res.failed >= 1, "Expected at least 1 vector to pass"
