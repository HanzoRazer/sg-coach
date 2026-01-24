# tests/test_groove_replay_gate_v1.py
"""
Pytest hook for Groove Profile -> Intent golden vector replay.
"""
from __future__ import annotations

from pathlib import Path

from sg_coach.groove_replay_gate_v1 import replay_all


def test_groove_profile_to_intent_golden_vectors():
    """All groove vectors must replay deterministically."""
    root = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "groove_vectors"
    res = replay_all(root)
    assert res.ok, res.message
