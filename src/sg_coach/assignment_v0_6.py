"""
v0.6 Assignment: history-aware + anti-oscillation commit state.

Extends v0.5 with:
- CommitMode enum (none, hold, cooldown)
- CommitStateV0 for carrying commit window state between cycles
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .assignment_v0_5 import OverrideDecisionV0, OverrideReason, CoachFeedbackV0_5


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommitMode(str, Enum):
    """Commit window modes for anti-oscillation."""

    none = "none"
    hold = "hold"          # hold knobs steady for N cycles
    cooldown = "cooldown"  # probing forbidden for N cycles


class CommitStateV0(BaseModel):
    """
    State the planner emits so the runtime (or session store) can carry it forward.
    """

    model_config = ConfigDict(extra="forbid")

    mode: CommitMode = CommitMode.none
    cycles_remaining: int = Field(ge=0, le=64, default=0)
    note: Optional[str] = Field(default=None, max_length=200)


class AssignmentV0_6(BaseModel):
    """
    v0.6 assignment adds:
      - commit_state: anti-oscillation commit window / cooldown signals
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_coach_assignment"] = "sg_coach_assignment"
    schema_version: Literal["v0_6"] = "v0_6"

    created_at_utc: datetime = Field(default_factory=utc_now)

    session_id: str = Field(min_length=1, max_length=128)
    instrument_id: str = Field(min_length=1, max_length=128)

    target_tempo_bpm: int = Field(ge=20, le=300)
    tempo_nudge_bpm: int = Field(ge=-20, le=20)
    density_cap: float = Field(ge=0.0, le=1.0)

    duration_seconds: int = Field(ge=10, le=3600)

    allow_probe: bool = False
    probe_reason: Optional[str] = Field(default=None, max_length=200)

    # v0.5 structured explainability
    reasons: List[OverrideReason] = Field(default_factory=list)
    overrides: List[OverrideDecisionV0] = Field(default_factory=list)

    # NEW v0.6: commit window / cooldown signals
    commit_state: CommitStateV0 = Field(default_factory=CommitStateV0)

    feedback: CoachFeedbackV0_5


__all__ = [
    "CommitMode",
    "CommitStateV0",
    "AssignmentV0_6",
]
