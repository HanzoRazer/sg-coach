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
from .assignment_outcome import (
    capture_assignment_outcome,
    response_type_from_assignment_outcome,
    assignment_outcome_to_feedback_request,
)
from .session_builder import (
    build_session_from_midi,
    ENGINE_VERSION as SESSION_BUILDER_VERSION,
)
from .practice_history import (
    PracticeHistoryEntry,
    PracticeHistoryQuery,
    PracticeHistoryStats,
    PracticeHistoryStore,
    create_history_entry,
)
from .practice_review import (
    build_session_review,
    build_practice_timeline,
    build_progress_summary,
)
from .goal_tracking import (
    build_weakness_progressions,
    generate_practice_goals,
    build_goal_progress_summary,
    update_goal_status,
)
from .curriculum_alignment import (
    align_goal_to_curriculum,
    curriculum_reference_to_drill_reference,
    build_goal_driven_assignment,
    build_goal_driven_assignments,
    build_progression_recommendation,
)
from .runtime_pipeline import (
    RUNTIME_VERSION,
    run_coaching_pipeline,
    normalize_runtime_output,
    run_fixture_pipeline,
)
from .practice_dashboard import (
    DASHBOARD_VERSION,
    build_practice_dashboard,
)
from .session_playback import (
    PLAYBACK_VERSION,
    DEFAULT_FINDING_WINDOW_MS,
    build_session_playback,
)
from .teacher_review import (
    TEACHER_REVIEW_VERSION,
    build_teacher_review,
    create_teacher_annotation,
    create_teacher_recommendation,
)
from .teacher_review_store import (
    TeacherReviewStore,
)
from .studio_roster_store import (
    STUDIO_ROSTER_VERSION,
    StudioRosterStore,
)
from .practice_queue import (
    QUEUE_VERSION,
    build_practice_queue,
    queue_priority_for_assignment,
    sort_practice_queue,
    mark_assignment_active,
    mark_assignment_completed,
    mark_assignment_deferred,
    mark_assignment_abandoned,
    next_queue_assignment,
)
from .practice_queue_store import (
    PRACTICE_QUEUE_STORE_VERSION,
    PracticeQueueStore,
)
from .outcome_integration import (
    OUTCOME_INTEGRATION_VERSION,
    outcome_to_queue_status,
    should_advance_curriculum,
    process_assignment_outcome,
)
from .runtime_flow import (
    RUNTIME_FLOW_VERSION,
    start_runtime_session,
    complete_runtime_session,
    abandon_runtime_session,
    start_next_queue_assignment,
    attach_session_record,
    attach_evaluation,
    attach_runtime_evidence,
    runtime_session_has_evidence,
)
from .runtime_flow_store import (
    RUNTIME_FLOW_STORE_VERSION,
    RuntimeFlowStore,
)
from .runtime_review import (
    RUNTIME_REVIEW_BUILDER_VERSION,
    build_runtime_evidence_summary,
    build_runtime_outcome_summary,
    build_runtime_review_report,
)
from .longitudinal_review import (
    LONGITUDINAL_REVIEW_BUILDER_VERSION,
    build_diagnosis_trend_summary,
    build_outcome_trajectory_summary,
    build_longitudinal_progress_review,
)
from .pedagogical_ledger import (
    PEDAGOGICAL_LEDGER_BUILDER_VERSION,
    ledger_entries_from_runtime_review,
    ledger_entries_from_longitudinal_review,
    ledger_entry_from_queue_event,
    ledger_entries_from_teacher_review,
    ledger_entry_from_assignment_outcome,
    ledger_entry_from_practice_assignment,
    ledger_entry_from_curriculum_recommendation,
    ledger_entry_from_teacher_scheduling_mediation,
    build_pedagogical_evidence_ledger,
    build_pedagogical_evidence_summary,
)
from .pedagogical_ledger_store import (
    PEDAGOGICAL_LEDGER_STORE_VERSION,
    PedagogicalLedgerStore,
)
from .adaptive_scheduling import (
    ADAPTIVE_SCHEDULING_VERSION,
    REPEATED_OUTCOME_THRESHOLD,
    RECURRING_DIAGNOSIS_THRESHOLD,
    ABANDONMENT_THRESHOLD,
    build_adaptive_scheduling_recommendations,
    build_adaptive_scheduling_plan,
    apply_adaptive_recommendations_to_queue,
)
from .teacher_scheduling_mediation import (
    TEACHER_SCHEDULING_MEDIATION_VERSION,
    create_teacher_scheduling_mediation,
    effective_recommendation_from_mediation,
    effective_scheduling_decision_from_mediation,
    apply_mediation_to_queue,
)
from .teacher_scheduling_mediation_store import (
    TEACHER_SCHEDULING_MEDIATION_STORE_VERSION,
    TeacherSchedulingMediationStore,
)
from .pedagogical_visualization import (
    PEDAGOGICAL_VISUALIZATION_VERSION,
    timeline_event_from_entry,
    timeline_events_from_ledger,
    build_diagnosis_timeline_groups,
    build_pedagogical_timeline_view,
)
from .guided_practice_view import (
    GUIDED_PRACTICE_VIEW_VERSION,
    INSTRUCTIONS_PREVIEW_MAX_LENGTH,
    build_assignment_view,
    build_playback_view,
    build_adaptive_view,
    build_mediation_view,
    build_guided_practice_session_view,
)
from .pedagogical_narrative import (
    PEDAGOGICAL_NARRATIVE_ENGINE_VERSION,
    build_guided_session_narrative,
    build_runtime_review_narrative,
    build_longitudinal_review_narrative,
)
from .session_workspace import (
    SESSION_WORKSPACE_ENGINE_VERSION,
    PANE_ORDER,
    PANE_TITLES,
    build_workspace_panes,
    build_workspace_layout,
    build_session_workspace_projection,
)
from .workspace_export import (
    WORKSPACE_EXPORT_ENGINE_VERSION,
    build_workspace_export_manifest,
    build_workspace_export_package,
    redact_workspace_export_package,
)
from .frontend_state import (
    FRONTEND_STATE_ENGINE_VERSION,
    build_frontend_pane_states,
    build_workspace_navigation_state,
    build_workspace_frontend_state,
)
from .frontend_interaction import (
    FRONTEND_INTERACTION_ENGINE_VERSION,
    generate_event_id,
    apply_frontend_interaction,
)
from .frontend_interaction_store import (
    FRONTEND_INTERACTION_STORE_VERSION,
    FrontendInteractionStore,
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
    # Assignment outcome (Sprint 10)
    "capture_assignment_outcome",
    "response_type_from_assignment_outcome",
    "assignment_outcome_to_feedback_request",
    # Session builder (Sprint 11)
    "build_session_from_midi",
    "SESSION_BUILDER_VERSION",
    # Practice history (Sprint 11)
    "PracticeHistoryEntry",
    "PracticeHistoryQuery",
    "PracticeHistoryStats",
    "PracticeHistoryStore",
    "create_history_entry",
    # Practice review (Sprint 12)
    "build_session_review",
    "build_practice_timeline",
    "build_progress_summary",
    # Goal tracking (Sprint 13)
    "build_weakness_progressions",
    "generate_practice_goals",
    "build_goal_progress_summary",
    "update_goal_status",
    # Curriculum alignment (Sprint 14, 22)
    "align_goal_to_curriculum",
    "curriculum_reference_to_drill_reference",
    "build_goal_driven_assignment",
    "build_goal_driven_assignments",
    "build_progression_recommendation",
    # Runtime pipeline (Sprint 15)
    "RUNTIME_VERSION",
    "run_coaching_pipeline",
    "normalize_runtime_output",
    "run_fixture_pipeline",
    # Practice dashboard (Sprint 17)
    "DASHBOARD_VERSION",
    "build_practice_dashboard",
    # Session playback (Sprint 18)
    "PLAYBACK_VERSION",
    "DEFAULT_FINDING_WINDOW_MS",
    "build_session_playback",
    # Teacher review (Sprint 19)
    "TEACHER_REVIEW_VERSION",
    "build_teacher_review",
    "create_teacher_annotation",
    "create_teacher_recommendation",
    "TeacherReviewStore",
    # Studio roster (Sprint 20)
    "STUDIO_ROSTER_VERSION",
    "StudioRosterStore",
    # Practice queue (Sprint 23)
    "QUEUE_VERSION",
    "build_practice_queue",
    "queue_priority_for_assignment",
    "sort_practice_queue",
    "mark_assignment_active",
    "mark_assignment_completed",
    "mark_assignment_deferred",
    "mark_assignment_abandoned",
    "next_queue_assignment",
    "PRACTICE_QUEUE_STORE_VERSION",
    "PracticeQueueStore",
    # Outcome integration (Sprint 24)
    "OUTCOME_INTEGRATION_VERSION",
    "outcome_to_queue_status",
    "should_advance_curriculum",
    "process_assignment_outcome",
    # Runtime flow (Sprint 25, 26)
    "RUNTIME_FLOW_VERSION",
    "start_runtime_session",
    "complete_runtime_session",
    "abandon_runtime_session",
    "start_next_queue_assignment",
    "attach_session_record",
    "attach_evaluation",
    "attach_runtime_evidence",
    "runtime_session_has_evidence",
    "RUNTIME_FLOW_STORE_VERSION",
    "RuntimeFlowStore",
    # Runtime review (Sprint 27)
    "RUNTIME_REVIEW_BUILDER_VERSION",
    "build_runtime_evidence_summary",
    "build_runtime_outcome_summary",
    "build_runtime_review_report",
    # Longitudinal review (Sprint 28)
    "LONGITUDINAL_REVIEW_BUILDER_VERSION",
    "build_diagnosis_trend_summary",
    "build_outcome_trajectory_summary",
    "build_longitudinal_progress_review",
    # Pedagogical ledger (Sprint 29)
    "PEDAGOGICAL_LEDGER_BUILDER_VERSION",
    "ledger_entries_from_runtime_review",
    "ledger_entries_from_longitudinal_review",
    "ledger_entry_from_queue_event",
    "ledger_entries_from_teacher_review",
    "ledger_entry_from_assignment_outcome",
    "ledger_entry_from_practice_assignment",
    "ledger_entry_from_curriculum_recommendation",
    "build_pedagogical_evidence_ledger",
    "build_pedagogical_evidence_summary",
    "PEDAGOGICAL_LEDGER_STORE_VERSION",
    "PedagogicalLedgerStore",
    # Adaptive scheduling (Sprint 30)
    "ADAPTIVE_SCHEDULING_VERSION",
    "REPEATED_OUTCOME_THRESHOLD",
    "RECURRING_DIAGNOSIS_THRESHOLD",
    "ABANDONMENT_THRESHOLD",
    "build_adaptive_scheduling_recommendations",
    "build_adaptive_scheduling_plan",
    "apply_adaptive_recommendations_to_queue",
    # Teacher scheduling mediation (Sprint 31, 32)
    "TEACHER_SCHEDULING_MEDIATION_VERSION",
    "create_teacher_scheduling_mediation",
    "effective_recommendation_from_mediation",
    "effective_scheduling_decision_from_mediation",
    "apply_mediation_to_queue",
    "ledger_entry_from_teacher_scheduling_mediation",
    "TEACHER_SCHEDULING_MEDIATION_STORE_VERSION",
    "TeacherSchedulingMediationStore",
    # Pedagogical visualization (Sprint 33)
    "PEDAGOGICAL_VISUALIZATION_VERSION",
    "timeline_event_from_entry",
    "timeline_events_from_ledger",
    "build_diagnosis_timeline_groups",
    "build_pedagogical_timeline_view",
    # Guided practice view (Sprint 34)
    "GUIDED_PRACTICE_VIEW_VERSION",
    "INSTRUCTIONS_PREVIEW_MAX_LENGTH",
    "build_assignment_view",
    "build_playback_view",
    "build_adaptive_view",
    "build_mediation_view",
    "build_guided_practice_session_view",
    # Pedagogical narrative (Sprint 35)
    "PEDAGOGICAL_NARRATIVE_ENGINE_VERSION",
    "build_guided_session_narrative",
    "build_runtime_review_narrative",
    "build_longitudinal_review_narrative",
    # Session workspace (Sprint 36)
    "SESSION_WORKSPACE_ENGINE_VERSION",
    "PANE_ORDER",
    "PANE_TITLES",
    "build_workspace_panes",
    "build_workspace_layout",
    "build_session_workspace_projection",
    # Workspace export (Sprint 37)
    "WORKSPACE_EXPORT_ENGINE_VERSION",
    "build_workspace_export_manifest",
    "build_workspace_export_package",
    "redact_workspace_export_package",
    # Frontend state (Sprint 38)
    "FRONTEND_STATE_ENGINE_VERSION",
    "build_frontend_pane_states",
    "build_workspace_navigation_state",
    "build_workspace_frontend_state",
    # Frontend interaction (Sprint 39)
    "FRONTEND_INTERACTION_ENGINE_VERSION",
    "generate_event_id",
    "apply_frontend_interaction",
    "FRONTEND_INTERACTION_STORE_VERSION",
    "FrontendInteractionStore",
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
