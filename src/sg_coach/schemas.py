"""
sg_coach.schemas — Coach data types re-exported from sg-spec.

This module re-exports all coach schema types from the canonical source
in sg_spec.schemas.coach_schemas.

Usage:
    from sg_coach.schemas import (
        SessionRecord,
        CoachFinding,
        CoachEvaluation,
        PracticeAssignment,
        Severity,
        FeedbackDomain,
        FeedbackSeverity,
    )
"""
from sg_spec.schemas.coach_schemas import (
    # Type aliases
    Sha256,
    # Enums
    ProgramType,
    Severity,
    ClaveKind,
    CoachMode,
    # Severity mapping
    severity_to_feedback_severity,
    # Shared
    ProgramRef,
    # Normalized evaluation inputs (Sprint 3)
    HarmonyEvaluationInput,
    TimingEvaluationInput,
    PitchEvaluationInput,
    NormalizedSessionData,
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
)

from sg_spec.schemas.feedback_vocabulary import (
    FeedbackDomain,
    FeedbackSeverity,
    FeedbackRenderHint,
    FeedbackActionType,
)

from sg_spec.schemas.adaptive_feedback import DiagnosisCode

__all__ = [
    # Type aliases
    "Sha256",
    # Enums
    "ProgramType",
    "Severity",
    "ClaveKind",
    "CoachMode",
    # Feedback vocabulary
    "FeedbackDomain",
    "FeedbackSeverity",
    "FeedbackRenderHint",
    "FeedbackActionType",
    "DiagnosisCode",
    # Severity mapping
    "severity_to_feedback_severity",
    # Shared
    "ProgramRef",
    # Normalized evaluation inputs (Sprint 3)
    "HarmonyEvaluationInput",
    "TimingEvaluationInput",
    "PitchEvaluationInput",
    "NormalizedSessionData",
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
]
