"""
Tests for v0.7 store shim using vector_006 fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from sg_coach.evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from sg_coach.store_shim_v0_7 import InMemoryCoachStoreV0_7


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


def test_store_shim_vector_006_produces_assignment_and_persists_commit_state():
    """Test that store shim produces assignment and persists commit_state."""
    vec = _fixtures_root()

    ev = EvaluationV0_3.model_validate_json(
        (vec / "evaluation.json").read_text(encoding="utf-8")
    )
    fb = CoachFeedbackV0.model_validate_json(
        (vec / "feedback.json").read_text(encoding="utf-8")
    )

    store = InMemoryCoachStoreV0_7()

    # Seed history assignments as SimpleNamespace objects (duck typing)
    hist = json.loads(
        (vec / "history_assignments.json").read_text(encoding="utf-8")
    )
    for item in hist:
        store.append_assignment(
            SimpleNamespace(**item),
            session_id=ev.session_id,
            instrument_id=ev.instrument_id,
        )

    a = store.next_assignment(ev, fb)

    st = store.get(ev.session_id)
    assert st is not None
    assert st.commit_state.mode in ("hold", "cooldown", "none")
    assert len(st.assignments) >= 4  # 3 seeded + new
    assert a.session_id == ev.session_id


def test_store_shim_empty_history_works():
    """Test that store shim works with no prior history."""
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
        session_id="test-session-empty",
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

    store = InMemoryCoachStoreV0_7()

    a = store.next_assignment(ev, fb)

    st = store.get(ev.session_id)
    assert st is not None
    assert len(st.evaluations) == 1
    assert len(st.assignments) == 1
    assert a.session_id == ev.session_id


def test_store_shim_multiple_cycles_persist_state():
    """Test that store shim persists state across multiple cycles."""
    from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0
    from sg_coach.assignment_v0_6 import CommitMode

    store = InMemoryCoachStoreV0_7()

    # First cycle
    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.55,  # Low stability triggers cooldown
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

    ev1 = EvaluationV0_3(
        session_id="test-multi-cycle",
        instrument_id="test-instrument",
        groove=groove,
        control_intent=intent,
        timing_score=0.6,
        consistency_score=0.5,
        flags={"instability": True, "tempo_drift": True},
    )

    fb = CoachFeedbackV0(
        severity="warn",
        message="Issues detected.",
        hints=[],
    )

    a1 = store.next_assignment(ev1, fb)

    # Should trigger cooldown
    assert a1.commit_state.mode == CommitMode.cooldown
    assert a1.commit_state.cycles_remaining > 0

    # Second cycle - state should persist and decrement
    ev2 = EvaluationV0_3(
        session_id="test-multi-cycle",
        instrument_id="test-instrument",
        groove=GrooveSnapshotV0(
            tempo_bpm_est=100.0,
            stability=0.85,  # Better now
            drift_ppm=300.0,
            density=0.6,
            last_update_ms=2000,
        ),
        control_intent=ControlIntentV0(
            target_tempo_bpm=100,
            tempo_nudge_bpm=0,
            density_cap=0.70,
            allow_probe=True,
            probe_reason="recovering",
        ),
        timing_score=0.8,
        consistency_score=0.75,
        flags={},
    )

    a2 = store.next_assignment(ev2, fb)

    st = store.get("test-multi-cycle")
    assert st is not None
    assert len(st.evaluations) == 2
    assert len(st.assignments) == 2
