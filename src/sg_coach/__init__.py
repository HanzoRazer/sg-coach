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
from .session_normalizer import (
    normalize_session,
    ensure_normalized_session,
    has_timing_input,
    has_pitch_input,
    has_harmony_input,
)
from .action_recommender import (
    recommend_actions,
    recommend_actions_batch,
)
from .recommendation_integration import (
    attach_recommendations,
)
from .feedback_capture import (
    capture_feedback,
    validate_feedback_linkage,
    FeedbackLinkageWarning,
)
from .learning_weight import (
    compute_signal_weight,
    compute_confidence_modifier,
    derive_learning_signal,
    is_weak_signal,
    BASE_EFFECTIVENESS,
    OUTCOME_MODIFIER,
    WEIGHT_MIN,
    WEIGHT_MAX,
    WEAK_SIGNAL_THRESHOLD,
)
from .learning_aggregation import (
    aggregate_effectiveness,
    compute_aggregate_confidence,
)
from .adaptive_ranking import (
    rank_recommendations,
    CONFIDENCE_THRESHOLD,
)
from .learning_store import (
    LearningSignalStore,
    aggregate_user_effectiveness,
    aggregate_global_effectiveness,
)
from .personalization_blend import (
    compute_blended_effectiveness,
    compute_personalized_action_score,
    rank_recommendations_personalized,
)
from .drill_resolver import (
    resolve_drill,
    request_from_recommended_action,
    resolve_drills_for_recommendations,
)
from .practice_assignment_assembler import (
    assemble_practice_assignment,
    assemble_practice_assignments,
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
    # Action recommendations (Sprint 4)
    ActionRecommendationSet,
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
    # Session normalizer (Sprint 3)
    "normalize_session",
    "ensure_normalized_session",
    "has_timing_input",
    "has_pitch_input",
    "has_harmony_input",
    # Normalized evaluation inputs (Sprint 3)
    "HarmonyEvaluationInput",
    "TimingEvaluationInput",
    "PitchEvaluationInput",
    "NormalizedSessionData",
    # Action recommender (Sprint 4)
    "recommend_actions",
    "recommend_actions_batch",
    "attach_recommendations",
    # Feedback capture (Sprint 5)
    "capture_feedback",
    "validate_feedback_linkage",
    "FeedbackLinkageWarning",
    # Learning weight (Sprint 5)
    "compute_signal_weight",
    "compute_confidence_modifier",
    "derive_learning_signal",
    "is_weak_signal",
    "BASE_EFFECTIVENESS",
    "OUTCOME_MODIFIER",
    "WEIGHT_MIN",
    "WEIGHT_MAX",
    "WEAK_SIGNAL_THRESHOLD",
    # Learning aggregation (Sprint 5)
    "aggregate_effectiveness",
    "compute_aggregate_confidence",
    # Adaptive ranking (Sprint 5)
    "rank_recommendations",
    "CONFIDENCE_THRESHOLD",
    # Learning store (Sprint 6)
    "LearningSignalStore",
    "aggregate_user_effectiveness",
    "aggregate_global_effectiveness",
    # Personalization blend (Sprint 7)
    "compute_blended_effectiveness",
    "compute_personalized_action_score",
    "rank_recommendations_personalized",
    # Drill resolution (Sprint 8)
    "resolve_drill",
    "request_from_recommended_action",
    "resolve_drills_for_recommendations",
    # Practice assignment assembly (Sprint 9)
    "assemble_practice_assignment",
    "assemble_practice_assignments",
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
    # Action recommendations (Sprint 4)
    "ActionRecommendationSet",
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
