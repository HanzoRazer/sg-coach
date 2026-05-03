# SessionRecord Normalization

Sprint 3: Canonical evaluator input management.

## Purpose

Move evaluator-specific inputs into `session.normalized` to enable a clean entry point:

```python
evaluate_session(session)  # Preferred
```

Instead of:

```python
evaluate_session(
    session,
    expected_times=...,
    performed_times=...,
    expected_pitch_events=...,
    performed_pitch_events=...,
)
```

## Canonical SessionRecord Shape

```python
SessionRecord(
    session_id=...,
    instrument_id=...,
    engine_version=...,
    program_ref=ProgramRef(...),
    timing=SessionTiming(...),
    duration_s=...,
    performance=PerformanceSummary(...),
    events=SessionEvents(...),
    created_at=...,
    
    # Sprint 3 additions
    key="C",  # Optional, extracted from program_ref if missing
    normalized=NormalizedSessionData(
        harmony=HarmonyEvaluationInput(...),
        timing=TimingEvaluationInput(...),
        pitch=PitchEvaluationInput(...),
    ),
)
```

## NormalizedSessionData

Container for evaluator-specific inputs:

```python
NormalizedSessionData(
    harmony: Optional[HarmonyEvaluationInput] = None,
    timing: Optional[TimingEvaluationInput] = None,
    pitch: Optional[PitchEvaluationInput] = None,
)
```

### HarmonyEvaluationInput

For diminished orbit evaluation:

```python
HarmonyEvaluationInput(
    key: Optional[str] = None,           # Music key
    performed_notes: List[Any] = [],      # Pitch classes (0-11)
    expected_orbit: Optional[List[Any]] = None,  # Explicit orbit (computed if None)
)
```

### TimingEvaluationInput

For timing grid evaluation:

```python
TimingEvaluationInput(
    expected_times: List[float] = [],     # Expected event times (seconds)
    performed_times: List[float] = [],    # Performed event times (seconds)
    threshold_ms: float = 40.0,           # Deviation threshold
)
```

### PitchEvaluationInput

For pitch accuracy evaluation:

```python
PitchEvaluationInput(
    expected_pitch_events: List[Dict[str, Any]] = [],
    performed_pitch_events: List[Dict[str, Any]] = [],
    cents_threshold: float = 25.0,
)
```

## Legacy Compatibility

Legacy parameters still work:

```python
# This still works (backward compatible)
evaluate_session(
    session,
    expected_times=[0.0, 0.5, 1.0],
    performed_times=[0.02, 0.51, 1.03],
)
```

Internally converted to:

```python
session.normalized.timing = TimingEvaluationInput(
    expected_times=[0.0, 0.5, 1.0],
    performed_times=[0.02, 0.51, 1.03],
    threshold_ms=40.0,
)
```

## Precedence Rule

**Existing `session.normalized` wins over legacy params.**

If caller passes both:
```python
evaluate_session(
    session_with_normalized_timing,
    expected_times=[...],  # Ignored
    performed_times=[...], # Ignored
)
```

The normalized data is used, legacy params are ignored.

## Evaluator Input Ownership

| Domain | Input Path | Evaluator |
|--------|------------|-----------|
| Harmony | `session.normalized.harmony` | diminished_evaluator |
| Timing | `session.normalized.timing` | timing_evaluator |
| Pitch | `session.normalized.pitch` | pitch_evaluator |

## Examples

### Preferred: Pre-normalized Session

```python
from sg_coach import (
    evaluate_session,
    SessionRecord,
    NormalizedSessionData,
    TimingEvaluationInput,
)

session = SessionRecord(
    ...,
    normalized=NormalizedSessionData(
        timing=TimingEvaluationInput(
            expected_times=[0.0, 0.5, 1.0],
            performed_times=[0.02, 0.56, 1.01],
            threshold_ms=40.0,
        )
    ),
)

result = evaluate_session(session)
```

### Legacy: Separate Parameters

```python
result = evaluate_session(
    session,
    expected_times=[0.0, 0.5, 1.0],
    performed_times=[0.02, 0.56, 1.01],
    timing_threshold_ms=40.0,
)
```

### Using normalize_session Directly

```python
from sg_coach import normalize_session

session = normalize_session(
    session,
    expected_times=[0.0, 0.5, 1.0],
    performed_times=[0.02, 0.56, 1.01],
)

# Now session.normalized.timing is populated
```

## Migration Rules

1. **New code**: Use `session.normalized` directly
2. **Existing code**: Legacy params continue to work
3. **Mixed**: `session.normalized` wins if present
4. **Immutable**: `normalize_session()` returns a copy, does not mutate

## Utility Functions

```python
from sg_coach import (
    normalize_session,        # Convert legacy params to normalized
    ensure_normalized_session, # Ensure normalized container exists
    has_timing_input,         # Check if timing input is complete
    has_pitch_input,          # Check if pitch input is complete
    has_harmony_input,        # Check if harmony input is complete
)
```

## Limitations

1. **No raw audio/MIDI**: Normalized inputs are already-parsed events
2. **No cross-evaluator dependencies**: Each evaluator reads its own input
3. **No streaming**: Batch evaluation only
4. **Sequential pairing**: No alignment for mismatched event counts
