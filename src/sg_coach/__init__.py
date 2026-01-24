"""
Smart Guitar Coach — Mode 1 (deterministic coaching spine).

Pipeline: SessionRecord → CoachEvaluation → PracticeAssignment

This module provides:
- Pydantic v2 models for session data, evaluations, and assignments
- Deterministic evaluation policy (facts → findings → focus)
- Deterministic assignment planner (focus → constraints → success criteria)
- OTA bundle builder + verifier (manifest, HMAC signing, zip packaging)
- CLI tools: sgc export-bundle, ota-pack, ota-verify, ota-bundle, ota-verify-zip
"""

from .contract import COACH_CONTRACT_VERSION
from .schemas import (
    # Enums
    ProgramType,
    Severity,
    ClaveKind,
    CoachMode,
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
from .coach_policy import evaluate_session, COACH_VERSION
from .assignment_policy import plan_assignment, AssignmentPolicyConfig
from .assignment_serializer import (
    FirmwareEnvelope,
    serialize_bundle,
    deserialize_bundle,
)
from .ota_payload import (
    # Constants
    OTA_BUNDLE_CONTRACT_VERSION,
    HMAC_ALGORITHM,
    # Manifest
    OtaArtifact,
    OtaBundleManifest,
    # Envelope
    OtaEnvelope,
    # Functions
    hmac_sha256_hex,
    sha256_file,
    sha256_bytes,
    build_ota_payload,
    verify_ota_payload,
    build_assignment_ota_bundle,
    verify_bundle_integrity,
    verify_bundle_signature,
    verify_zip_bundle,
    BundleBuildResult,
)
from .cli import main

# v0.3: Groove-aware evaluation
from .groove_contracts import GrooveSnapshotV0, ControlIntentV0
from .evaluation_v0_3 import EvaluationV0_3, CoachFeedbackV0
from .evaluation_builder_v0_3 import EvaluationBuilderV0_3

# v0.4: Planner consumes control_intent + flags
from .planner_v0_4 import (
    AssignmentV0_4,
    CoachFeedbackCompat,
    PlannerPolicyV0_4,
    plan_next_v0_4,
)

# v0.5: Structured override reasons
from .assignment_v0_5 import (
    OverrideReason,
    OverrideDecisionV0,
    CoachFeedbackV0_5,
    AssignmentV0_5,
)
from .planner_v0_5 import (
    PlannerPolicyV0_5,
    plan_next_v0_5,
)

# v0.6: History-aware + anti-oscillation
from .assignment_v0_6 import (
    CommitMode,
    CommitStateV0,
    AssignmentV0_6,
)
from .planner_v0_6 import (
    PlannerPolicyV0_6,
    plan_next_v0_6,
)

# v0.7: Commit-state reducer + store shim
from .commit_state_reducer_v0_7 import reduce_commit_state
from .store_shim_v0_7 import InMemoryCoachStoreV0_7, SessionStateV0_7

# v0.8: SQLite adapter + replay gate
from .sqlite_store_v0_8 import SQLiteCoachStoreV0_8, SqliteStoreConfigV0_8
from .replay_gate_v0_8 import replay_vector_dir, ReplayResultV0_8

# v0.9: Replay-all + diff printer + seedable timestamps
from .replay_utils_v0_9 import ReplayDiffV0_9, json_diff, seeded_utc_iso, normalize_assignment_for_compare
from .replay_all_v0_9 import replay_all, ReplayAllResultV0_9

# v1.0: Fixture generator + golden-update guard
from .golden_update_v1_0 import update_goldens, GoldenUpdateResultV1_0
from .fixture_generator_v1_0 import generate_assignment_fixture

# v1.1: Golden metadata + per-vector seeds + fixture provenance
from .golden_meta_v1_1 import VectorMetaV1_1, read_vector_meta, ensure_vector_meta

# v1.2: Meta-required gate + fixture provenance policy
from .versioning_v1_2 import CURRENT_GENERATOR_VERSION
from .meta_gate_v1_2 import run_gates, GateFailureV1_2
from .meta_autofill_v1_2 import autofill_meta, AutofillReportV1_2
from .meta_gate_v1_2 import run_gates, GateFailureV1_2

__all__ = [
    # Contract
    "COACH_CONTRACT_VERSION",
    "COACH_VERSION",
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
    # Policies
    "evaluate_session",
    "plan_assignment",
    "AssignmentPolicyConfig",
    # Serialization
    "FirmwareEnvelope",
    "serialize_bundle",
    "deserialize_bundle",
    # OTA
    "OTA_BUNDLE_CONTRACT_VERSION",
    "HMAC_ALGORITHM",
    "OtaArtifact",
    "OtaBundleManifest",
    "OtaEnvelope",
    "hmac_sha256_hex",
    "sha256_file",
    "sha256_bytes",
    "build_ota_payload",
    "verify_ota_payload",
    "build_assignment_ota_bundle",
    "verify_bundle_integrity",
    "verify_bundle_signature",
    "verify_zip_bundle",
    "BundleBuildResult",
    # CLI
    "main",
    # v0.3: Groove-aware evaluation
    "GrooveSnapshotV0",
    "ControlIntentV0",
    "EvaluationV0_3",
    "CoachFeedbackV0",
    "EvaluationBuilderV0_3",
    # v0.4: Planner
    "AssignmentV0_4",
    "CoachFeedbackCompat",
    "PlannerPolicyV0_4",
    "plan_next_v0_4",
    # v0.5: Structured override reasons
    "OverrideReason",
    "OverrideDecisionV0",
    "CoachFeedbackV0_5",
    "AssignmentV0_5",
    "PlannerPolicyV0_5",
    "plan_next_v0_5",
    # v0.6: History-aware + anti-oscillation
    "CommitMode",
    "CommitStateV0",
    "AssignmentV0_6",
    "PlannerPolicyV0_6",
    "plan_next_v0_6",
    # v0.7: Commit-state reducer + store shim
    "reduce_commit_state",
    "InMemoryCoachStoreV0_7",
    "SessionStateV0_7",
    # v0.8: SQLite adapter + replay gate
    "SQLiteCoachStoreV0_8",
    "SqliteStoreConfigV0_8",
    "replay_vector_dir",
    "ReplayResultV0_8",
    # v0.9: Replay-all + diff printer + seedable timestamps
    "ReplayDiffV0_9",
    "json_diff",
    "seeded_utc_iso",
    "normalize_assignment_for_compare",
    "replay_all",
    "ReplayAllResultV0_9",
    # v1.0: Fixture generator + golden-update guard
    "update_goldens",
    "GoldenUpdateResultV1_0",
    "generate_assignment_fixture",
    # v1.1: Golden metadata + per-vector seeds + fixture provenance
    "VectorMetaV1_1",
    "read_vector_meta",
    "ensure_vector_meta",
    # v1.2: Meta-required gate + fixture provenance policy
    "CURRENT_GENERATOR_VERSION",
    "run_gates",
    "GateFailureV1_2",
    # v1.2: Meta autofill (non-CI utility)
    "autofill_meta",
    "AutofillReportV1_2",
]
