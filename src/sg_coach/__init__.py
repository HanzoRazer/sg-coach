"""
sg_coach — Smart Guitar Coach (Mode 1 deterministic coaching spine).

This package provides rule-based evaluation of practice sessions.
Schemas are sourced from sg_spec.schemas.coach_schemas.

Pipeline: SessionRecord → CoachEvaluation → PracticeAssignment

Usage:
    from sg_coach import evaluate_session
    from sg_coach.schemas import SessionRecord, CoachEvaluation, CoachFinding

Layer 1 Coaching Pipelines:
    - diminished_evaluator: DIM_ORBIT_VIOLATION
    - timing_evaluator: TIMING_GRID_DEVIATION
    - pitch_evaluator: WRONG_NOTE / PITCH_DEVIATION
"""

# Core policy
from .coach_policy import evaluate_session, COACH_VERSION

# Evaluators
from .diminished_evaluator import (
    DimOrbitContext,
    DimOrbitViolation,
    DimOrbitEvaluation,
    build_context,
    evaluate_notes,
    evaluate_pitch_classes,
)
from .timing_evaluator import (
    TimingEvent,
    TimingDeviation,
    TimingGridEvaluation,
    evaluate_timing_grid,
    DEFAULT_THRESHOLD_MS,
)
from .exercise_classifier import (
    ExerciseCategory,
    classify_exercise,
    is_diminished_exercise,
    is_timing_grid_exercise,
    is_pitch_exercise,
    extract_key_from_program,
)
from .pitch_evaluator import (
    ExpectedNote,
    PerformedNote,
    PitchComparisonResult,
    evaluate_pitch_accuracy,
    DEFAULT_CENTS_THRESHOLD,
)

# Re-export schemas for convenience
from .schemas import (
    # Enums
    ProgramType,
    Severity,
    ClaveKind,
    CoachMode,
    FeedbackDomain,
    FeedbackSeverity,
    FeedbackRenderHint,
    FeedbackActionType,
    DiagnosisCode,
    # Shared
    ProgramRef,
    # Session layer
    SessionTiming,
    TimingErrorStats,
    PerformanceSummary,
    SessionEvents,
    SessionRecord,
    # Coach layer
    FindingEvidence,
    CoachFinding,
    FocusRecommendation,
    CoachEvaluation,
    SuggestedAction,
    TargetSpan,
    # Assignment layer
    AssignmentConstraints,
    AssignmentFocus,
    SuccessCriteria,
    CoachPrompt,
    PracticeAssignment,
    # Validators
    validate_coach_references_session,
    validate_assignment_program_exists,
    # Mapping helpers
    severity_to_feedback_severity,
)

__all__ = [
    # Version
    "COACH_VERSION",
    # Core policy
    "evaluate_session",
    # Diminished evaluator
    "DimOrbitContext",
    "DimOrbitViolation",
    "DimOrbitEvaluation",
    "build_context",
    "evaluate_notes",
    "evaluate_pitch_classes",
    # Timing evaluator
    "TimingEvent",
    "TimingDeviation",
    "TimingGridEvaluation",
    "evaluate_timing_grid",
    "DEFAULT_THRESHOLD_MS",
    # Exercise classifier
    "ExerciseCategory",
    "classify_exercise",
    "is_diminished_exercise",
    "is_timing_grid_exercise",
    "is_pitch_exercise",
    "extract_key_from_program",
    # Pitch evaluator
    "ExpectedNote",
    "PerformedNote",
    "PitchComparisonResult",
    "evaluate_pitch_accuracy",
    "DEFAULT_CENTS_THRESHOLD",
    # Enums
    "ProgramType",
    "Severity",
    "ClaveKind",
    "CoachMode",
    "FeedbackDomain",
    "FeedbackSeverity",
    "FeedbackRenderHint",
    "FeedbackActionType",
    "DiagnosisCode",
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
    "SuggestedAction",
    "TargetSpan",
    # Assignment layer
    "AssignmentConstraints",
    "AssignmentFocus",
    "SuccessCriteria",
    "CoachPrompt",
    "PracticeAssignment",
    # Validators
    "validate_coach_references_session",
    "validate_assignment_program_exists",
    # Mapping helpers
    "severity_to_feedback_severity",
]
