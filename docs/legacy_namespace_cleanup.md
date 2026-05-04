# Legacy Namespace Cleanup

Date: 2026-05-04

## Summary

This document records the removal of legacy `sg_spec.ai.coach.*` namespace references from sg-coach. These references pointed to modules that no longer exist in sg-spec after the migration to the canonical `sg_spec.schemas.*` namespace.

## Canonical Paths

### Current (Use These)

```python
# Schemas
from sg_spec.schemas.coach_schemas import (
    SessionRecord,
    CoachEvaluation,
    CoachFinding,
    PracticeAssignment,
    # ... all coach types
)

# Feedback vocabulary
from sg_spec.schemas.feedback_vocabulary import (
    FeedbackDomain,
    FeedbackSeverity,
    FeedbackActionType,
)

# Diagnosis codes
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

# Action mapping
from sg_spec.schemas.action_mapping import (
    ActionMapping,
    RecommendedAction,
    ActionRecommendationSet,
)

# Via sg-coach convenience re-exports
from sg_coach import evaluate_session, attach_recommendations
from sg_coach.schemas import CoachEvaluation, CoachFinding
```

### Deprecated (Removed)

```python
# NO LONGER EXISTS - was migrated to sg_spec.schemas.*
from sg_spec.ai.coach.schemas import ...
from sg_spec.ai.coach.fixtures import ...
from sg_spec.ai.coach.* import ...
```

## What Was Removed

### Legacy Stub Modules (sg-coach/src/sg_coach/)

These files were 3-line re-export stubs pointing to non-existent `sg_spec.ai.coach.*` modules:

| File | Status |
|------|--------|
| `assignment_policy.py` | Deleted |
| `assignment_serializer.py` | Deleted |
| `assignment_v0_5.py` | Deleted |
| `assignment_v0_6.py` | Deleted |
| `cli.py` | Deleted |
| `commit_state_reducer_v0_7.py` | Deleted |
| `contract.py` | Deleted |
| `evaluation_builder_v0_3.py` | Deleted |
| `evaluation_v0_3.py` | Deleted |
| `fixture_generator_v1_0.py` | Deleted |
| `fixtures/__init__.py` | Deleted |
| `golden_meta_v1_1.py` | Deleted |
| `golden_update_v1_0.py` | Deleted |
| `groove_contracts.py` | Deleted |
| `meta_autofill_v1_2.py` | Deleted |
| `meta_gate_v1_2.py` | Deleted |
| `ota_payload.py` | Deleted |
| `planner_v0_4.py` | Deleted |
| `planner_v0_5.py` | Deleted |
| `planner_v0_6.py` | Deleted |
| `replay_all_v0_9.py` | Deleted |
| `replay_gate_v0_8.py` | Deleted |
| `replay_utils_v0_9.py` | Deleted |
| `sqlite_store_v0_8.py` | Deleted |
| `store_shim_v0_7.py` | Deleted |
| `versioning_v1_2.py` | Deleted |

### Legacy Tests (sg-coach/tests/)

These tests imported from the dead namespace and tested v0.x functionality superseded by Layer 1:

| File | Status |
|------|--------|
| `test_assignment_serializer.py` | Deleted |
| `test_coach_policy_mode1.py` | Deleted |
| `test_commit_state_reducer_v0_7.py` | Deleted |
| `test_evaluation_builder_v0_3.py` | Deleted |
| `test_golden_update_guard_v1_0.py` | Deleted |
| `test_groove_contracts.py` | Deleted |
| `test_meta_gate_v1_2.py` | Deleted |
| `test_ota_bundle_manifest.py` | Deleted |
| `test_ota_bundle_zip_and_signature.py` | Deleted |
| `test_planner_v0_4.py` | Deleted |
| `test_planner_v0_5.py` | Deleted |
| `test_planner_v0_6.py` | Deleted |
| `test_replay_all_v0_9.py` | Deleted |
| `test_replay_gate_v0_8.py` | Deleted |
| `test_sgc_cli_ota_bundle.py` | Deleted |
| `test_sgc_cli_ota_verify.py` | Deleted |
| `test_sgc_cli_ota_verify_zip.py` | Deleted |
| `test_sgc_cli_ota_verify_zip_signature_tamper.py` | Deleted |
| `test_sgc_cli_ota_verify_zip_tamper.py` | Deleted |
| `test_sqlite_store_v0_8.py` | Deleted |
| `test_store_shim_v0_7.py` | Deleted |
| `test_vector_meta_and_provenance_v1_1.py` | Deleted |

### Documentation Updated

| File | Change |
|------|--------|
| `.github/copilot-instructions.md` | Updated to use canonical paths |

## What Was Preserved

All Layer 1 coaching pipeline code (Sprints 1-4) was preserved:

- `coach_policy.py` — evaluate_session()
- `diminished_evaluator.py` — DIM_ORBIT_VIOLATION
- `timing_evaluator.py` — TIMING_GRID_DEVIATION
- `pitch_evaluator.py` — WRONG_NOTE / PITCH_DEVIATION
- `session_normalizer.py` — normalize_session()
- `exercise_classifier.py` — classify_exercise()
- `action_recommender.py` — recommend_actions()
- `recommendation_integration.py` — attach_recommendations()
- `default_action_mappings.py` — DEFAULT_ACTION_MAPPINGS
- `schemas.py` — re-exports from sg_spec.schemas.*

All Layer 1 tests (183 tests) remain and pass.

## Why This Was Done

1. **Dead code removal**: The `sg_spec.ai.coach` namespace was migrated to `sg_spec.schemas.*` but the stub files in sg-coach were never updated.

2. **Single canonical path**: All coach-related types now come from `sg_spec.schemas.*` (or via `sg_coach.schemas`).

3. **Sprints 1-4 supersede v0.x**: The Layer 1 coaching pipeline provides the production architecture. The v0.x planners/evaluators were prototype code.

4. **Broken code is worse than deleted code**: Keeping import errors in main creates confusion and CI noise.

## Migration Guide

If you have code importing from the old paths:

```python
# OLD (broken)
from sg_coach.evaluation_v0_3 import EvaluationV0_3
from sg_coach.planner_v0_4 import plan_next_v0_4

# NEW
from sg_coach import evaluate_session, attach_recommendations
from sg_coach.schemas import CoachEvaluation, CoachFinding
```

The v0.x APIs are not directly replaceable — they represent a different architecture. Use the Layer 1 pipeline instead.
