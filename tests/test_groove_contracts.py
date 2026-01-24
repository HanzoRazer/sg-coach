"""
Tests for groove contracts models.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sg_coach.groove_contracts import ControlIntentV0, GrooveSnapshotV0


def test_groove_snapshot_valid():
    """Test valid GrooveSnapshotV0 creation."""
    snap = GrooveSnapshotV0(
        tempo_bpm_est=120.0,
        stability=0.85,
        drift_ppm=500.0,
        density=0.6,
        last_update_ms=1000,
    )

    assert snap.schema_id == "sg_groove_snapshot"
    assert snap.schema_version == "v0"
    assert snap.tempo_bpm_est == 120.0
    assert snap.stability == 0.85


def test_groove_snapshot_bounds():
    """Test GrooveSnapshotV0 enforces bounds."""
    with pytest.raises(ValidationError):
        GrooveSnapshotV0(
            tempo_bpm_est=10.0,  # Below 20
            stability=0.5,
            drift_ppm=0,
            density=0.5,
            last_update_ms=0,
        )

    with pytest.raises(ValidationError):
        GrooveSnapshotV0(
            tempo_bpm_est=100.0,
            stability=1.5,  # Above 1.0
            drift_ppm=0,
            density=0.5,
            last_update_ms=0,
        )


def test_control_intent_valid():
    """Test valid ControlIntentV0 creation."""
    intent = ControlIntentV0(
        target_tempo_bpm=100,
        tempo_nudge_bpm=-5,
        density_cap=0.7,
        allow_probe=True,
        probe_reason="Player has been stable for 30 seconds.",
    )

    assert intent.schema_id == "sg_groove_control_intent"
    assert intent.schema_version == "v0"
    assert intent.target_tempo_bpm == 100
    assert intent.tempo_nudge_bpm == -5
    assert intent.allow_probe is True


def test_control_intent_nudge_bounds():
    """Test ControlIntentV0 nudge bounds."""
    with pytest.raises(ValidationError):
        ControlIntentV0(
            target_tempo_bpm=100,
            tempo_nudge_bpm=-25,  # Below -20
            density_cap=0.5,
        )

    with pytest.raises(ValidationError):
        ControlIntentV0(
            target_tempo_bpm=100,
            tempo_nudge_bpm=25,  # Above 20
            density_cap=0.5,
        )


def test_control_intent_json_roundtrip():
    """Test ControlIntentV0 JSON serialization."""
    intent = ControlIntentV0(
        target_tempo_bpm=96,
        tempo_nudge_bpm=-2,
        density_cap=0.55,
        allow_probe=False,
    )

    json_str = intent.model_dump_json()
    recovered = ControlIntentV0.model_validate_json(json_str)

    assert recovered == intent
