"""
Coach Schema v1: Session -> Coach -> Assignment spine.

Single source of truth for coach-related types.
This module is the authoritative definition consumed by both sg-coach and zt-band.

Three layers with strict ownership boundaries:
- SessionRecord: What happened (runtime owns, immutable facts)
- CoachEvaluation: What it means (coach owns, interpretation)
- PracticeAssignment: What's next (planner owns, intent)

INVARIANT: These layers never blur. If they do, stop and fix it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# Type Aliases
# ============================================================================

Sha256 = str  # recommended format: "sha256:<hex>"


# ============================================================================
# Enums
# ============================================================================


class ProgramType(str, Enum):
    """Type of program artifact."""
    ztprog = "ztprog"
    ztex = "ztex"
    ztplay = "ztplay"


class Severity(str, Enum):
    """Finding severity level."""
    primary = "primary"      # Critical issue
    secondary = "secondary"  # Warning-level
    info = "info"           # Informational


class ClaveKind(str, Enum):
    """Clave pattern type."""
    son_2_3 = "son_2_3"
    son_3_2 = "son_3_2"


class CoachMode(str, Enum):
    """Coach evaluation mode."""
    rules_first = "rules_first"   # Mode 1: All text from templates (deterministic)
    hybrid = "hybrid"             # Mode 2: AI phrases, rules structure
    generative = "generative"     # Mode 3: AI proposes new exercises


# ============================================================================
# Shared Components
# ============================================================================


class ProgramRef(BaseModel):
    """
    Immutable reference to an authored program/exercise artifact.
    'hash' should refer to the canonical on-disk payload (e.g., the .ztprog file bytes).
    """

    model_config = ConfigDict(extra="forbid")

    type: ProgramType
    name: str = Field(min_length=1)
    hash: Optional[Sha256] = None

    @field_validator("hash")
    @classmethod
    def _hash_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.startswith("sha256:"):
            raise ValueError("hash must start with 'sha256:'")
        if len(v) <= len("sha256:"):
            raise ValueError("hash must include sha256 hex after 'sha256:'")
        return v


# ============================================================================
# 1) SessionRecord (What happened — facts only)
# ============================================================================
# Owner: Runtime / Telemetry
# Created by: Smart Guitar / String Master runtime
# Consumed by: Coach (Mode 1, 2, 3)
#
# Invariants:
#   - No free text
#   - No AI language
#   - No user identity beyond instrument/session
#   - Hashes link to immutable engine artifacts
# ============================================================================


class SessionTiming(BaseModel):
    """Timing configuration for a practice session."""
    model_config = ConfigDict(extra="forbid")

    bpm: float = Field(gt=0)
    grid: int = Field(description="8 or 16, matching realtime grid resolution")
    clave: Optional[ClaveKind] = None

    strict: bool = True
    strict_window_ms: Optional[int] = Field(default=None, description="If strict, optional window size")

    # realtime robustness settings (for truthful analysis)
    late_drop_ms: int = Field(default=35, ge=0, le=500)
    ghost_vel_max: int = Field(default=22, ge=1, le=127)
    panic_enabled: bool = True

    @field_validator("grid")
    @classmethod
    def _grid_allowed(cls, v: int) -> int:
        if v not in (8, 16):
            raise ValueError("grid must be 8 or 16")
        return v

    @model_validator(mode="after")
    def _strict_window_consistency(self) -> "SessionTiming":
        if self.strict_window_ms is not None and not self.strict:
            raise ValueError("strict_window_ms is only valid when strict=true")
        if self.strict_window_ms is not None:
            if not (0 <= self.strict_window_ms <= 500):
                raise ValueError("strict_window_ms must be 0..500")
        return self


class TimingErrorStats(BaseModel):
    """Statistical summary of timing errors."""
    model_config = ConfigDict(extra="forbid")

    mean: float = 0.0
    std: float = 0.0
    max: float = 0.0

    @model_validator(mode="after")
    def _non_negative(self) -> "TimingErrorStats":
        if self.std < 0 or self.max < 0:
            raise ValueError("std/max must be non-negative")
        return self


class PerformanceSummary(BaseModel):
    """What the player actually did."""
    model_config = ConfigDict(extra="forbid")

    bars_played: int = Field(ge=0)
    notes_expected: int = Field(ge=0)
    notes_played: int = Field(ge=0)
    notes_dropped: int = Field(ge=0)

    timing_error_ms: TimingErrorStats = Field(default_factory=TimingErrorStats)

    # per-step mean error magnitude (ms). step keys are "0".."15" (grid=16) or "0".."7" (grid=8)
    error_by_step: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _counts_consistent(self) -> "PerformanceSummary":
        if self.notes_played + self.notes_dropped < self.notes_expected:
            raise ValueError("notes_played + notes_dropped must be >= notes_expected")
        return self


class SessionEvents(BaseModel):
    """Discrete events during session."""
    model_config = ConfigDict(extra="forbid")

    late_drops: int = Field(default=0, ge=0)
    panic_triggered: bool = False


class SessionRecord(BaseModel):
    """
    Pure fact. No opinions. No coaching.
    This is the immutable truth of what happened during practice.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    instrument_id: str = Field(min_length=1)

    engine_version: str = Field(min_length=1, description="e.g., zt-band@0.2.0")
    program_ref: ProgramRef

    timing: SessionTiming
    duration_s: int = Field(ge=0)

    performance: PerformanceSummary = Field(default_factory=PerformanceSummary)
    events: SessionEvents = Field(default_factory=SessionEvents)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _error_by_step_keys(self) -> "SessionRecord":
        # enforce step key ranges based on timing.grid
        max_step = 15 if self.timing.grid == 16 else 7
        for k in self.performance.error_by_step.keys():
            if not k.isdigit():
                raise ValueError("error_by_step keys must be digit strings")
            i = int(k)
            if not (0 <= i <= max_step):
                raise ValueError(f"error_by_step step key {i} out of range 0..{max_step}")
        return self


# ============================================================================
# 2) CoachEvaluation (What it means — structured interpretation)
# ============================================================================
# Owner: Coach layer (Mode 1 deterministic; Mode 2 phrased by AI)
# Created by: Coach
# Consumed by: Assignment planner + UI
#
# Invariants:
#   - Coach cannot change notes, chords, or style
#   - Findings must reference measured facts
#   - confidence is required (forces honesty)
# ============================================================================


class FindingEvidence(BaseModel):
    """Evidence backing a coaching finding — must reference measured facts."""
    model_config = ConfigDict(extra="forbid")

    step: Optional[int] = Field(default=None, ge=0, le=15)
    mean_error_ms: Optional[float] = None
    metric: Optional[str] = None
    value: Optional[float] = None


class CoachFinding(BaseModel):
    """A single coaching observation tied to evidence."""
    model_config = ConfigDict(extra="forbid")

    type: Literal["timing", "harmony", "technique", "consistency", "other"]
    severity: Severity
    evidence: FindingEvidence = Field(default_factory=FindingEvidence)
    interpretation: str = Field(min_length=1, max_length=240)


class FocusRecommendation(BaseModel):
    """What to focus on next, derived from findings."""
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=240)


class CoachEvaluation(BaseModel):
    """
    Interpretation, but still structured.
    Coach sees facts, produces meaning. Never touches music.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    coach_version: str = Field(min_length=1, description="e.g., coach-rules@0.1.0")

    findings: List[CoachFinding] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)

    focus_recommendation: FocusRecommendation
    confidence: float = Field(ge=0.0, le=1.0)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("strengths", "weaknesses")
    @classmethod
    def _bullets_reasonable(cls, v: List[str]) -> List[str]:
        for s in v:
            if len(s) > 160:
                raise ValueError("strength/weakness items must be <= 160 chars")
        return v


# ============================================================================
# 3) PracticeAssignment (What to do next — intent)
# ============================================================================
# Owner: Curriculum / Planner
# Created by: Assignment engine (possibly AI-assisted)
# Consumed by: Runtime
#
# Invariants:
#   - Assignment cannot invent new theory
#   - Only uses existing programs/exercises
#   - Constraints are numeric, testable, and reversible
# ============================================================================


class AssignmentConstraints(BaseModel):
    """Numeric, testable, reversible constraints."""
    model_config = ConfigDict(extra="forbid")

    tempo_start: int = Field(ge=20, le=300)
    tempo_target: int = Field(ge=20, le=300)
    tempo_step: int = Field(ge=1, le=40, description="BPM step when ramping")

    strict: bool = True
    strict_window_ms: Optional[int] = Field(default=None, ge=0, le=500)

    bars_per_loop: int = Field(ge=1, le=16)
    repetitions: int = Field(ge=1, le=999)

    @model_validator(mode="after")
    def _tempo_ramp(self) -> "AssignmentConstraints":
        if self.tempo_target < self.tempo_start:
            raise ValueError("tempo_target must be >= tempo_start")
        if self.strict_window_ms is not None and not self.strict:
            raise ValueError("strict_window_ms is only valid when strict=true")
        return self


class AssignmentFocus(BaseModel):
    """What to pay attention to."""
    model_config = ConfigDict(extra="forbid")

    primary: str = Field(min_length=1, max_length=64)
    secondary: Optional[str] = Field(default=None, max_length=64)


class SuccessCriteria(BaseModel):
    """Measurable success thresholds."""
    model_config = ConfigDict(extra="forbid")

    max_mean_error_ms: float = Field(gt=0, le=2000)
    max_late_drops: int = Field(ge=0, le=9999)


class CoachPrompt(BaseModel):
    """Optional coaching message for UI."""
    model_config = ConfigDict(extra="forbid")

    mode: Literal["none", "optional", "required"] = "optional"
    message: Optional[str] = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def _message_required_if_not_none(self) -> "CoachPrompt":
        if self.mode != "none" and (self.message is None or not self.message.strip()):
            raise ValueError("message is required when mode is optional/required")
        if self.mode == "none" and self.message is not None:
            raise ValueError("message must be omitted when mode=none")
        return self


class PracticeAssignment(BaseModel):
    """
    Controls practice, not music.
    This is intent — what the student should do next.
    """

    model_config = ConfigDict(extra="forbid")

    assignment_id: UUID
    session_id: UUID

    program: ProgramRef
    constraints: AssignmentConstraints
    focus: AssignmentFocus
    success_criteria: SuccessCriteria

    coach_prompt: CoachPrompt = Field(default_factory=CoachPrompt)
    expires_after_sessions: int = Field(default=3, ge=1, le=50)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _program_type_allowed(self) -> "PracticeAssignment":
        if self.program.type not in (ProgramType.ztprog, ProgramType.ztex):
            raise ValueError("program.type must be ztprog or ztex for PracticeAssignment")
        return self


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_coach_references_session(
    evaluation: CoachEvaluation,
    session: SessionRecord,
) -> None:
    """Ensure coach findings reference actual session data."""
    if evaluation.session_id != session.session_id:
        raise ValueError("CoachEvaluation.session_id must match SessionRecord.session_id")

    # Validate that referenced steps exist in session data
    session_steps = set(session.performance.error_by_step.keys())
    for finding in evaluation.findings:
        if finding.evidence.step is not None:
            if str(finding.evidence.step) not in session_steps:
                raise ValueError(
                    f"Finding references step {finding.evidence.step} "
                    f"not in session data: {session_steps}"
                )


def validate_assignment_program_exists(
    assignment: PracticeAssignment,
    available_programs: set[str],
) -> None:
    """Ensure assignment references an existing program."""
    if assignment.program.name not in available_programs:
        raise ValueError(
            f"Assignment references unknown program: {assignment.program.name}"
        )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Type aliases
    "Sha256",
    # Enums
    "ProgramType",
    "Severity",
    "ClaveKind",
    "CoachMode",
    # Shared
    "ProgramRef",
    # Session layer
    "SessionTiming",
    "TimingErrorStats",
    "PerformanceSummary",
    "SessionEvents",
    "SessionRecord",
    # Coach layer
    "FindingEvidence",
    "CoachFinding",
    "FocusRecommendation",
    "CoachEvaluation",
    # Assignment layer
    "AssignmentConstraints",
    "AssignmentFocus",
    "SuccessCriteria",
    "CoachPrompt",
    "PracticeAssignment",
    # Validators
    "validate_coach_references_session",
    "validate_assignment_program_exists",
]
