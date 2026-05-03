"""
Diminished Orbit Evaluator

Evaluates performed notes against a key's diminished orbit.
Emits DIM_ORBIT_VIOLATION findings when notes fall outside the orbit.

This module is the coach interpretation layer for diminished navigation.
It does not generate MIDI or mutate assignments — it only evaluates.

Architecture:
    diminished.py       = theory truth (in zone_tritone)
    corpus pack         = curriculum truth
    this module         = learner-facing interpretation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from shared.zone_tritone import (
    is_in_dim_orbit,
    get_dim_set_for_key,
    pc_from_name,
    name_from_pc,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

from .schemas import (
    CoachFinding,
    FindingEvidence,
    Severity,
    FeedbackDomain,
    FeedbackRenderHint,
    FeedbackActionType,
    SuggestedAction,
)


@dataclass
class DimOrbitContext:
    """Context for diminished orbit evaluation."""
    key: str
    dim_notes: tuple[str, ...]
    resolution_map: Optional[dict[str, str]] = None


@dataclass
class DimOrbitViolation:
    """A single violation of diminished orbit rules."""
    note: str
    pitch_class: int
    position: Optional[int] = None


@dataclass
class DimOrbitEvaluation:
    """Result of evaluating notes against a diminished orbit."""
    key: str
    dim_notes: tuple[str, ...]
    notes_evaluated: int
    notes_in_orbit: int
    violations: list[DimOrbitViolation]
    diagnosis_code: Optional[DiagnosisCode] = None
    message: Optional[str] = None
    suggestion: Optional[str] = None

    @property
    def is_clean(self) -> bool:
        """True if no violations were found."""
        return len(self.violations) == 0

    def to_coach_finding(self) -> Optional[CoachFinding]:
        """Convert to CoachFinding if there's a violation."""
        if self.is_clean:
            return None

        violation_notes = [v.note for v in self.violations]
        message = self.message or render_violation_message(
            DimOrbitContext(key=self.key, dim_notes=self.dim_notes),
            self.violations,
        )

        return CoachFinding(
            # Legacy fields (backward compatibility)
            type="harmony",
            severity=Severity.secondary,
            interpretation=message,
            # Governance fields (Phase 5.3)
            code=DiagnosisCode.DIM_ORBIT_VIOLATION,
            domain=FeedbackDomain.harmony,
            title="Diminished orbit violation",
            message=message,
            evidence=FindingEvidence(
                metric="dim_orbit_violations",
                value=float(len(self.violations)),
                key=self.key,
                expected_set=list(self.dim_notes),
                performed_set=violation_notes,
                aggregate_stats={
                    "notes_evaluated": self.notes_evaluated,
                    "notes_in_orbit": self.notes_in_orbit,
                    "violation_count": len(self.violations),
                },
            ),
            render_hint=FeedbackRenderHint.summary,
            suggested_actions=[
                SuggestedAction(
                    action_type=FeedbackActionType.isolate,
                    label="Isolate problem notes",
                    rationale="Practice the specific notes that fell outside the orbit",
                ),
                SuggestedAction(
                    action_type=FeedbackActionType.review_reference,
                    label="Review diminished orbit",
                    rationale=f"In key of {self.key}, the orbit is: {', '.join(self.dim_notes)}",
                ),
                SuggestedAction(
                    action_type=FeedbackActionType.assign_drill,
                    label="Orbit awareness drill",
                    rationale="Practice chromatic approach patterns using orbit notes",
                ),
            ],
            confidence=1.0,
            source_evaluator="diminished_evaluator",
        )


def build_context(key: str, resolution_map: Optional[dict[str, str]] = None) -> DimOrbitContext:
    """
    Build evaluation context for a key.

    Parameters
    ----------
    key:
        Key name (e.g., 'C', 'G', 'F#') or pitch class.
    resolution_map:
        Optional map of dim notes to their resolution targets.

    Returns
    -------
    Context object with key, dim_notes, and resolution_map.
    """
    if isinstance(key, int):
        key = name_from_pc(key)

    dim_pcs = get_dim_set_for_key(key)
    dim_notes = tuple(name_from_pc(pc) for pc in dim_pcs)

    return DimOrbitContext(
        key=key,
        dim_notes=dim_notes,
        resolution_map=resolution_map,
    )


def evaluate_notes(
    context: DimOrbitContext,
    performed_notes: Sequence[str | int],
) -> DimOrbitEvaluation:
    """
    Evaluate performed notes against the diminished orbit.

    Parameters
    ----------
    context:
        Evaluation context from build_context().
    performed_notes:
        Sequence of note names or pitch classes that were performed.

    Returns
    -------
    Evaluation result with violations and rendered message.
    """
    violations: list[DimOrbitViolation] = []
    notes_in_orbit = 0

    for i, note in enumerate(performed_notes):
        if isinstance(note, str):
            try:
                pc = pc_from_name(note)
            except ValueError:
                continue
            note_name = note
        else:
            pc = note % 12
            note_name = name_from_pc(pc)

        if is_in_dim_orbit(pc, context.key):
            notes_in_orbit += 1
        else:
            violations.append(DimOrbitViolation(
                note=note_name,
                pitch_class=pc,
                position=i,
            ))

    diagnosis_code = None
    message = None
    suggestion = None

    if violations:
        diagnosis_code = DiagnosisCode.DIM_ORBIT_VIOLATION
        message = render_violation_message(context, violations)
        suggestion = render_suggestion(context)

    return DimOrbitEvaluation(
        key=context.key,
        dim_notes=context.dim_notes,
        notes_evaluated=len(performed_notes),
        notes_in_orbit=notes_in_orbit,
        violations=violations,
        diagnosis_code=diagnosis_code,
        message=message,
        suggestion=suggestion,
    )


def render_violation_message(
    context: DimOrbitContext,
    violations: list[DimOrbitViolation],
) -> str:
    """
    Render the coach message for a violation.

    Uses the canonical message from the assignment pack:
    "Your line is outside the diminished orbit — you're not using
    the available chromatic approach tones."
    """
    return (
        "Your line is outside the diminished orbit — "
        "you're not using the available chromatic approach tones."
    )


def render_suggestion(context: DimOrbitContext) -> str:
    """
    Render the coach suggestion with placeholders filled.

    Template from pack:
    "In key of {key}, use {dim_notes} as approach tones to chord tones."
    """
    dim_notes_str = ", ".join(context.dim_notes)
    return f"In key of {context.key}, use {dim_notes_str} as approach tones to chord tones."


def evaluate_pitch_classes(
    key: str | int,
    performed_pcs: Sequence[int],
) -> DimOrbitEvaluation:
    """
    Convenience function: evaluate pitch classes directly.

    Parameters
    ----------
    key:
        Key name or pitch class.
    performed_pcs:
        Sequence of pitch classes (0-11) that were performed.

    Returns
    -------
    Evaluation result.
    """
    context = build_context(key if isinstance(key, str) else name_from_pc(key))
    return evaluate_notes(context, performed_pcs)


__all__ = [
    "DimOrbitContext",
    "DimOrbitViolation",
    "DimOrbitEvaluation",
    "build_context",
    "evaluate_notes",
    "evaluate_pitch_classes",
    "render_violation_message",
    "render_suggestion",
]
