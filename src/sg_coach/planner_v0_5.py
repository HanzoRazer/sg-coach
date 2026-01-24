"""
v0.5 Planner: structured overrides + reasons.

Key differences from v0.4:
  - Does NOT mutate feedback text
  - Emits machine-readable reasons[] and overrides[]
  - Full audit trail for UI + analytics
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .assignment_v0_5 import (
    AssignmentV0_5,
    CoachFeedbackV0_5,
    OverrideDecisionV0,
    OverrideReason,
)
from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3


@dataclass(frozen=True)
class PlannerPolicyV0_5:
    """v0.5 planner policy configuration."""

    duration_seconds: int = 8 * 60  # 480 seconds

    # recovery knobs
    recovery_density_cap: float = 0.55
    recovery_down_nudge_bpm: int = -4

    # drift knobs
    drift_down_nudge_bpm: int = -2

    # overplay knobs
    overplay_density_cap: float = 0.60

    # clamp
    max_abs_tempo_nudge: int = 8


DEFAULT_POLICY_V0_5 = PlannerPolicyV0_5()


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _map_feedback(feedback: CoachFeedbackV0) -> CoachFeedbackV0_5:
    """Map v0.3 feedback to v0.5 (unchanged, no mutation)."""
    return CoachFeedbackV0_5(
        message=feedback.message,
        severity=feedback.severity,
        hints=list(feedback.hints),
    )


def _as_s(val) -> str:
    """Convert value to string for override record."""
    if val is None:
        return "None"
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, float):
        return f"{val:.2f}".rstrip("0").rstrip(".")
    return str(val)


def _apply_override(
    overrides: List[OverrideDecisionV0],
    reasons: List[OverrideReason],
    field: str,
    old,
    new,
    reason: OverrideReason,
):
    """Record an override if old != new, return new value."""
    if old == new:
        return old
    overrides.append(
        OverrideDecisionV0(
            field=field,
            from_value=_as_s(old),
            to_value=_as_s(new),
            reason=reason,
        )
    )
    if reason not in reasons:
        reasons.append(reason)
    return new


def plan_next_v0_5(
    e: EvaluationV0_3,
    feedback: CoachFeedbackV0,
    policy: PlannerPolicyV0_5 = DEFAULT_POLICY_V0_5,
) -> AssignmentV0_5:
    """
    v0.5 planner:
      - consumes control_intent as baseline
      - applies flag-based safety overrides
      - emits structured reasons + override decisions
      - does NOT mutate feedback text
    """

    flags = e.flags or {}
    intent = e.control_intent

    overrides: List[OverrideDecisionV0] = []
    reasons: List[OverrideReason] = []

    # baseline (prefer intent)
    target_tempo_bpm = int(round(e.groove.tempo_bpm_est))
    tempo_nudge_bpm = 0
    density_cap = 0.70
    allow_probe = False
    probe_reason: Optional[str] = None

    if intent is not None:
        target_tempo_bpm = intent.target_tempo_bpm
        tempo_nudge_bpm = intent.tempo_nudge_bpm
        density_cap = float(intent.density_cap)
        allow_probe = bool(intent.allow_probe)
        probe_reason = intent.probe_reason

    # --- overrides (priority) ---
    # Instability disables probe and forces recovery constraints
    if flags.get("instability_block", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.instability_block
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason or "intent", None, OverrideReason.instability_block
        )
        new_nudge = min(tempo_nudge_bpm, policy.recovery_down_nudge_bpm)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.instability_block
        )
        new_density = min(density_cap, policy.recovery_density_cap)
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, new_density, OverrideReason.instability_block
        )

    elif flags.get("instability", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.instability
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason or "intent", None, OverrideReason.instability
        )
        new_nudge = min(tempo_nudge_bpm, -1)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.instability
        )
        new_density = min(density_cap, policy.recovery_density_cap)
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, new_density, OverrideReason.instability
        )

    # Drift and overplay also disable probing (even if stability OK)
    if flags.get("tempo_drift", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.tempo_drift
        )
        if probe_reason is not None:
            probe_reason = _apply_override(
                overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.tempo_drift
            )
        new_nudge = min(tempo_nudge_bpm, policy.drift_down_nudge_bpm)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.tempo_drift
        )

    if flags.get("overplaying", False):
        # Record reason even if values don't change further
        if OverrideReason.overplaying not in reasons:
            reasons.append(OverrideReason.overplaying)
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.overplaying
        )
        if probe_reason is not None:
            probe_reason = _apply_override(
                overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.overplaying
            )
        new_density = min(density_cap, policy.overplay_density_cap)
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, new_density, OverrideReason.overplaying
        )

    # Additional "soft" reasons (no knob change yet, but we still record why)
    if flags.get("low_confidence", False) and OverrideReason.low_confidence not in reasons:
        reasons.append(OverrideReason.low_confidence)
    if flags.get("inconsistent_dynamics", False) and OverrideReason.inconsistent_dynamics not in reasons:
        reasons.append(OverrideReason.inconsistent_dynamics)

    # Clamp values
    tempo_nudge_clamped = _clamp_int(tempo_nudge_bpm, -policy.max_abs_tempo_nudge, policy.max_abs_tempo_nudge)
    if tempo_nudge_clamped != tempo_nudge_bpm:
        tempo_nudge_bpm = tempo_nudge_clamped

    density_cap = max(0.0, min(1.0, float(density_cap)))

    return AssignmentV0_5(
        session_id=e.session_id,
        instrument_id=e.instrument_id,
        target_tempo_bpm=int(target_tempo_bpm),
        tempo_nudge_bpm=int(tempo_nudge_bpm),
        density_cap=float(density_cap),
        duration_seconds=policy.duration_seconds,
        allow_probe=bool(allow_probe),
        probe_reason=probe_reason,
        reasons=reasons,
        overrides=overrides,
        feedback=_map_feedback(feedback),
    )


__all__ = [
    "PlannerPolicyV0_5",
    "DEFAULT_POLICY_V0_5",
    "plan_next_v0_5",
]
