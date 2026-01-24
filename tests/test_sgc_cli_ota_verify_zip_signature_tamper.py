"""
Tests for signature-only tamper detection.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

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


def _tamper_signature_in_zip(src_zip: Path, dst_zip: Path) -> None:
    """
    Copy src_zip -> dst_zip, but replace signature.json contents ONLY.
    This should fail verification due to signature mismatch.
    """
    with zipfile.ZipFile(src_zip, "r") as zin:
        names = zin.namelist()

        sig_candidates = [n for n in names if n.endswith("signature.json")]
        if len(sig_candidates) != 1:
            raise AssertionError(f"expected exactly one signature.json in zip, found: {sig_candidates}")
        sig_name = sig_candidates[0]

        with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                data = zin.read(name)

                if name == sig_name:
                    try:
                        obj = json.loads(data.decode("utf-8"))
                    except Exception:
                        obj = {"algorithm": "none"}

                    # Intentionally wrong subject hash (64 hex chars)
                    obj["subject"] = obj.get("subject", "manifest.json")
                    obj["subject_sha256"] = "0" * 64
                    obj["signature"] = "0" * 64  # fake signature

                    new_bytes = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")
                    zout.writestr(name, new_bytes)
                else:
                    zout.writestr(name, data)


def test_sgc_ota_verify_zip_fails_on_signature_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """ota-verify-zip with --secret should fail when signature is wrong."""
    session = _make_session()
    ev = evaluate_session(session)
    assignment = plan_assignment(ev, session.program_ref)

    secret = "test-hmac-secret"

    res = build_assignment_ota_bundle(
        assignment=assignment,
        out_dir=tmp_path,
        make_zip=True,
        hmac_secret=secret.encode("utf-8"),
    )
    assert res.zip_path is not None
    assert res.zip_path.exists()

    # Create signature-tampered zip
    tampered_zip = tmp_path / f"{res.zip_path.stem}_SIG_TAMPERED.zip"
    _tamper_signature_in_zip(res.zip_path, tampered_zip)
    assert tampered_zip.exists()

    # Verify with secret should FAIL (nonzero) due to wrong signature
    rc = main(["ota-verify-zip", str(tampered_zip), "--secret", secret])
    out = capsys.readouterr()
    assert rc != 0

    msg = (out.err + "\n" + out.out).lower()
    # Expect a signature-related mismatch
    assert "fail" in msg or "signature" in msg, msg
