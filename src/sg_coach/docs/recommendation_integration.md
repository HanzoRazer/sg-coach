# Recommendation Integration Contract

Sprint 4: Contract for attaching action recommendations to CoachEvaluation.

## Purpose

This document defines the integration contract between CoachEvaluation and ActionRecommendationSet. It specifies how recommendations are attached to evaluations and the invariants that must be maintained.

## Architecture

```
SessionRecord → evaluate_session() → CoachEvaluation
                                          ↓
                                   attach_recommendations()
                                          ↓
                              CoachEvaluation.recommendations
                                          ↓
                              List[ActionRecommendationSet]
```

## CoachEvaluation.recommendations Field

Added in Sprint 4, this optional field holds action recommendations for each finding.

```python
class CoachEvaluation(BaseModel):
    # ... existing fields ...
    
    recommendations: Optional[List[ActionRecommendationSet]] = Field(
        default=None,
        description="Recommended actions for each finding, populated by action recommender",
    )
```

### Field Semantics

**IMPORTANT**: `None` and `[]` have distinct meanings:

| State | Meaning |
|-------|---------|
| `None` | Recommendations **not yet attached** — `attach_recommendations()` has not been called |
| `[]` | Recommendations **attached, no findings** — evaluation has zero findings, so zero recommendation sets |
| `[ActionRecommendationSet, ...]` | Recommendations **attached with findings** — one set per finding |

This distinction matters for:
- UI: `None` means "loading" or "not computed"; `[]` means "nothing to show"
- Serialization: Both are valid states that round-trip correctly
- Idempotency: Re-attaching recommendations to an evaluation with `recommendations=[]` produces `[]` again

## attach_recommendations() Function

```python
def attach_recommendations(
    evaluation: CoachEvaluation,
    mappings: Optional[Mapping[DiagnosisCode, ActionMapping]] = None,
) -> CoachEvaluation:
    """Attach action recommendations to a CoachEvaluation."""
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `evaluation` | `CoachEvaluation` | required | The evaluation to enhance |
| `mappings` | `Mapping[DiagnosisCode, ActionMapping]` | `DEFAULT_ACTION_MAPPINGS` | Custom mappings registry |

### Guarantees

1. **Immutable pattern**: Returns a new CoachEvaluation; does not mutate input
2. **Order preservation**: `recommendations[i]` corresponds to `findings[i]`
3. **Complete coverage**: Every finding gets a recommendation set (may be empty)
4. **No failures**: Unmapped codes produce empty sets, not exceptions

### Usage Patterns

#### Pattern A: Sequential (recommended)

```python
from sg_coach import evaluate_session, attach_recommendations

evaluation = evaluate_session(session)
evaluation = attach_recommendations(evaluation)
```

#### Pattern B: Pipeline

```python
evaluation = attach_recommendations(evaluate_session(session))
```

#### Pattern C: Custom mappings

```python
custom_mappings = {DiagnosisCode.WRONG_NOTE: custom_action_mapping}
evaluation = attach_recommendations(evaluation, mappings=custom_mappings)
```

## Invariants

### INV-1: Order matches findings

```python
assert len(evaluation.recommendations) == len(evaluation.findings)
for i, rec_set in enumerate(evaluation.recommendations):
    assert rec_set.finding_code == evaluation.findings[i].code or evaluation.findings[i].code is None
```

### INV-2: No recommendation mutation

```python
original = evaluation.model_copy()
enhanced = attach_recommendations(evaluation)
assert original == evaluation  # Original unchanged
```

### INV-3: Idempotent reattachment

```python
once = attach_recommendations(evaluation)
twice = attach_recommendations(once)
assert once.recommendations == twice.recommendations
```

## Relationship to evaluate_session()

The evaluate_session() function does NOT call attach_recommendations() automatically. This is intentional:

1. **Separation of concerns**: Evaluation produces findings; recommendation interprets them
2. **Optional enrichment**: Not all consumers need recommendations
3. **Custom mappings**: Callers may want to use different mapping registries

If a single-step function is needed, consumers can create their own wrapper:

```python
def evaluate_and_recommend(session, mappings=None):
    return attach_recommendations(evaluate_session(session), mappings)
```

## Serialization

Recommendations serialize as part of CoachEvaluation JSON:

```json
{
  "session_id": "...",
  "findings": [...],
  "recommendations": [
    {
      "finding_code": "WRONG_NOTE",
      "actions": [
        {"action_type": "isolate", "label": "Isolate problem note"},
        {"action_type": "review_reference", "label": "Review expected note"}
      ],
      "source": "action_mapping",
      "confidence": 1.0
    }
  ]
}
```

## Versioning

- The `recommendations` field is optional with `default=None`
- Old evaluations without recommendations deserialize cleanly
- New evaluations can be consumed by old code that ignores the field

## Testing Requirements

Tests must verify:

1. Empty findings → empty recommendations
2. Findings with mapped codes → non-empty recommendations
3. Findings with unmapped codes → empty action sets
4. Order preservation
5. Immutability of input evaluation
6. Custom mappings override defaults
