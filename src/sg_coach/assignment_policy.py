"""
Deterministic Mode-1 assignment planner.

Converts measured session facts + CoachEvaluation into a concrete next practice plan.
No LLM. No MIDI generation. Pure policy logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from .schemas import (
    AssignmentConstraints,
    AssignmentFocus,
    CoachEvaluation,
    PracticeAssignment,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SuccessCriteria,
)


@dataclass(frozen=True)
class AssignmentPolicyConfig:
    """
    Tunable knobs for assignment planning.
    Frozen dataclass ensures immutability.
    """

    # Tempo ramp defaults
    tempo_step_bpm: int = 5
    tempo_floor_bpm: int = 50
    tempo_ceiling_bpm: int = 220

    # Looping defaults
    default_bars_per_loop: int = 2
    default_repetitions: int = 8

    # Strict window suggestion bounds
    strict_window_min_ms: int = 15
    strict_window_max_ms: int = 60

    # Success criteria defaults
    success_mean_error_ms_good: float = 15.0
    success_mean_error_ms_ok: float = 20.0
    success_mean_error_ms_easy: float = 25.0

    # Late-drop tolerances (ornaments only)
    max_late_drops_good: int = 1
    max_late_drops_ok: int = 3
    max_late_drops_easy: int = 6

    # If session was short, keep assignment shorter as well
    short_session_s: int = 180
    short_session_reps: int = 6


DEFAULT_ASSIGNMENT_POLICY = AssignmentPolicyConfig()


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _round_int(x: float) -> int:
    return int(round(float(x)))


def _suggest_strict_window_ms(mean_err_ms: float, cfg: AssignmentPolicyConfig) -> int:
    """
    Deterministic window suggestion:
    - start near mean error + small buffer
    - clamp to safe bounds
    """
    # +6ms buffer keeps "strict" usable while still demanding improvement
    raw = _round_int(mean_err_ms + 6.0)
    return _clamp_int(raw, cfg.strict_window_min_ms, cfg.strict_window_max_ms)


def _tempo_plan(session_bpm: float, cfg: AssignmentPolicyConfig) -> tuple[int, int, int]:
    """
    Deterministic tempo plan:
    - start: drop to a controllable tempo for skill work (unless already low)
    - target: approach session tempo (not exceed)
    - step: fixed
    """
    bpm = float(session_bpm)
    # Start at session bpm - 20, but never below floor; for slow sessions, keep close.
    start = _clamp_int(_round_int(bpm - 20.0), cfg.tempo_floor_bpm, cfg.tempo_ceiling_bpm)
    target = _clamp_int(_round_int(bpm), cfg.tempo_floor_bpm, cfg.tempo_ceiling_bpm)
    step = cfg.tempo_step_bpm
    # If start == target, still return a valid ramp (planner/UI can treat as "steady")
    return start, target, step


def _success_thresholds(mean_err_ms: float, cfg: AssignmentPolicyConfig) -> tuple[float, int]:
    """
    Deterministic criteria based on current performance:
    - Better sessions get tighter goals
    - Struggling sessions get reachable goals
    """
    m = float(mean_err_ms)
    if m <= cfg.success_mean_error_ms_good:
        return cfg.success_mean_error_ms_good, cfg.max_late_drops_good
    if m <= cfg.success_mean_error_ms_ok:
        return cfg.success_mean_error_ms_ok, cfg.max_late_drops_ok
    return cfg.success_mean_error_ms_easy, cfg.max_late_drops_easy


def plan_assignment(
    *,
    session: SessionRecord,
    evaluation: CoachEvaluation,
    cfg: AssignmentPolicyConfig = DEFAULT_ASSIGNMENT_POLICY,
    assignment_id: Optional[UUID] = None,
) -> PracticeAssignment:
    """
    Deterministic Mode-1 planner: SessionRecord + CoachEvaluation -> PracticeAssignment.

    - references an existing program/exercise (never invents new theory)
    - sets tempo ramp + strict window suggestion
    - sets loop size + reps
    - sets success criteria
    """
    perf = session.performance
    timing = session.timing

    mean_err = float(perf.timing_error_ms.mean)

    tempo_start, tempo_target, tempo_step = _tempo_plan(timing.bpm, cfg)
    strict_window = _suggest_strict_window_ms(mean_err, cfg)

    # reps: scale down for short sessions, otherwise default
    reps = cfg.default_repetitions
    if session.duration_s <= cfg.short_session_s:
        reps = cfg.short_session_reps

    # success criteria: based on current level (reachable next step)
    max_mean_err, max_late_drops = _success_thresholds(mean_err, cfg)

    # focus: taken from evaluation (schema-safe)
    focus = AssignmentFocus(
        primary=evaluation.focus_recommendation.concept,
        secondary=None,
    )

    # program reference: prefer session program; keep the hash if present
    program = ProgramRef(
        type=session.program_ref.type if session.program_ref.type in (ProgramType.ztprog, ProgramType.ztex) else ProgramType.ztprog,
        name=session.program_ref.name,
        hash=session.program_ref.hash,
    )

    # strict is enabled if the session was strict OR the coach focus is alignment-based
    want_strict = bool(timing.strict) or evaluation.focus_recommendation.concept in ("grid_alignment", "clave_alignment")

    # bars_per_loop: stable and small by default; can be expanded later
    bars_per_loop = cfg.default_bars_per_loop

    # assignment_id: caller can provide stable ID, otherwise generate UUID4
    aid = assignment_id if assignment_id is not None else uuid4()

    # coach_prompt: still deterministic (LLM can rephrase later in Mode 2)
    prompt_msg = f"Focus: {evaluation.focus_recommendation.concept}. {evaluation.focus_recommendation.reason}"

    return PracticeAssignment(
        assignment_id=aid,
        session_id=session.session_id,
        program=program,
        constraints=AssignmentConstraints(
            tempo_start=tempo_start,
            tempo_target=tempo_target,
            tempo_step=tempo_step,
            strict=want_strict,
            strict_window_ms=strict_window if want_strict else None,
            bars_per_loop=bars_per_loop,
            repetitions=reps,
        ),
        focus=focus,
        success_criteria=SuccessCriteria(
            max_mean_error_ms=max_mean_err,
            max_late_drops=max_late_drops,
        ),
        coach_prompt={"mode": "optional", "message": prompt_msg},
        expires_after_sessions=3,
    )
