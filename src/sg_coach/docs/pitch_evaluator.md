# Pitch Accuracy Evaluator

Layer 1b coaching pipeline for note identity and pitch deviation detection.

## Purpose

Evaluates performed note events against expected note events, emitting:
- **WRONG_NOTE**: When note identity differs (wrong fret, wrong string)
- **PITCH_DEVIATION**: When pitch differs beyond cents threshold (intonation issues)

This module is the coach interpretation layer. It does not parse audio or MIDI — it uses already-parsed event data.

## Scope

**In scope:**
- Single-note sequential comparison
- Note identity matching (MIDI or string-based)
- Pitch deviation detection (cents-based)
- Governance-compliant CoachFinding output

**Out of scope:**
- Audio pitch detection (runtime's job)
- MIDI parsing (runtime's job)
- Chord/polyphonic analysis
- Bend/vibrato detection
- Non-sequential alignment

## Input Contract

Events are `Mapping[str, Any]` with optional fields:

```python
{
    "note": str,        # e.g., "E4", "Eb4"
    "midi": int,        # e.g., 64
    "pitch_hz": float,  # e.g., 329.63
    "index": int,       # optional, for tracking
    "time_sec": float,  # optional, for display
}
```

**Pairing**: Notes are paired sequentially by list index. If lists differ in length, excess notes are ignored.

## Note Identity Matching

Priority order:
1. **MIDI number** — If both events have `midi`, compare directly
2. **Normalized string** — If MIDI unavailable, compare normalized `note` strings

Normalization is conservative:
- Strip whitespace
- Uppercase first letter
- Preserve accidentals and octave exactly

If neither field is available, identity is unknown (no WRONG_NOTE emitted).

## Pitch Deviation Detection

Only runs when:
1. Note identity matches OR is unknown
2. Both events have `pitch_hz`

Formula (standard cents calculation):
```
cents_error = 1200 * log2(performed_hz / expected_hz)
```

- Positive cents = sharp
- Negative cents = flat
- Default threshold: 25 cents

## No Double-Reporting

A single note index never emits both WRONG_NOTE and PITCH_DEVIATION:
- If identity differs → WRONG_NOTE only (skip pitch check)
- If identity matches/unknown AND pitch differs → PITCH_DEVIATION only

## Output Examples

### WRONG_NOTE

```python
CoachFinding(
    code=DiagnosisCode.WRONG_NOTE,
    domain=FeedbackDomain.pitch,
    title="Wrong note",
    message="Expected E4 but played Eb4",
    evidence=FindingEvidence(
        metric="wrong_note",
        expected="E4",
        actual="Eb4",
        index=0,
    ),
    render_hint=FeedbackRenderHint.inline,
    suggested_actions=[
        SuggestedAction(action_type=FeedbackActionType.isolate, ...),
        SuggestedAction(action_type=FeedbackActionType.review_reference, ...),
        SuggestedAction(action_type=FeedbackActionType.retry_section, ...),
    ],
    confidence=1.0,
    source_evaluator="pitch_evaluator",
)
```

### PITCH_DEVIATION

```python
CoachFinding(
    code=DiagnosisCode.PITCH_DEVIATION,
    domain=FeedbackDomain.pitch,
    title="Pitch deviation",
    message="Pitch was 30 cents sharp",
    evidence=FindingEvidence(
        metric="pitch_deviation",
        value=30.0,
        unit="cents",
        threshold=25.0,
        expected=440.0,
        actual=447.69,
        direction="sharp",
        index=0,
    ),
    render_hint=FeedbackRenderHint.timeline,
    suggested_actions=[...],
    confidence=1.0,
    source_evaluator="pitch_evaluator",
)
```

## Exercise Gating

The pitch evaluator only runs for pitch-gated exercises. Detection uses program name patterns:

```python
PITCH_PATTERNS = [
    "pitch_accuracy",
    "pitch_sequence",
    "pitch_layer1b",
    "note_accuracy",
    "single_note_pitch",
]
```

Use `is_pitch_exercise(program_ref)` to check gating.

## Pipeline Integration

Wire through `evaluate_session()`:

```python
result = evaluate_session(
    session,
    expected_pitch_events=[{"note": "E4", "midi": 64}],
    performed_pitch_events=[{"note": "Eb4", "midi": 63}],
    pitch_cents_threshold=25.0,
)
```

## Limitations

1. **No audio pitch detection** — Requires already-parsed events from runtime
2. **No chord/polyphonic** — Single-note sequential pairing only
3. **No bends/vibrato** — Instantaneous pitch comparison, no time-series
4. **Sequential pairing only** — Does not handle inserted/deleted notes
5. **No enharmonic normalization** — "C#4" and "Db4" are different unless MIDI matches

## API

```python
from sg_coach.pitch_evaluator import (
    evaluate_pitch_accuracy,
    DEFAULT_CENTS_THRESHOLD,  # 25.0
)

findings = evaluate_pitch_accuracy(
    expected_notes=[...],
    performed_notes=[...],
    cents_threshold=25.0,
)
```
