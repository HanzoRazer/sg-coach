"""
Tests for sgc CLI ota-bundle command.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from sg_coach.cli import main


def _make_session_record(session_id: str = "00000000-0000-0000-0000-0000000000dd") -> dict:
    """Create a valid SessionRecord for testing."""
    return {
        "session_id": session_id,
        "instrument_id": "test-guitar-001",
        "engine_version": "zt-band@0.2.0",
        "program_ref": {
            "type": "ztprog",
            "name": "golden_vector_program",
            "hash": None,
        },
        "timing": {
            "bpm": 120.0,
            "grid": 16,
            "clave": None,
            "strict": True,
            "strict_window_ms": 35,
            "late_drop_ms": 35,
            "ghost_vel_max": 22,
            "panic_enabled": True,
        },
        "duration_s": 300,
        "performance": {
            "bars_played": 8,
            "notes_expected": 100,
            "notes_played": 98,
            "notes_dropped": 2,
            "timing_error_ms": {
                "mean": 12.0,
                "std": 8.0,
                "max": 38.0,
            },
            "error_by_step": {
                "0": 5.0,
                "4": -8.0,
                "8": 15.0,
                "12": -3.0,
            },
        },
        "events": {
            "late_drops": 1,
            "panic_triggered": False,
        },
    }


def test_sgc_ota_bundle_creates_folder_and_zip(tmp_path: Path):
    """sgc ota-bundle should create bundle folder and zip."""
    session = _make_session_record()

    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out" / "ota"

    rc = main(
        [
            "ota-bundle",
            "--session",
            str(session_path),
            "--out",
            str(out_dir),
            "--zip",
        ]
    )
    assert rc == 0

    # There should be exactly one bundle folder created inside out_dir
    assert out_dir.exists()
    bundle_dirs = [p for p in out_dir.iterdir() if p.is_dir()]
    assert len(bundle_dirs) == 1
    bundle_dir = bundle_dirs[0]

    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "assignment.json").exists()
    # signature.json always created (with or without HMAC)
    assert (bundle_dir / "signature.json").exists()

    # zip created next to folder
    zip_path = out_dir / f"{bundle_dir.name}.zip"
    assert zip_path.exists()


def test_sgc_ota_bundle_with_hmac_secret(tmp_path: Path):
    """sgc ota-bundle should sign with HMAC when --secret provided."""
    session = _make_session_record("00000000-0000-0000-0000-0000000000de")

    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out" / "ota"

    rc = main(
        [
            "ota-bundle",
            "--session",
            str(session_path),
            "--out",
            str(out_dir),
            "--secret",
            "test-secret-key",
        ]
    )
    assert rc == 0

    bundle_dirs = [p for p in out_dir.iterdir() if p.is_dir()]
    assert len(bundle_dirs) == 1
    bundle_dir = bundle_dirs[0]

    # Should have signature.json with actual signature
    sig_path = bundle_dir / "signature.json"
    assert sig_path.exists()

    sig_data = json.loads(sig_path.read_text(encoding="utf-8"))
    assert sig_data["algorithm"] == "HS256"
    assert sig_data["signature"] is not None
    assert len(sig_data["signature"]) == 64  # SHA256 hex
