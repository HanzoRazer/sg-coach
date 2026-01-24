"""
Assignment Policy v1: CoachEvaluation -> PracticeAssignment.

Pure function that takes a coach evaluation and produces a practice assignment.
No model calls; uses rule-based tempo adjustment and focus derivation.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .schemas import (
    AssignmentConstraints,
    AssignmentFocus,
    CoachEvaluation,
    CoachPrompt,
    PracticeAssignment,
    ProgramRef,
    ProgramType,
    SuccessCriteria,
)


@dataclass(frozen=True)
class AssignmentPolicyConfig:
    """Assignment policy configuration."""
    tempo_start_default: int = 80
    tempo_step: int = 5
    tempo_floor: int = 40
    tempo_ceiling: int = 200
    bars_per_loop: int = 4
    repetitions: int = 8
    max_mean_error_ms: float = 30.0
    max_late_drops: int = 3


def plan_assignment(
    evaluation: CoachEvaluation,
    program: ProgramRef,
    *,
    previous_tempo: int | None = None,
    config: AssignmentPolicyConfig = AssignmentPolicyConfig(),
) -> PracticeAssignment:
    """
    Create assignment from evaluation using rule-based logic.

    Tempo planning:
    - If evaluation has no primary findings -> increase tempo
    - If evaluation has primary findings -> hold or reduce tempo
    - previous_tempo allows tempo continuity across sessions
    """
    # Determine base tempo
    if previous_tempo is not None:
        base = previous_tempo
    else:
        base = config.tempo_start_default

    # Tempo adjustment based on evaluation
    has_primary = any(f.severity.value == "primary" for f in evaluation.findings)
    has_secondary = any(f.severity.value == "secondary" for f in evaluation.findings)

    if has_primary:
        # Reduce tempo
        tempo_start = max(config.tempo_floor, base - config.tempo_step)
        tempo_target = tempo_start  # stay at reduced tempo
        prompt_mode = "required"
        prompt_msg = "Focus on accuracy before increasing tempo."
    elif has_secondary:
        # Hold tempo
        tempo_start = base
        tempo_target = base
        prompt_mode = "optional"
        prompt_msg = "Minor issues detected; refine technique at current tempo."
    else:
        # Increase tempo
        tempo_start = base
        tempo_target = min(config.tempo_ceiling, base + config.tempo_step)
        prompt_mode = "optional"
        prompt_msg = "Great work! Try pushing the tempo."

    # Build focus from evaluation
    focus = evaluation.focus_recommendation
    assignment_focus = AssignmentFocus(
        primary=focus.concept,
        secondary=None,
    )

    # Constraints
    constraints = AssignmentConstraints(
        tempo_start=tempo_start,
        tempo_target=tempo_target,
        tempo_step=config.tempo_step,
        strict=True,
        strict_window_ms=35,
        bars_per_loop=config.bars_per_loop,
        repetitions=config.repetitions,
    )

    # Success criteria
    success = SuccessCriteria(
        max_mean_error_ms=config.max_mean_error_ms,
        max_late_drops=config.max_late_drops,
    )

    # Coach prompt
    prompt = CoachPrompt(
        mode=prompt_mode,
        message=prompt_msg,
    )

    return PracticeAssignment(
        assignment_id=uuid4(),
        session_id=evaluation.session_id,
        program=program,
        constraints=constraints,
        focus=assignment_focus,
        success_criteria=success,
        coach_prompt=prompt,
        expires_after_sessions=3,
    )


__all__ = ["plan_assignment", "AssignmentPolicyConfig"]
