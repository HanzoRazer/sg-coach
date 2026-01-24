"""
Groove-Aware Evaluation Models (v0.3)

Includes GrooveSnapshot + optional ControlIntent as inputs/observations,
and produces flags + scores used by the planner.

NOTE: SG-only; never crosses ToolBox boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from .groove_contracts import ControlIntentV0, GrooveSnapshotV0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CoachFeedbackV0(BaseModel):
    """
    v0.3 feedback stub:
    Deterministic, rules-based guidance (no LLM dependency).
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_coach_feedback"] = "sg_coach_feedback"
    schema_version: Literal["v0"] = "v0"

    created_at_utc: datetime = Field(default_factory=utc_now)

    severity: Literal["info", "warn", "block"] = "info"
    message: str = Field(min_length=1, max_length=800)
    hints: List[str] = Field(default_factory=list)


class EvaluationV0_3(BaseModel):
    """
    v0.3 evaluation:
    includes GrooveSnapshot + optional ControlIntent as inputs/observations,
    and produces flags + scores used by the planner.

    NOTE: SG-only; never crosses ToolBox boundary.
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_coach_evaluation"] = "sg_coach_evaluation"
    schema_version: Literal["v0_3"] = "v0_3"

    evaluated_at_utc: datetime = Field(default_factory=utc_now)

    session_id: str = Field(min_length=1, max_length=128)
    instrument_id: str = Field(min_length=1, max_length=128)

    groove: GrooveSnapshotV0
    control_intent: ControlIntentV0 | None = None

    timing_score: float = Field(ge=0.0, le=1.0)
    consistency_score: float = Field(ge=0.0, le=1.0)

    flags: Dict[str, bool] = Field(default_factory=dict)


__all__ = ["CoachFeedbackV0", "EvaluationV0_3", "utc_now"]
