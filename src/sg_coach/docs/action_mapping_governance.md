# Action Mapping Governance

Sprint 4: Contract for turning CoachFindings into coaching actions.

## Purpose

ActionMapping governs how CoachFindings become recommended next steps. It defines the stable contract between diagnosis and action, ensuring consistent, structured recommendations that UI can render without parsing text.

## Ownership

| Component | Owner | Responsibility |
|-----------|-------|----------------|
| ActionMapping schemas | sg-spec | Shared contracts |
| Action vocabulary (FeedbackActionType) | sg-spec | Canonical action types |
| Mapping policy | sg-coach | Which actions for which diagnosis |
| Recommendation engine | sg-coach (future) | Applies mappings to findings |
| Drill/exercise content | sg-curriculum (future) | Content for assign_drill |
| Action rendering | UI | Display actions, do not invent them |

## Governance Rules

### 1. Every actionable DiagnosisCode must have an ActionMapping

If a diagnosis code can lead to a coaching action, it must have a documented mapping. Unmapped codes produce no recommendations.

### 2. Recommended actions must use FeedbackActionType

Actions must use the canonical vocabulary:
- `repeat` — Play the section again
- `slow_down` — Reduce tempo
- `isolate` — Focus on specific note/passage
- `retry_section` — Attempt the section again with focus
- `assign_drill` — Recommend a targeted exercise
- `review_reference` — Review expected/correct content

Do not invent action types outside this vocabulary.

### 3. Actions must not be buried only in message text

All actionable information must be in structured `RecommendedAction` objects. UI must not parse `message` or `rationale` strings to extract actions.

**Wrong:**
```python
CoachFinding(
    message="Try slowing down to 80 BPM and isolating bars 3-4"
    # No structured actions
)
```

**Right:**
```python
ActionRecommendationSet(
    actions=[
        RecommendedAction(action_type=slow_down, label="Slow to 80 BPM"),
        RecommendedAction(action_type=isolate, label="Isolate bars 3-4"),
    ]
)
```

### 4. assign_drill actions must set requires_curriculum = true

If an action depends on curriculum content (specific drills, exercises), it must declare this dependency:

```python
RecommendedAction(
    action_type=FeedbackActionType.assign_drill,
    label="Practice diminished orbits",
    requires_curriculum=True,  # Required
)
```

### 5. Actions needing a location must set target_span_required = true

If an action makes no sense without a specific location (bar, beat, note index), declare it:

```python
RecommendedAction(
    action_type=FeedbackActionType.retry_section,
    label="Retry bars 3-4",
    target_span_required=True,  # Required
)
```

### 6. Recommendation engine must preserve source finding code

When generating ActionRecommendationSet, always include the source:

```python
ActionRecommendationSet(
    finding_code=DiagnosisCode.WRONG_NOTE,  # Required
    finding_id="finding-001",  # If available
    source="action_mapping",
    ...
)
```

### 7. UI must render action objects, not parse feedback strings

UI receives structured actions and renders them. UI does not:
- Parse message text to find actions
- Invent actions not in the set
- Modify action labels or types

## Required Initial Mappings

Layer 1 diagnosis codes requiring mappings:

| DiagnosisCode | Domain | Status |
|---------------|--------|--------|
| DIM_ORBIT_VIOLATION | harmony | Required |
| TIMING_GRID_DEVIATION | timing | Required |
| WRONG_NOTE | pitch | Required |
| PITCH_DEVIATION | pitch | Required |

See [action_mapping_examples.md](action_mapping_examples.md) for concrete mapping definitions.

## Action Selection Rules

The recommendation engine uses these rules to select actions from mappings.

### Severity determines action scope

Finding severity controls whether escalation actions are included.

| Severity | Actions Included |
|----------|------------------|
| info | default_actions only |
| warning / secondary | default_actions only |
| error / primary | default_actions + escalation_actions |
| critical | default_actions + escalation_actions |

The engine normalizes both legacy `Severity` and `FeedbackSeverity` internally:
- `Severity.info` → info
- `Severity.secondary` → warning
- `Severity.primary` → error
- `FeedbackSeverity.critical` → critical

### Location determines retry_section eligibility

Actions with `target_span_required=true` are only included if the finding has location info.

Location exists if any of:
- `finding.target_span is not None`
- `finding.evidence.index is not None`
- `finding.evidence.beat is not None`

**Rule:** If action requires target_span but no location exists, omit that action silently. Do not fail the recommendation set.

### Missing mapping behavior

If no ActionMapping exists for a DiagnosisCode:
- Return empty `ActionRecommendationSet`
- Do not crash
- Set `source = "no_mapping"`

### Duplicate action behavior

If multiple findings recommend the same `action_type`:
- Keep both actions
- Do not deduplicate in v1
- UI may choose to collapse duplicates

### Selection pseudocode

```python
def select_actions(finding, mapping):
    if mapping is None:
        return ActionRecommendationSet(
            finding_code=finding.code,
            actions=[],
            source="no_mapping",
        )
    
    severity = normalize_severity(finding.severity)
    has_location = (
        finding.target_span is not None
        or finding.evidence.index is not None
        or finding.evidence.beat is not None
    )
    
    actions = []
    
    # Add default actions
    for action in mapping.default_actions:
        if action.target_span_required and not has_location:
            continue  # Omit, don't fail
        actions.append(action)
    
    # Add escalation actions for severe findings
    if severity in ("error", "critical"):
        for action in mapping.escalation_actions:
            if action.target_span_required and not has_location:
                continue
            actions.append(action)
    
    return ActionRecommendationSet(
        finding_code=finding.code,
        actions=actions,
        source="action_mapping",
    )
```

## Schema Reference

### RecommendedAction

```python
RecommendedAction(
    action_type: FeedbackActionType,
    label: str,                      # 1-80 chars
    rationale: str | None = None,    # max 240 chars
    priority: int = 0,               # 0-10, higher = more important
    params: dict = {},               # action-specific parameters
    target_span_required: bool = False,
    requires_curriculum: bool = False,
)
```

### ActionMapping

```python
ActionMapping(
    diagnosis_code: DiagnosisCode,
    domain: FeedbackDomain,
    default_actions: list[RecommendedAction],  # min 1
    escalation_actions: list[RecommendedAction] = [],
    prerequisites: list[str] = [],
    version: str = "0.1",            # per-mapping version
)
```

### ActionRecommendationSet

```python
ActionRecommendationSet(
    finding_code: DiagnosisCode,
    finding_id: str | None = None,
    actions: list[RecommendedAction] = [],
    source: str = "action_mapping",
    confidence: float = 1.0,
    version: str = "0.1",
)
```

## Versioning

- `version` on ActionMapping is per-mapping version
- Tracks evolution of that specific diagnosis-to-action policy
- Schema version is tracked separately in module/docs
