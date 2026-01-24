"""
v0.6 Planner: history-aware + anti-oscillation.

Key features:
- Detects flip-flop in tempo_nudge / density_cap
- Enforces commit window ("hold steady for N cycles")
- Cooldown after safety overrides (probe forbidden briefly)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .assignment_v0_5 import OverrideDecisionV0, OverrideReason, CoachFeedbackV0_5
from .assignment_v0_6 import AssignmentV0_6, CommitMode, CommitStateV0
from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3


@dataclass(frozen=True)
class PlannerPolicyV0_6:
    """
    History + anti-oscillation policy:

    - lookback_n: how many recent assignments to consider
    - flipflop_threshold: if knobs toggle direction this many times, enter commit window
    - commit_cycles: how long to hold steady after detecting oscillation
    - probe_cooldown_cycles: after any instability/drift override, forbid probing briefly
    """

    duration_seconds: int = 8 * 60  # 480 seconds

    lookback_n: int = 6
    flipflop_threshold: int = 2

    commit_cycles: int = 3
    probe_cooldown_cycles: int = 2

    # knob bounds
    max_abs_tempo_nudge: int = 8

    # conservative recovery caps
    recovery_density_cap: float = 0.55
    overplay_density_cap: float = 0.60


DEFAULT_POLICY_V0_6 = PlannerPolicyV0_6()


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _map_feedback(feedback: CoachFeedbackV0) -> CoachFeedbackV0_5:
    """Map v0.3 feedback to v0.5 format (unchanged, no mutation)."""
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


def _extract_knobs_from_assignment(a) -> Tuple[int, float, bool]:
    """Extract knobs from assignment (duck typed for v0.5/v0.6 compat)."""
    # Handle both Pydantic models and dicts
    if isinstance(a, dict):
        return int(a["tempo_nudge_bpm"]), float(a["density_cap"]), bool(a.get("allow_probe", False))
    return int(a.tempo_nudge_bpm), float(a.density_cap), bool(a.allow_probe)


def _sign(x: float) -> int:
    """Return sign of x: +1, -1, or 0."""
    if x > 1e-9:
        return 1
    if x < -1e-9:
        return -1
    return 0


def _count_flipflops(seq: List[int]) -> int:
    """
    Count sign changes ignoring zeros.
    Example: [1, 1, -1, -1, 1] => 2 flipflops.
    """
    nonzero = [s for s in seq if s != 0]
    if len(nonzero) < 2:
        return 0
    flips = 0
    last = nonzero[0]
    for s in nonzero[1:]:
        if s != last:
            flips += 1
            last = s
    return flips


def _detect_oscillation(
    history_assignments: List,
    lookback_n: int,
    flipflop_threshold: int,
) -> bool:
    """Detect if recent assignments show flip-flop pattern."""
    if not history_assignments:
        return False
    tail = history_assignments[-lookback_n:]
    tempo_series = [_sign(_extract_knobs_from_assignment(a)[0]) for a in tail]
    # Density oscillation relative to a midline (0.65)
    dens_series = [_sign(_extract_knobs_from_assignment(a)[1] - 0.65) for a in tail]

    tempo_flips = _count_flipflops(tempo_series)
    dens_flips = _count_flipflops(dens_series)

    return (tempo_flips >= flipflop_threshold) or (dens_flips >= flipflop_threshold)


def plan_next_v0_6(
    e: EvaluationV0_3,
    feedback: CoachFeedbackV0,
    history_assignments: Optional[List] = None,
    history_evaluations: Optional[List[EvaluationV0_3]] = None,
    prior_commit_state: Optional[CommitStateV0] = None,
    policy: PlannerPolicyV0_6 = DEFAULT_POLICY_V0_6,
) -> AssignmentV0_6:
    """
    v0.6 planner:
      - Start from Groove control_intent baseline
      - Apply safety overrides from flags
      - Apply anti-oscillation commit window if flip-flop detected
      - Emit commit_state so runtime can persist it

    Notes:
      - history_assignments can be AssignmentV0_5 or V0_6 (duck typed).
      - prior_commit_state is carried from last assignment (or session store).
    """
    history_assignments = history_assignments or []
    history_evaluations = history_evaluations or []
    flags = e.flags or {}
    intent = e.control_intent

    overrides: List[OverrideDecisionV0] = []
    reasons: List[OverrideReason] = []

    # baseline knobs
    target_tempo_bpm = int(round(e.groove.tempo_bpm_est))
    tempo_nudge_bpm = 0
    density_cap = 0.70
    allow_probe = False
    probe_reason: Optional[str] = None

    if intent is not None:
        target_tempo_bpm = int(intent.target_tempo_bpm)
        tempo_nudge_bpm = int(intent.tempo_nudge_bpm)
        density_cap = float(intent.density_cap)
        allow_probe = bool(intent.allow_probe)
        probe_reason = intent.probe_reason

    # carry commit state
    commit = prior_commit_state or CommitStateV0()

    # decrement existing commit window
    if commit.mode != CommitMode.none and commit.cycles_remaining > 0:
        new_remaining = commit.cycles_remaining - 1
        if new_remaining == 0:
            commit = CommitStateV0()  # reset
        else:
            commit = CommitStateV0(
                mode=commit.mode,
                cycles_remaining=new_remaining,
                note=commit.note,
            )

    # Safety overrides (probe veto)
    probe_vetoed = False

    if flags.get("instability_block", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.instability_block
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.instability_block
        )
        new_nudge = min(tempo_nudge_bpm, -3)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.instability_block
        )
        new_density = min(density_cap, policy.recovery_density_cap)
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, new_density, OverrideReason.instability_block
        )
        probe_vetoed = True

    if flags.get("instability", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.instability
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.instability
        )
        new_nudge = min(tempo_nudge_bpm, -1)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.instability
        )
        new_density = min(density_cap, policy.recovery_density_cap)
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, new_density, OverrideReason.instability
        )
        probe_vetoed = True

    if flags.get("tempo_drift", False):
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.tempo_drift
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.tempo_drift
        )
        new_nudge = min(tempo_nudge_bpm, -2)
        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, new_nudge, OverrideReason.tempo_drift
        )
        probe_vetoed = True

    if flags.get("overplaying", False):
        # Record reason even if values don't change
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
        probe_vetoed = True

    if flags.get("low_confidence", False) and OverrideReason.low_confidence not in reasons:
        reasons.append(OverrideReason.low_confidence)
    if flags.get("inconsistent_dynamics", False) and OverrideReason.inconsistent_dynamics not in reasons:
        reasons.append(OverrideReason.inconsistent_dynamics)

    # Clamp tempo nudge
    tempo_nudge_bpm = _clamp_int(tempo_nudge_bpm, -policy.max_abs_tempo_nudge, policy.max_abs_tempo_nudge)
    density_cap = max(0.0, min(1.0, float(density_cap)))

    # Apply probe cooldown if we vetoed probe due to safety reasons
    if probe_vetoed and commit.mode == CommitMode.none:
        commit = CommitStateV0(
            mode=CommitMode.cooldown,
            cycles_remaining=policy.probe_cooldown_cycles,
            note="probe cooldown after safety veto",
        )

    # Anti-oscillation: if oscillation detected and we're not already in a commit/cooldown state
    oscillation = _detect_oscillation(
        history_assignments,
        policy.lookback_n,
        policy.flipflop_threshold,
    )
    if oscillation and commit.mode == CommitMode.none:
        commit = CommitStateV0(
            mode=CommitMode.hold,
            cycles_remaining=policy.commit_cycles,
            note="oscillation commit window",
        )

    # Commit behavior
    if commit.mode == CommitMode.hold and history_assignments:
        # Hold last assignment knobs steady
        last = history_assignments[-1]
        last_tempo_nudge, last_density_cap, _ = _extract_knobs_from_assignment(last)

        tempo_nudge_bpm = _apply_override(
            overrides, reasons, "tempo_nudge_bpm", tempo_nudge_bpm, int(last_tempo_nudge), OverrideReason.low_confidence
        )
        density_cap = _apply_override(
            overrides, reasons, "density_cap", density_cap, float(last_density_cap), OverrideReason.low_confidence
        )

        # During hold: do not probe
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.low_confidence
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.low_confidence
        )

    if commit.mode == CommitMode.cooldown and commit.cycles_remaining > 0:
        # Cooldown: probing forbidden
        allow_probe = _apply_override(
            overrides, reasons, "allow_probe", allow_probe, False, OverrideReason.low_confidence
        )
        probe_reason = _apply_override(
            overrides, reasons, "probe_reason", probe_reason, None, OverrideReason.low_confidence
        )

    return AssignmentV0_6(
        session_id=e.session_id,
        instrument_id=e.instrument_id,
        target_tempo_bpm=target_tempo_bpm,
        tempo_nudge_bpm=int(tempo_nudge_bpm),
        density_cap=float(density_cap),
        duration_seconds=policy.duration_seconds,
        allow_probe=bool(allow_probe),
        probe_reason=probe_reason,
        reasons=reasons,
        overrides=overrides,
        commit_state=commit,
        feedback=_map_feedback(feedback),
    )


__all__ = [
    "PlannerPolicyV0_6",
    "DEFAULT_POLICY_V0_6",
    "plan_next_v0_6",
]
