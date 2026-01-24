"""
Tests for EvaluationBuilderV0_3 with groove-aware evaluation.
"""
from __future__ import annotations

import json
from pathlib import Path

from sg_coach.evaluation_builder_v0_3 import EvaluationBuilderV0_3
from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0
from sg_coach.schemas import SessionRecord


def _fixtures_root() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).resolve().parent.parent / "src" / "sg_coach" / "fixtures" / "golden" / "vector_003"


def test_vector_003_groove_aware_eval_and_feedback():
    """Test that EvaluationBuilderV0_3 produces correct evaluation and feedback."""
    vec = _fixtures_root()

    session = SessionRecord.model_validate_json(
        (vec / "session.json").read_text(encoding="utf-8")
    )

    groove = GrooveSnapshotV0(
        tempo_bpm_est=96.0,
        stability=0.62,
        drift_ppm=1800.0,
        density=0.82,
        last_update_ms=1510,
    )

    intent = ControlIntentV0(
        target_tempo_bpm=96,
        tempo_nudge_bpm=-2,
        density_cap=0.55,
        allow_probe=False,
        probe_reason=None,
    )

    builder = EvaluationBuilderV0_3()
    ev, fb = builder.build(session=session, groove=groove, control_intent=intent)

    expected_ev = json.loads((vec / "evaluation.json").read_text(encoding="utf-8"))
    expected_fb = json.loads((vec / "feedback.json").read_text(encoding="utf-8"))

    # Compare deterministic fields; ignore timestamps by overwriting them
    ev_dict = ev.model_dump(mode="json")
    fb_dict = fb.model_dump(mode="json")

    ev_dict["evaluated_at_utc"] = expected_ev["evaluated_at_utc"]
    fb_dict["created_at_utc"] = expected_fb["created_at_utc"]

    assert ev_dict == expected_ev
    assert fb_dict == expected_fb


def test_evaluation_builder_detects_instability():
    """Test that low stability triggers instability flags."""
    from uuid import uuid4

    from sg_coach.schemas import (
        PerformanceSummary,
        ProgramRef,
        ProgramType,
        SessionEvents,
        SessionTiming,
        TimingErrorStats,
    )

    session = SessionRecord(
        session_id=uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test"),
        timing=SessionTiming(bpm=100.0, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=50,
            notes_played=48,
            notes_dropped=2,
            timing_error_ms=TimingErrorStats(mean=10.0, std=5.0, max=20.0),
        ),
        events=SessionEvents(),
    )

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.50,  # Below STABILITY_BLOCK
        drift_ppm=500.0,
        density=0.5,
        last_update_ms=1000,
    )

    builder = EvaluationBuilderV0_3()
    ev, fb = builder.build(session=session, groove=groove)

    assert ev.flags.get("instability") is True
    assert ev.flags.get("instability_block") is True
    assert fb.severity == "block"
    assert "simplify and slow down" in fb.message.lower()


def test_evaluation_builder_good_session():
    """Test that good session produces positive feedback."""
    from uuid import uuid4

    from sg_coach.schemas import (
        PerformanceSummary,
        ProgramRef,
        ProgramType,
        SessionEvents,
        SessionTiming,
        TimingErrorStats,
    )

    session = SessionRecord(
        session_id=uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test"),
        timing=SessionTiming(bpm=100.0, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=50,
            notes_played=50,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=8.0, std=4.0, max=15.0),
        ),
        events=SessionEvents(),
    )

    groove = GrooveSnapshotV0(
        tempo_bpm_est=100.0,
        stability=0.90,
        drift_ppm=200.0,
        density=0.5,
        last_update_ms=1000,
    )

    builder = EvaluationBuilderV0_3()
    ev, fb = builder.build(session=session, groove=groove)

    assert not ev.flags  # No flags for good session
    assert fb.severity == "info"
    assert "good control" in fb.message.lower()
