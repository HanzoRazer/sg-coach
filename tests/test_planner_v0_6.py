"""
Tests for v0.6 planner: history + anti-oscillation.
"""
from __future__ import annotations

import json
from pathlib import Path

from sg_coach.evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from sg_coach.planner_v0_6 import plan_next_v0_6
from sg_coach.assignment_v0_6 import CommitMode, CommitStateV0


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


def test_vector_006_history_anti_oscillation_commit_window():
    """Test that oscillation detection triggers commit window."""
    vec = _fixtures_root()

    ev = EvaluationV0_3.model_validate_json(
        (vec / "evaluation.json").read_text(encoding="utf-8")
    )
    fb = CoachFeedbackV0.model_validate_json(
        (vec / "feedback.json").read_text(encoding="utf-8")
    )

    hist_assign = json.loads(
        (vec / "history_assignments.json").read_text(encoding="utf-8")
    )

    produced = plan_next_v0_6(
        ev,
        fb,
        history_assignments=hist_assign,
        history_evaluations=[],
        prior_commit_state=CommitStateV0(),
    )

    expected = json.loads(
        (vec / "assignment_v0_6.json").read_text(encoding="utf-8")
    )

    prod = produced.model_dump(mode="json")
    prod["created_at_utc"] = expected["created_at_utc"]

    assert prod == expected


def test_planner_v0_6_no_history_no_commit():
    """Test that without history, no commit window is triggered."""
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

    assignment = plan_next_v0_6(ev, fb, history_assignments=[], prior_commit_state=None)

    # No oscillation → no commit state
    assert assignment.commit_state.mode == CommitMode.none
    assert assignment.commit_state.cycles_remaining == 0
    # Intent should pass through
    assert assignment.tempo_nudge_bpm == 1
    assert assignment.allow_probe is True


def test_planner_v0_6_commit_window_decrements():
    """Test that commit window decrements each cycle."""
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
        timing_score=0.9,
        consistency_score=0.85,
        flags={},
    )

    fb = CoachFeedbackV0(
        severity="info",
        message="Keep going.",
        hints=[],
    )

    # Start with existing commit state
    prior = CommitStateV0(
        mode=CommitMode.hold,
        cycles_remaining=3,
        note="test",
    )

    assignment = plan_next_v0_6(ev, fb, history_assignments=[], prior_commit_state=prior)

    # Should decrement to 2
    assert assignment.commit_state.mode == CommitMode.hold
    assert assignment.commit_state.cycles_remaining == 2


def test_planner_v0_6_commit_resets_when_zero():
    """Test that commit state resets when cycles reach zero."""
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
        allow_probe=True,
        probe_reason="ready",
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
        message="Done.",
        hints=[],
    )

    # Prior with 1 remaining → will decrement to 0 and reset
    prior = CommitStateV0(
        mode=CommitMode.cooldown,
        cycles_remaining=1,
        note="last cycle",
    )

    assignment = plan_next_v0_6(ev, fb, history_assignments=[], prior_commit_state=prior)

    # Should reset to none
    assert assignment.commit_state.mode == CommitMode.none
    assert assignment.commit_state.cycles_remaining == 0


def test_planner_v0_6_safety_override_triggers_cooldown():
    """Test that safety overrides trigger probe cooldown."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.55,
        drift_ppm=2000.0,
        density=0.8,
        last_update_ms=1000,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=100,
        tempo_nudge_bpm=2,
        density_cap=0.75,
        allow_probe=True,
        probe_reason="attempt",
    )

    ev = EvaluationV0_3(
        session_id="test-session",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.6,
        consistency_score=0.5,
        flags={
            "instability": True,
            "tempo_drift": True,
        },
    )

    fb = CoachFeedbackV0(
        severity="warn",
        message="Issues detected.",
        hints=[],
    )

    assignment = plan_next_v0_6(ev, fb, history_assignments=[], prior_commit_state=None)

    # Safety override should trigger cooldown
    assert assignment.commit_state.mode == CommitMode.cooldown
    assert assignment.commit_state.cycles_remaining == 2  # default probe_cooldown_cycles
    assert assignment.allow_probe is False
