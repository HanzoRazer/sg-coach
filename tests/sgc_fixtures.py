"""
Shared test fixtures for sg_coach tests.
"""
from __future__ import annotations


def make_session_record(
    session_id: str = "00000000-0000-0000-0000-0000000000dd",
    bpm: float = 120.0,
    error_by_step: dict | None = None,
) -> dict:
    """Create a valid SessionRecord for testing."""
    if error_by_step is None:
        error_by_step = {
            "0": 5.0,
            "4": -8.0,
            "8": 15.0,
            "12": -3.0,
        }

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
            "bpm": bpm,
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
            "error_by_step": error_by_step,
        },
        "events": {
            "late_drops": 1,
            "panic_triggered": False,
        },
    }
