# Action Mapping Examples

Sprint 4: Concrete mappings for Layer 1 diagnosis codes.

## DIM_ORBIT_VIOLATION

Played note outside the expected diminished orbit.

### JSON

```json
{
  "diagnosis_code": "dim_orbit_violation",
  "domain": "harmony",
  "default_actions": [
    {
      "action_type": "isolate",
      "label": "Isolate orbit note",
      "rationale": "Focus on the note that fell outside the diminished orbit",
      "priority": 1,
      "target_span_required": true
    },
    {
      "action_type": "review_reference",
      "label": "Review diminished orbit",
      "rationale": "The diminished orbit contains B, D, F, Ab (for key C)",
      "priority": 2
    }
  ],
  "escalation_actions": [
    {
      "action_type": "assign_drill",
      "label": "Practice diminished patterns",
      "rationale": "Build familiarity with symmetric diminished structures",
      "requires_curriculum": true
    }
  ],
  "version": "0.1"
}
```

### Python

```python
ActionMapping(
    diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    domain=FeedbackDomain.harmony,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate orbit note",
            rationale="Focus on the note that fell outside the diminished orbit",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Review diminished orbit",
            rationale="The diminished orbit contains B, D, F, Ab (for key C)",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Practice diminished patterns",
            rationale="Build familiarity with symmetric diminished structures",
            requires_curriculum=True,
        ),
    ],
    version="0.1",
)
```

---

## TIMING_GRID_DEVIATION

Note played too early or late relative to the timing grid.

### JSON

```json
{
  "diagnosis_code": "timing_grid_deviation",
  "domain": "timing",
  "default_actions": [
    {
      "action_type": "slow_down",
      "label": "Reduce tempo",
      "rationale": "Slower tempo allows more precise placement",
      "priority": 1,
      "params": {"tempo_reduction_pct": 10}
    },
    {
      "action_type": "repeat",
      "label": "Repeat with metronome",
      "rationale": "Lock in to the grid with audible reference",
      "priority": 2
    }
  ],
  "escalation_actions": [
    {
      "action_type": "retry_section",
      "label": "Retry problem bars",
      "rationale": "Focus on the specific passage with timing issues",
      "target_span_required": true
    }
  ],
  "version": "0.1"
}
```

### Python

```python
ActionMapping(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    domain=FeedbackDomain.timing,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.slow_down,
            label="Reduce tempo",
            rationale="Slower tempo allows more precise placement",
            priority=1,
            params={"tempo_reduction_pct": 10},
        ),
        RecommendedAction(
            action_type=FeedbackActionType.repeat,
            label="Repeat with metronome",
            rationale="Lock in to the grid with audible reference",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.retry_section,
            label="Retry problem bars",
            rationale="Focus on the specific passage with timing issues",
            target_span_required=True,
        ),
    ],
    version="0.1",
)
```

---

## WRONG_NOTE

Played a different note than expected.

### JSON

```json
{
  "diagnosis_code": "wrong_note",
  "domain": "pitch",
  "default_actions": [
    {
      "action_type": "isolate",
      "label": "Isolate problem note",
      "rationale": "Practice the correct note in isolation",
      "priority": 1,
      "target_span_required": true
    },
    {
      "action_type": "review_reference",
      "label": "Review expected note",
      "rationale": "Confirm the correct note before retrying",
      "priority": 2
    }
  ],
  "escalation_actions": [
    {
      "action_type": "retry_section",
      "label": "Retry passage",
      "rationale": "Play the section again with correct note",
      "target_span_required": true
    }
  ],
  "version": "0.1"
}
```

### Python

```python
ActionMapping(
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    domain=FeedbackDomain.pitch,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate problem note",
            rationale="Practice the correct note in isolation",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Review expected note",
            rationale="Confirm the correct note before retrying",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.retry_section,
            label="Retry passage",
            rationale="Play the section again with correct note",
            target_span_required=True,
        ),
    ],
    version="0.1",
)
```

---

## PITCH_DEVIATION

Correct note but pitch (intonation) is off.

### JSON

```json
{
  "diagnosis_code": "pitch_deviation",
  "domain": "pitch",
  "default_actions": [
    {
      "action_type": "isolate",
      "label": "Isolate pitch",
      "rationale": "Focus on intonation for this specific note",
      "priority": 1,
      "target_span_required": true
    },
    {
      "action_type": "review_reference",
      "label": "Check tuning reference",
      "rationale": "Compare against reference pitch",
      "priority": 2
    }
  ],
  "escalation_actions": [
    {
      "action_type": "repeat",
      "label": "Repeat with pitch focus",
      "rationale": "Play again while listening carefully to intonation"
    }
  ],
  "version": "0.1"
}
```

### Python

```python
ActionMapping(
    diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
    domain=FeedbackDomain.pitch,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate pitch",
            rationale="Focus on intonation for this specific note",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Check tuning reference",
            rationale="Compare against reference pitch",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.repeat,
            label="Repeat with pitch focus",
            rationale="Play again while listening carefully to intonation",
        ),
    ],
    version="0.1",
)
```

---

## Summary Table

| DiagnosisCode | Default Actions | Escalation Actions |
|---------------|-----------------|-------------------|
| DIM_ORBIT_VIOLATION | isolate, review_reference | assign_drill |
| TIMING_GRID_DEVIATION | slow_down, repeat | retry_section |
| WRONG_NOTE | isolate, review_reference | retry_section |
| PITCH_DEVIATION | isolate, review_reference | repeat |

## Notes

- `target_span_required=true` indicates the action needs location context
- `requires_curriculum=true` indicates the action depends on curriculum content
- `priority` determines display order (higher = more prominent)
- `params` holds action-specific configuration (e.g., tempo reduction percentage)
