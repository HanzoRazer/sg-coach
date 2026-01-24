"""
Tests for OTA bundle zip creation and signature.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from uuid import uuid4

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
from sg_coach.ota_payload import (
    build_assignment_ota_bundle,
    verify_bundle_integrity,
    verify_bundle_signature,
)


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


def test_bundle_zip_and_signature_created_and_valid(tmp_path: Path):
    """Bundle zip and signature should be created and valid."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    secret = b"test-hmac-secret"

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=True,
        hmac_secret=secret,
    )

    assert res.signature_path is not None
    assert res.signature_path.exists()

    assert res.zip_path is not None
    assert res.zip_path.exists()

    # Verify folder integrity checks still pass
    assert verify_bundle_integrity(res.bundle_dir)
    assert verify_bundle_signature(res.bundle_dir, secret=secret)

    # Zip contains expected files
    with zipfile.ZipFile(res.zip_path, "r") as z:
        names = set(z.namelist())
        assert "manifest.json" in names
        assert "assignment.json" in names
        assert "signature.json" in names


def test_signature_mismatch_fails(tmp_path: Path):
    """Tampered manifest should fail signature verification."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    secret = b"test-hmac-secret"

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=False,
        hmac_secret=secret,
    )
    assert res.signature_path is not None

    # Tamper manifest to invalidate signature
    manifest_path = res.bundle_dir / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["tampered"] = True
    manifest_path.write_text(json.dumps(manifest_data) + "\n", encoding="utf-8")

    # Signature verification should now fail
    assert not verify_bundle_signature(res.bundle_dir, secret=secret)
