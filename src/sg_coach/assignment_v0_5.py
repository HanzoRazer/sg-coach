"""
v0.5 Assignment: structured override reasons + decisions.

This replaces feedback mutation with machine-readable audit trails.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OverrideReason(str, Enum):
    """Machine-readable reasons for planner overrides."""

    instability_block = "instability_block"
    instability = "instability"
    tempo_drift = "tempo_drift"
    overplaying = "overplaying"
    low_confidence = "low_confidence"
    inconsistent_dynamics = "inconsistent_dynamics"


class OverrideDecisionV0(BaseModel):
    """
    Structured record of a single override applied by the planner.
    Example: density_cap 0.70 -> 0.55 due to overplaying.
    """

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=64)
    from_value: str = Field(min_length=1, max_length=64)
    to_value: str = Field(min_length=1, max_length=64)
    reason: OverrideReason


class CoachFeedbackV0_5(BaseModel):
    """v0.5 feedback model (unchanged content, not mutated by planner)."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    severity: Literal["info", "warn", "block"] = "info"
    hints: List[str] = Field(default_factory=list)


class AssignmentV0_5(BaseModel):
    """
    v0.5 assignment adds:
      - reasons[]: machine-readable reasons the planner chose recovery constraints
      - overrides[]: explicit (field, from, to, reason) decisions
      - feedback is included but NOT mutated by planner
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_coach_assignment"] = "sg_coach_assignment"
    schema_version: Literal["v0_5"] = "v0_5"

    created_at_utc: datetime = Field(default_factory=utc_now)

    session_id: str = Field(min_length=1, max_length=128)
    instrument_id: str = Field(min_length=1, max_length=128)

    target_tempo_bpm: int = Field(ge=20, le=300)
    tempo_nudge_bpm: int = Field(ge=-20, le=20)
    density_cap: float = Field(ge=0.0, le=1.0)

    duration_seconds: int = Field(ge=10, le=3600)

    allow_probe: bool = False
    probe_reason: Optional[str] = Field(default=None, max_length=200)

    # NEW v0.5:
    reasons: List[OverrideReason] = Field(default_factory=list)
    overrides: List[OverrideDecisionV0] = Field(default_factory=list)

    feedback: CoachFeedbackV0_5


__all__ = [
    "OverrideReason",
    "OverrideDecisionV0",
    "CoachFeedbackV0_5",
    "AssignmentV0_5",
]
