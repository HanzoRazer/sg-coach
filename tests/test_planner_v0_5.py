"""
Tests for v0.5 planner: structured overrides + reasons.
"""
from __future__ import annotations

import json
from pathlib import Path

from sg_coach.evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from sg_coach.planner_v0_5 import plan_next_v0_5
from sg_coach.assignment_v0_5 import OverrideReason


def _fixtures_root() -> Path:
    """Return the path to the fixtures directory."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "sg_coach"
        / "fixtures"
        / "golden"
        / "vector_005"
    )


def test_vector_005_structured_overrides_and_reasons():
    """Test that v0.5 planner emits structured overrides and reasons."""
    vec = _fixtures_root()

    ev = EvaluationV0_3.model_validate_json(
        (vec / "evaluation.json").read_text(encoding="utf-8")
    )
    fb = CoachFeedbackV0.model_validate_json(
        (vec / "feedback.json").read_text(encoding="utf-8")
    )

    produced = plan_next_v0_5(ev, fb)

    expected = json.loads((vec / "assignment_v0_5.json").read_text(encoding="utf-8"))

    prod = produced.model_dump(mode="json")
    # normalize timestamp
    prod["created_at_utc"] = expected["created_at_utc"]

    assert prod == expected


def test_planner_v0_5_no_flags_no_overrides():
    """Test that no flags means no overrides (clean intent passthrough)."""
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

    assignment = plan_next_v0_5(ev, fb)

    # Should use intent values directly with no overrides
    assert assignment.target_tempo_bpm == 105
    assert assignment.tempo_nudge_bpm == 3
    assert assignment.density_cap == 0.75
    assert assignment.allow_probe is True
    assert assignment.probe_reason == "stable_for_30s"
    assert assignment.reasons == []
    assert assignment.overrides == []
    # Feedback should be unchanged
    assert assignment.feedback.message == fb.message


def test_planner_v0_5_records_all_overrides():
    """Test that all flag-triggered changes are recorded."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.50,
        drift_ppm=2000.0,
        density=0.85,
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
        flags={
            "instability": True,
            "tempo_drift": True,
            "overplaying": True,
        },
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Test message.",
        hints=[],
    )

    assignment = plan_next_v0_5(ev, fb)

    # Check reasons list
    assert OverrideReason.instability in assignment.reasons
    assert OverrideReason.tempo_drift in assignment.reasons
    assert OverrideReason.overplaying in assignment.reasons

    # Check overrides are recorded
    override_fields = [o.field for o in assignment.overrides]
    assert "allow_probe" in override_fields
    assert "tempo_nudge_bpm" in override_fields
    assert "density_cap" in override_fields

    # Check final values reflect overrides
    assert assignment.allow_probe is False
    assert assignment.tempo_nudge_bpm < 0
    assert assignment.density_cap <= 0.55

    # Feedback should NOT be mutated
    assert assignment.feedback.message == "Test message."


def test_planner_v0_5_soft_reasons_recorded():
    """Test that soft reasons (no knob change) are still recorded."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.90,
        drift_ppm=200.0,
        density=0.5,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=100,
        tempo_nudge_bpm=0,
        density_cap=0.70,
        allow_probe=False,
        probe_reason=None,
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.5,  # Low
        consistency_score=0.6,  # Low
        flags={
            "low_confidence": True,
            "inconsistent_dynamics": True,
        },
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Some message.",
        hints=[],
    )

    assignment = plan_next_v0_5(ev, fb)

    # Soft reasons should be recorded even without knob changes
    assert OverrideReason.low_confidence in assignment.reasons
    assert OverrideReason.inconsistent_dynamics in assignment.reasons

    # No overrides since no knob changes
    assert len(assignment.overrides) == 0
