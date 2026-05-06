# Drill Resolution Governance

Sprint 8: Drill Resolution Contract

## Overview

The drill resolution system maps coaching findings to concrete practice drills. This document defines the contract between `sg_coach.drill_resolver` and consumers.

## Core Principles

1. **Deterministic Resolution**: Same input always produces same output
2. **Copy Safety**: Resolved drills are copies, not catalog originals
3. **Action-Type Scoped**: Only `assign_drill` actions are resolved
4. **Catalog Independence**: Resolver accepts custom catalogs for testing

## Schemas (sg_spec)

### DrillDifficulty

Enum with three levels:
- `beginner` — Foundational exercises
- `intermediate` — Building proficiency
- `advanced` — Performance-level challenges

### DrillReference

Pointer to a curriculum drill:
- `drill_id: str` — Unique identifier (e.g., `timing_grid_quarter_note_reset_v1`)
- `title: str` — Human-readable name
- `source: str` — Origin system (default: `sg-coach`)
- `description: str | None` — Drill explanation
- `diagnosis_code: DiagnosisCode | None` — Primary target finding
- `action_type: FeedbackActionType | None` — Action this drill serves
- `difficulty: DrillDifficulty | None` — Skill level
- `estimated_duration_sec: int | None` — Expected completion time
- `tags: list[str]` — Searchable metadata
- `params: dict[str, Any]` — Drill-specific parameters

### DrillResolutionRequest

Input to resolver:
- `diagnosis_code: DiagnosisCode` — Finding to address
- `action_type: FeedbackActionType` — Action type requested
- `user_id: str | None` — For personalization (future)
- `session_id: str | None` — Session context
- `instrument_id: str | None` — Instrument context
- `target_span: TargetSpan | None` — Time range of finding
- `context: dict[str, Any]` — Additional context
- `preferred_difficulty: DrillDifficulty | None` — User preference

### DrillResolutionResult

Output from resolver:
- `resolved: bool` — Whether resolution succeeded
- `request: DrillResolutionRequest` — Original request
- `drill: DrillReference | None` — Resolved drill (if successful)
- `reason: str | None` — Failure reason (if unsuccessful)
- `source: str` — Resolution source (default: `static_catalog`)
- `confidence: float` — Resolution confidence [0.0, 1.0]

## Resolution Functions

### resolve_drill()

```python
def resolve_drill(
    request: DrillResolutionRequest,
    *,
    catalog: Mapping | None = None,
) -> DrillResolutionResult
```

**Behavior:**
1. Returns `unsupported_action_type` if not `assign_drill`
2. Looks up `(diagnosis_code, action_type)` in catalog
3. Returns `no_matching_drill` if not found
4. Returns deep copy of catalog drill if found

### request_from_recommended_action()

```python
def request_from_recommended_action(
    *,
    diagnosis_code: DiagnosisCode,
    action: RecommendedAction,
    user_id: str | None = None,
    session_id: str | None = None,
    instrument_id: str | None = None,
    target_span: TargetSpan | None = None,
    context: dict | None = None,
) -> DrillResolutionRequest
```

**Behavior:**
- Converts `RecommendedAction` to `DrillResolutionRequest`
- Copies non-empty `action.params` to `context["action_params"]`
- Merges with provided context

### resolve_drills_for_recommendations()

```python
def resolve_drills_for_recommendations(
    *,
    diagnosis_code: DiagnosisCode,
    recommendations: ActionRecommendationSet,
    user_id: str | None = None,
    session_id: str | None = None,
    instrument_id: str | None = None,
    target_span: TargetSpan | None = None,
    catalog: Mapping | None = None,
) -> list[DrillResolutionResult]
```

**Behavior:**
- Filters to `assign_drill` actions only
- Returns results in original action order
- Skips non-drill actions silently

## Catalog Structure

The default catalog (`DEFAULT_DRILL_CATALOG`) maps:
```python
(DiagnosisCode, FeedbackActionType) -> DrillReference
```

### Layer 1 Mappings

| Diagnosis Code | Action Type | Drill ID |
|---------------|-------------|----------|
| DIM_ORBIT_VIOLATION | assign_drill | diminished_orbit_isolation_v1 |
| TIMING_GRID_DEVIATION | assign_drill | timing_grid_quarter_note_reset_v1 |
| WRONG_NOTE | assign_drill | single_note_reference_recall_v1 |
| PITCH_DEVIATION | assign_drill | pitch_centering_sustain_v1 |

## Failure Modes

| Reason | Meaning |
|--------|---------|
| `unsupported_action_type` | Action is not `assign_drill` |
| `no_matching_drill` | No drill in catalog for this finding |

## Invariants

1. `resolved=True` implies `drill is not None`
2. `resolved=False` implies `reason is not None`
3. Returned drills are independent copies
4. Request is always preserved in result
5. Empty results for no `assign_drill` actions

## Future Extensions

- `sg-curriculum` becomes canonical drill source
- Difficulty-based selection
- User preference matching
- A/B testing of drill variants
