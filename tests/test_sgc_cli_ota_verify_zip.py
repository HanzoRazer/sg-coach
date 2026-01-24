"""
Tests for sgc ota-verify-zip CLI command.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sg_coach.cli import main
from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    TimingErrorStats,
    SessionEvents,
    ProgramRef,
    ProgramType,
)
from sg_coach.coach_policy import evaluate_session
from sg_coach.assignment_policy import plan_assignment
from sg_coach.ota_payload import build_assignment_ota_bundle


def _make_session() -> SessionRecord:
    """Create a valid SessionRecord for testing."""
    return SessionRecord(
        session_id=uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="golden_vector_program",
        ),
        timing=SessionTiming(
            bpm=120.0,
            grid=16,
        ),
        duration_s=300,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=98,
            notes_dropped=2,
            timing_error_ms=TimingErrorStats(mean=12.0, std=8.0, max=38.0),
            error_by_step={"0": 5.0, "4": -8.0, "8": 15.0, "12": -3.0},
        ),
        events=SessionEvents(late_drops=1, panic_triggered=False),
    )


def test_sgc_ota_verify_zip_ok(tmp_path: Path):
    """sgc ota-verify-zip should succeed for valid bundle zip."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=True,
    )

    assert res.zip_path is not None
    rc = main(["ota-verify-zip", str(res.zip_path)])
    assert rc == 0
