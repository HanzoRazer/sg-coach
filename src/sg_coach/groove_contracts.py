"""
Groove Layer Contracts (v0.3)

SG-only groove snapshot and control intent contracts.
These are the bridge between Groove Layer and Coach.

Keep them small and stable; never embed raw audio/MIDI here.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class GrooveSnapshotV0(BaseModel):
    """
    SG-only groove snapshot contract (input to coach planning).
    This is the bridge between Groove Layer and Coach.

    Keep it small and stable; do NOT embed raw audio/MIDI here.
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_groove_snapshot"] = "sg_groove_snapshot"
    schema_version: Literal["v0"] = "v0"

    tempo_bpm_est: float = Field(ge=20.0, le=300.0)
    stability: float = Field(ge=0.0, le=1.0)
    drift_ppm: float = Field(ge=0.0, le=250000.0)
    density: float = Field(ge=0.0, le=1.0)

    last_update_ms: int = Field(ge=0)


class ControlIntentV0(BaseModel):
    """
    SG-only control intent contract (what Groove Layer suggests next).
    Coach can consume this as a hint, but remains the authority for assignments.

    - target_tempo_bpm: desired tempo for next segment
    - tempo_nudge_bpm: small correction step
    - density_cap: reduce/limit rhythmic density
    - allow_probe: whether Groove Layer says probing is eligible
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_groove_control_intent"] = "sg_groove_control_intent"
    schema_version: Literal["v0"] = "v0"

    target_tempo_bpm: int = Field(ge=20, le=300)
    tempo_nudge_bpm: int = Field(ge=-20, le=20)
    density_cap: float = Field(ge=0.0, le=1.0)

    allow_probe: bool = False
    probe_reason: Optional[str] = Field(default=None, max_length=200)


__all__ = ["GrooveSnapshotV0", "ControlIntentV0"]
