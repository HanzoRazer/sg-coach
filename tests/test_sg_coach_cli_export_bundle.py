"""
Tests for sg-coach CLI export-bundle command.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sg_coach.cli import main
from sg_coach.schemas import (
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    TimingErrorStats,
)


def _make_session() -> SessionRecord:
    return SessionRecord(
        session_id=uuid4(),
        instrument_id="sg-000142",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="salsa_minor_Dm",
            hash="sha256:abc123",
        ),
        timing=SessionTiming(
            bpm=110,
            grid=16,
            strict=True,
            late_drop_ms=35,
            ghost_vel_max=22,
            panic_enabled=True,
        ),
        duration_s=120,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=100,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=14.0, std=6.0, max=40.0),
            error_by_step={"7": 32.0, "3": 18.0},
        ),
        events={"late_drops": 2, "panic_triggered": False},
    )


def test_cli_export_bundle_roundtrip(tmp_path: Path):
    """Full CLI roundtrip: session.json -> bundle.json."""
    session = _make_session()
    session_json = tmp_path / "session.json"
    # Write JSON-safe session (UUID/datetime serialized by pydantic)
    session_json.write_text(
        json.dumps(session.model_dump(mode="json")),
        encoding="utf-8",
    )

    out_json = tmp_path / "bundle.json"
    rc = main(["export-bundle", "--in", str(session_json), "--out", str(out_json)])
    assert rc == 0
    assert out_json.exists()

    obj = json.loads(out_json.read_text(encoding="utf-8"))
    assert obj["kind"] == "sg_coach_bundle"
    assert "session" in obj and "evaluation" in obj and "assignment" in obj
    assert isinstance(obj["assignment"]["assignment_id"], str)
