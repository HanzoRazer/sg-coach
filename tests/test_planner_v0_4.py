"""
Tests for v0.4 planner: consumes control_intent + flags.
"""
from __future__ import annotations

import json
from pathlib import Path

from sg_coach.evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from sg_coach.planner_v0_4 import plan_next_v0_4, AssignmentV0_4


def _fixtures_root() -> Path:
    """Return the path to the fixtures directory."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "sg_coach"
        / "fixtures"
        / "golden"
        / "vector_004"
    )


def test_vector_004_planner_consumes_intent_and_flags():
    """Test that planner applies safety overrides from flags."""
    vec = _fixtures_root()

    ev = EvaluationV0_3.model_validate_json(
        (vec / "evaluation.json").read_text(encoding="utf-8")
    )
    fb = CoachFeedbackV0.model_validate_json(
        (vec / "feedback.json").read_text(encoding="utf-8")
    )

    produced = plan_next_v0_4(ev, fb)

    expected = json.loads((vec / "assignment.json").read_text(encoding="utf-8"))

    prod = produced.model_dump(mode="json")
    # Normalize timestamps for deterministic compare
    prod["created_at_utc"] = expected["created_at_utc"]

    assert prod == expected


def test_planner_uses_intent_when_no_flags():
    """Test that planner uses control_intent values when flags are empty."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.90,
        drift_ppm=200.0,
        density=0.5,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=105,
        tempo_nudge_bpm=3,
        density_cap=0.75,
        allow_probe=True,
        probe_reason="stable_for_30s",
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.9,
        consistency_score=0.85,
        flags={},  # No flags
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Good control—take a small step forward.",
        hints=["Keep accents consistent."],
    )

    assignment = plan_next_v0_4(ev, fb)

    # Should use intent values directly
    assert assignment.target_tempo_bpm == 105
    assert assignment.tempo_nudge_bpm == 3
    assert assignment.density_cap == 0.75
    assert assignment.allow_probe is True
    assert assignment.probe_reason == "stable_for_30s"


def test_planner_overrides_on_instability():
    """Test that instability flag disables probe and reduces tempo."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.50,
        drift_ppm=500.0,
        density=0.5,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=105,
        tempo_nudge_bpm=3,
        density_cap=0.75,
        allow_probe=True,
        probe_reason="stable_for_30s",
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.9,
        consistency_score=0.85,
        flags={"instability": True},
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Test message.",
        hints=[],
    )

    assignment = plan_next_v0_4(ev, fb)

    # Instability should disable probe and reduce tempo nudge
    assert assignment.allow_probe is False
    assert assignment.probe_reason is None
    assert assignment.tempo_nudge_bpm < 0  # Should be negative
    assert assignment.density_cap <= 0.55  # Should be reduced


def test_planner_overrides_on_tempo_drift():
    """Test that tempo_drift flag disables probe."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.85,
        drift_ppm=2000.0,
        density=0.5,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=105,
        tempo_nudge_bpm=3,
        density_cap=0.75,
        allow_probe=True,
        probe_reason="stable_for_30s",
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.9,
        consistency_score=0.85,
        flags={"tempo_drift": True},
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Test message.",
        hints=[],
    )

    assignment = plan_next_v0_4(ev, fb)

    # Tempo drift should disable probe
    assert assignment.allow_probe is False
    assert assignment.probe_reason is None
    assert assignment.tempo_nudge_bpm <= -2  # Drift override
    assert "re-center time" in assignment.feedback.message.lower()
