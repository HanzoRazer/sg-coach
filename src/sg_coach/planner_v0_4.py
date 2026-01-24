"""
v0.4 Planner: consumes control_intent + flags, produces Assignment.

Goals:
  1) Use Groove Layer intent when safe.
  2) Apply deterministic overrides when flags indicate instability/drift/overplay.
  3) Never allow probe when instability or drift is present.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# v0.4 Models
# ============================================================================


class CoachFeedbackCompat(BaseModel):
    """v0.4 feedback model for Assignment (compatible with v0.1 shape)."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    severity: Literal["info", "warn", "block"] = "info"
    hints: List[str] = Field(default_factory=list)


class AssignmentV0_4(BaseModel):
    """
    v0.4 Assignment: output of planner consuming control_intent + flags.

    This is a simplified assignment format for SG-only use.
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["sg_coach_assignment"] = "sg_coach_assignment"
    schema_version: Literal["v0"] = "v0"

    created_at_utc: datetime = Field(default_factory=utc_now)

    session_id: str = Field(min_length=1, max_length=128)
    instrument_id: str = Field(min_length=1, max_length=128)

    target_tempo_bpm: int = Field(ge=20, le=300)
    tempo_nudge_bpm: int = Field(ge=-20, le=20)
    density_cap: float = Field(ge=0.0, le=1.0)
    duration_seconds: int = Field(ge=30, le=3600)

    allow_probe: bool = False
    probe_reason: Optional[str] = Field(default=None, max_length=200)

    feedback: CoachFeedbackCompat


# ============================================================================
# Policy Configuration
# ============================================================================


@dataclass(frozen=True)
class PlannerPolicyV0_4:
    """
    v0.4: Planner consumes:
      - control_intent (preferred baseline knobs)
      - flags (safety overrides)

    Goals:
      1) Use Groove Layer intent when safe.
      2) Apply deterministic overrides when flags indicate instability/drift/overplay.
      3) Never allow probe when instability or drift is present.
    """

    # Assignment defaults
    duration_seconds: int = 8 * 60  # 480 seconds

    # Override knobs (recovery)
    recovery_density_cap: float = 0.55
    recovery_down_nudge_bpm: int = -4

    # Drift override
    drift_down_nudge_bpm: int = -2

    # Overplay override
    overplay_density_cap: float = 0.60

    # Cap changes
    max_abs_tempo_nudge: int = 8


DEFAULT_POLICY_V0_4 = PlannerPolicyV0_4()


# ============================================================================
# Planner Implementation
# ============================================================================


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _map_feedback(feedback: CoachFeedbackV0) -> CoachFeedbackCompat:
    """Map v0.3 feedback into v0.4 feedback model used by Assignment."""
    return CoachFeedbackCompat(
        message=feedback.message,
        severity=feedback.severity,
        hints=list(feedback.hints),
    )


def _augment_feedback(
    feedback: CoachFeedbackV0, severity: str, extra_sentence: str
) -> CoachFeedbackV0:
    """
    Deterministic augmentation:
      - escalate severity if needed
      - append a sentence once
    """
    sev_rank = {"info": 0, "warn": 1, "block": 2}
    cur = feedback.severity
    new_sev = cur
    if sev_rank.get(severity, 0) > sev_rank.get(cur, 0):
        new_sev = severity  # type: ignore[assignment]

    msg = feedback.message
    if extra_sentence not in msg:
        msg = f"{msg} {extra_sentence}".strip()

    return CoachFeedbackV0(
        severity=new_sev,  # type: ignore[arg-type]
        message=msg,
        hints=list(feedback.hints),
    )


def plan_next_v0_4(
    e: EvaluationV0_3,
    feedback: CoachFeedbackV0,
    policy: PlannerPolicyV0_4 = DEFAULT_POLICY_V0_4,
) -> AssignmentV0_4:
    """
    Produces a v0.4-style Assignment using:
      - control_intent (baseline)
      - flags (override)
      - feedback (copied through; may be augmented deterministically)
    """

    flags = e.flags or {}
    intent = e.control_intent

    # --- baseline knobs (prefer intent if present) ---
    target_tempo_bpm = int(round(e.groove.tempo_bpm_est))
    tempo_nudge_bpm = 0
    density_cap = 0.70
    allow_probe = False
    probe_reason: Optional[str] = None

    if intent is not None:
        target_tempo_bpm = intent.target_tempo_bpm
        tempo_nudge_bpm = intent.tempo_nudge_bpm
        density_cap = intent.density_cap
        allow_probe = bool(intent.allow_probe)
        probe_reason = intent.probe_reason

    # --- safety overrides driven by flags ---
    # Priority order: instability_block > instability > tempo_drift > overplaying
    # Instability always disables probe.
    if flags.get("instability_block", False):
        allow_probe = False
        probe_reason = None
        tempo_nudge_bpm = min(tempo_nudge_bpm, policy.recovery_down_nudge_bpm)
        density_cap = min(density_cap, policy.recovery_density_cap)
        feedback = _augment_feedback(
            feedback, "block", "Recovery mode: stabilize timing before progressing."
        )
    elif flags.get("instability", False):
        allow_probe = False
        probe_reason = None
        tempo_nudge_bpm = min(tempo_nudge_bpm, -1)
        density_cap = min(density_cap, policy.recovery_density_cap)
        feedback = _augment_feedback(
            feedback, "warn", "Recovery mode: simplify rhythm and reduce tempo slightly."
        )
    else:
        # No instability → probe may still be disabled by drift/overplay
        pass

    # Always check drift and overplay (even with instability)
    if flags.get("tempo_drift", False):
        allow_probe = False
        probe_reason = None
        tempo_nudge_bpm = min(tempo_nudge_bpm, policy.drift_down_nudge_bpm)
        feedback = _augment_feedback(
            feedback, "warn", "Tempo drift override: re-center time before probing."
        )

    if flags.get("overplaying", False):
        allow_probe = False
        probe_reason = None
        density_cap = min(density_cap, policy.overplay_density_cap)
        feedback = _augment_feedback(
            feedback, "warn", "Density override: leave space to improve control."
        )

    # Clamp nudge and density
    tempo_nudge_bpm = _clamp_int(
        tempo_nudge_bpm, -policy.max_abs_tempo_nudge, policy.max_abs_tempo_nudge
    )
    density_cap = max(0.0, min(1.0, float(density_cap)))

    return AssignmentV0_4(
        session_id=e.session_id,
        instrument_id=e.instrument_id,
        target_tempo_bpm=target_tempo_bpm,
        tempo_nudge_bpm=tempo_nudge_bpm,
        density_cap=density_cap,
        duration_seconds=policy.duration_seconds,
        allow_probe=allow_probe,
        probe_reason=probe_reason,
        feedback=_map_feedback(feedback),
    )


__all__ = [
    "AssignmentV0_4",
    "CoachFeedbackCompat",
    "PlannerPolicyV0_4",
    "DEFAULT_POLICY_V0_4",
    "plan_next_v0_4",
]
