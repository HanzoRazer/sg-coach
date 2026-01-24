"""
Tests for OTA bundle building and verification.
"""
from __future__ import annotations

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
from sg_coach.ota_payload import build_assignment_ota_bundle, verify_bundle_integrity


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


def test_build_and_verify_assignment_ota_bundle(tmp_path: Path):
    """Build a bundle and verify it passes integrity checks."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        product="smart-guitar",
        target_device_model="SG-Pi5-Proto",
        target_min_firmware="0.3.0",
        attachments=[("packs/readme.txt", b"hello")],
    )

    assert res.manifest_path.exists()
    assert res.assignment_path.exists()

    # Verifies hashes/sizes
    assert verify_bundle_integrity(res.bundle_dir)


def test_bundle_without_zip(tmp_path: Path):
    """Bundle can be created without zip."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=False,
    )

    assert res.manifest_path.exists()
    assert res.assignment_path.exists()
    assert res.zip_path is None
    # signature.json is always created (with algorithm: none if no secret)
    assert res.signature_path is not None and res.signature_path.exists()


def test_bundle_with_hmac_and_zip(tmp_path: Path):
    """Bundle with HMAC signing and zip should have all files."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    secret = b"test-secret-key"

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=True,
        hmac_secret=secret,
    )

    assert res.manifest_path.exists()
    assert res.assignment_path.exists()
    assert res.signature_path is not None and res.signature_path.exists()
    assert res.zip_path is not None and res.zip_path.exists()

    # Verification should pass
    assert verify_bundle_integrity(res.bundle_dir)
