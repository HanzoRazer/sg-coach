# Learning Aggregation Governance

Sprint 5 Dev Order 4: Aggregation only, no adaptation.

## Purpose

Convert many `LearningSignal` records into aggregated `ActionEffectivenessProfile` records grouped by diagnosis code and action type.

This is the first adaptation primitive, but **does not adapt behavior yet**.

## Aggregation Key

Signals are grouped by:

```
(source_finding_code, action_type)
```

Example:
```
TIMING_GRID_DEVIATION + slow_down → one profile
TIMING_GRID_DEVIATION + repeat   → another profile
```

## Aggregate Fields

Each `ActionEffectivenessProfile` contains:

| Field | Description |
|-------|-------------|
| diagnosis_code | DiagnosisCode for this group |
| action_type | FeedbackActionType for this group |
| average_weight | Mean weight of usable signals |
| signal_count | Total signals in group |
| usable_signal_count | Non-weak signals |
| weak_signal_count | Weak signals (abs < 0.2) |
| confidence | min(1.0, usable_count / 10) |

## Weak Signal Policy

```
Weak signal: abs(weight) < 0.2
```

Default behavior:
- Weak signals **excluded** from average_weight
- Weak signals **counted** in weak_signal_count
- Weak signals **remain visible** in profiles

If all signals are weak:
```
average_weight = 0.0
confidence = 0.0
signal_count = total weak signals
usable_signal_count = 0
```

Core rule:
```
Weak signals should not influence effectiveness,
but they should remain visible.
```

## Confidence Formula

```
confidence = min(1.0, usable_signal_count / 10)
```

| Usable Signals | Confidence |
|----------------|------------|
| 0 | 0.0 |
| 1 | 0.1 |
| 5 | 0.5 |
| 10+ | 1.0 |

Confidence reflects sample size, not correctness.

## No Adaptation Yet

This sprint only produces profiles. It does **not**:
- Reorder recommended actions
- Change action selection
- Persist profiles
- Integrate with curriculum

## Governance Rules

1. Aggregation does not change recommendations
2. Aggregation does not mutate LearningSignals
3. Weak signals are excluded by default
4. Profiles are grouped by DiagnosisCode + FeedbackActionType
5. Confidence reflects sample size, not correctness
6. Storage and persistence are out of scope
7. Per-user/global separation is future work

## Usage

```python
from sg_coach import aggregate_effectiveness
from sg_spec.schemas.user_feedback import LearningSignal

signals: list[LearningSignal] = [...]

# Default: exclude weak signals
result = aggregate_effectiveness(signals)

# Include weak signals in average
result = aggregate_effectiveness(signals, include_weak=True)

for profile in result.profiles:
    print(f"{profile.diagnosis_code} + {profile.action_type}")
    print(f"  avg_weight={profile.average_weight:.2f}")
    print(f"  confidence={profile.confidence:.2f}")
```

## Example

Input:
```python
signals = [
    LearningSignal(
        source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        action_type=FeedbackActionType.slow_down,
        weight=1.0,
        ...
    ),
    LearningSignal(
        source_finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        action_type=FeedbackActionType.slow_down,
        weight=0.8,
        ...
    ),
]
```

Output:
```json
{
  "profiles": [
    {
      "diagnosis_code": "timing_grid_deviation",
      "action_type": "slow_down",
      "average_weight": 0.9,
      "signal_count": 2,
      "usable_signal_count": 2,
      "weak_signal_count": 0,
      "confidence": 0.2
    }
  ],
  "total_signals": 2
}
```

## Definition of Done

- [x] ActionEffectivenessProfile schema exists
- [x] LearningSignalAggregateSet schema exists
- [x] aggregate_effectiveness() works
- [x] Weak signals excluded by default
- [x] Confidence formula implemented
- [x] Tests pass
- [x] Docs committed
- [ ] No adaptive selection added yet
- [ ] No persistence added yet

## Future Integration

### Adaptive Ranking (Future)

```
rank actions by:
score × confidence
```

### Per-User vs Global (Future)

```
Separate user-specific learning from global defaults.
```

### Persistence (Future)

```
Store profiles for retrieval across sessions.
```
