# Timing Grid Evaluator

## Purpose

Evaluates performed note timing against expected grid timestamps.
Emits `TIMING_GRID_DEVIATION` findings when timing deviation exceeds threshold.

This is the second Layer 1 Coaching Pipeline, alongside `diminished_evaluator`.

## Scope

- Uses already-parsed note/event data
- No raw audio processing
- No MIDI parsing
- No pitch detection
- Compares timestamps only

## Input Contract

```python
evaluate_timing_grid(
    tempo_bpm: float,              # Tempo in BPM
    expected_times: Sequence[float],  # Expected event times (seconds)
    performed_times: Sequence[float], # Performed event times (seconds)
    threshold_ms: float = 40.0,    # Deviation threshold (milliseconds)
) -> TimingGridEvaluation
```

### Via evaluate_session()

```python
evaluate_session(
    session: SessionRecord,
    expected_times: Sequence[float] = None,
    performed_times: Sequence[float] = None,
    timing_threshold_ms: float = 40.0,
) -> CoachEvaluation
```

### Gating

Only runs for exercises tagged with timing patterns:
- `timing_grid`
- `timing_quarter_notes`
- `timing_layer1a`
- `timing/grid`
- `grid_timing`

## Output Example

```python
TimingGridEvaluation(
    tempo_bpm=120.0,
    threshold_ms=40.0,
    events_evaluated=4,
    deviations=[
        TimingDeviation(
            event=TimingEvent(
                index=1,
                expected_time_sec=0.5,
                performed_time_sec=0.56,
                offset_ms=60.0,
                direction="late",
            ),
            threshold_ms=40.0,
        )
    ],
    average_abs_error_ms=25.0,
    max_abs_error_ms=60.0,
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    message="Timing deviation detected: 60.0ms late (threshold: 40ms)...",
)
```

### CoachFinding

```python
CoachFinding(
    type="timing",
    severity=Severity.secondary,  # or .primary if >= 2x threshold
    evidence=FindingEvidence(
        metric="timing_grid_deviation",
        value=60.0,  # max_abs_error_ms
    ),
    interpretation="Timing deviation detected: 60.0ms late...",
)
```

## Detection Logic

1. Pair expected events to performed events in order (v1 simple matching)
2. Compute offset for each pair:
   ```
   offset_ms = (performed_time_sec - expected_time_sec) * 1000
   ```
3. If `abs(offset_ms) > threshold_ms`, record a deviation
4. Track direction: "early" or "late"
5. Compute aggregate stats: `average_abs_error_ms`, `max_abs_error_ms`

## Severity

| Condition | Severity |
|-----------|----------|
| `max_abs_error_ms >= threshold_ms * 2` | `Severity.primary` (error) |
| `max_abs_error_ms >= threshold_ms` | `Severity.secondary` (warning) |
| `max_abs_error_ms < threshold_ms` | No finding |

## Limitations

- v1 uses simple sequential pairing (no reordering)
- Does not handle missing notes or extra notes
- Does not detect tempo drift (accumulating error)
- Requires pre-parsed timestamp data

## Future Extensions

- Smart event matching for missed/extra notes
- Tempo drift detection (`GRID_DRIFT`)
- Per-bar analysis
- Integration with sg-agentd for live feedback
