# Session Playback Governance

Sprint 18: Session playback and inspection data structures.

## Purpose

Session playback transforms static coaching results into inspectable interactive practice review. It provides structured JSON for timeline-based session visualization, enabling users to scrub through their practice session and see findings, assignments, and notes at each point.

## Playback Data Model

### SessionPlaybackData

Top-level container for all playback sections:

```python
class SessionPlaybackData(BaseModel):
    session_id: str
    user_id: Optional[str]
    generated_at: datetime
    duration_ms: int
    timeline_events: list[PlaybackTimelineEvent]
    finding_overlays: list[PlaybackFindingOverlay]
    assignments: list[PlaybackAssignmentReference]
    version: str = "0.1"
```

### Timeline Events

Events are sorted by `timestamp_ms` ascending, then by event type order:
1. note
2. finding
3. assignment
4. marker

Each event has:
- **event_type** — PlaybackEventType (note, finding, assignment, marker)
- **timestamp_ms** — milliseconds from session start
- **label** — human-readable label (max 200 chars)
- **description** — optional detailed description (max 500 chars)
- **finding_id** — linked finding ID for finding events
- **assignment_id** — linked assignment ID for assignment events
- **diagnosis_code** — DiagnosisCode if applicable
- **severity** — Severity level if applicable
- **note** — note name or MIDI number for note events
- **metadata** — additional event metadata

### Finding Overlays

Overlays represent time spans where findings apply, enabling UI to highlight affected regions:

- **finding_id** — matches timeline event finding_id
- **diagnosis_code** — the diagnosis code for this finding
- **severity** — Severity level (primary, secondary, info)
- **start_timestamp_ms** — start of the finding span
- **end_timestamp_ms** — end of the finding span (>= start)
- **label** — human-readable overlay label
- **recommendation_ids** — linked recommendation IDs

Window duration: DEFAULT_FINDING_WINDOW_MS = 2000ms

### Assignment References

Links assignments to their source findings:

- **assignment_id** — matches timeline event assignment_id
- **title** — assignment title
- **diagnosis_code** — the weakness this assignment addresses
- **linked_finding_ids** — IDs of findings linked by diagnosis_code
- **linked_timestamps_ms** — timestamps of linked findings

## Timestamp Derivation

Finding timestamps are extracted using priority:
1. `target_span.start_time_sec` (converted to ms)
2. Default to 0

## ID Generation

Finding IDs are generated as: `playback_finding_{index}_{diagnosis_code_value}`

Example: `playback_finding_0_timing_grid_deviation`

## Governance Rules

1. **Read-only** — Playback must not mutate session, evaluation, or assignments
2. **Sorted timeline** — Events must be sorted by timestamp_ms, then event type
3. **Valid spans** — Overlay end_timestamp_ms must be >= start_timestamp_ms
4. **Clamped overlays** — Overlay end must not exceed session duration
5. **JSON serializable** — All playback data must serialize to JSON
6. **UI-independent** — Playback output is UI-ready but UI-independent
7. **Optional note events** — Note events require MIDI input

## Builder Inputs

```python
def build_session_playback(
    *,
    session: SessionRecord,
    evaluation: CoachEvaluation,
    assignments: Optional[AssembledPracticeAssignmentSet] = None,
    user_id: Optional[str] = None,
    midi_events: Optional[list[MidiNoteEvent]] = None,
) -> SessionPlaybackData
```

## CLI Usage

```bash
sg-coach playback --session session.json --evaluation evaluation.json
sg-coach playback --session session.json --evaluation evaluation.json --assignments assignments.json
sg-coach playback --session session.json --evaluation evaluation.json --user-id user_123 --pretty
```

Output: JSON (default) or pretty-printed JSON (--pretty)

## Future UI Usage

The playback data is designed for interactive timeline rendering:

```json
{
  "session_id": "abc123",
  "duration_ms": 60000,
  "timeline_events": [
    {
      "event_type": "note",
      "timestamp_ms": 500,
      "label": "Note 60",
      "note": "60"
    },
    {
      "event_type": "finding",
      "timestamp_ms": 2000,
      "label": "Timing deviation detected",
      "finding_id": "playback_finding_0_timing_grid_deviation",
      "diagnosis_code": "timing_grid_deviation",
      "severity": "primary"
    }
  ],
  "finding_overlays": [
    {
      "finding_id": "playback_finding_0_timing_grid_deviation",
      "start_timestamp_ms": 2000,
      "end_timestamp_ms": 4000,
      "severity": "primary"
    }
  ]
}
```

A web UI can render this as a scrubber timeline with finding highlights.

## Limitations

- No audio waveform data (MIDI events only)
- No video sync (future)
- No real-time updates (post-session only)
- Note events require MIDI input to be provided
- Legacy findings without diagnosis_code are skipped
