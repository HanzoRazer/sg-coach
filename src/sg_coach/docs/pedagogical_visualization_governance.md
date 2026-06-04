# Pedagogical Visualization Governance

Sprint 33: Pedagogical Timeline Visualization Layer

## Overview

Pedagogical Visualization provides a projection-only layer that transforms evidence ledger entries into UI-ready timeline structures. The system is deterministic, read-only, and sources exclusively from the canonical evidence ledger.

## Core Rules

1. **Projection-Only**: No mutation of source data; all functions produce new view objects
2. **Evidence Ledger is Canonical**: All visualization data derives from PedagogicalEvidenceLedger
3. **Deterministic Ordering**: Timeline events sorted by timestamp (asc), severity (desc), event_id (asc)
4. **No AI Summarization**: Notes generated via count-based rules only (max 5 notes)
5. **Unknown Sources Skipped**: Unrecognized ledger sources produce no events (not errors)

## Source-to-EventType Mapping

| Ledger Source | Visualization Event Type |
|---------------|--------------------------|
| `runtime_review` | `runtime_review` |
| `longitudinal_review` | `longitudinal_review` |
| `assignment_outcome` | `assignment_outcome` |
| `queue_event` | `adaptive_scheduling` |
| `practice_assignment` | `adaptive_scheduling` |
| `teacher_scheduling_mediation` | `teacher_mediation` |
| `teacher_review` | `teacher_mediation` |
| `curriculum_progression` | `curriculum_progression` |

## Severity Mapping

| Ledger Severity | Visualization Severity |
|-----------------|------------------------|
| `informational` | `informational` |
| `warning` | `warning` |
| `critical` | `critical` |

## ID Formats

- Timeline Events: `ptv_<12hex>`
- Evidence IDs (from ledger): `ped_<12hex>`

## Deterministic Notes Rules

Notes are generated based on count thresholds (max 5 notes):

1. Empty ledger → "No pedagogical evidence recorded yet."
2. Most common diagnosis → "[code] is the most frequent evidence category."
3. Critical count > 0 → "[N] critical evidence events require review."
4. Teacher mediation count >= 2 → "Teacher mediation appears in multiple evidence events."
5. Assignment outcome count >= 2 → "Assignment outcomes provide repeated evidence for practice response."
6. Curriculum progression count >= 1 → "Curriculum progression evidence is available."

## Usage

### Building a Timeline View

```python
from sg_coach import build_pedagogical_timeline_view
from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceLedger

# Build complete view from ledger
view = build_pedagogical_timeline_view(ledger=ledger)

# With student ID override
view = build_pedagogical_timeline_view(
    ledger=ledger,
    student_id="student_override",
)
```

### Converting Individual Entries

```python
from sg_coach import timeline_event_from_entry

# Convert single entry (returns None for unknown sources)
event = timeline_event_from_entry(entry)
if event is not None:
    process_event(event)
```

### Building Diagnosis Groups

```python
from sg_coach import timeline_events_from_ledger, build_diagnosis_timeline_groups

# Convert ledger to sorted events
events = timeline_events_from_ledger(ledger)

# Group by diagnosis code (sorted by total_events desc)
groups = build_diagnosis_timeline_groups(events)
for group in groups:
    print(f"{group.diagnosis_code}: {group.total_events} events")
```

## CLI Usage

```bash
# Build timeline view from ledger
sg-coach timeline-view --ledger ledger.json

# With student ID override
sg-coach timeline-view --ledger ledger.json --student-id student_123

# Pretty-printed output
sg-coach timeline-view --ledger ledger.json --pretty
```

## Schema Structure

### PedagogicalTimelineEvent

```json
{
  "event_id": "ptv_abc123def456",
  "timestamp": "2026-05-15T12:00:00Z",
  "event_type": "runtime_review",
  "title": "Session Evidence Captured",
  "summary": "Timing analysis identified 3 findings.",
  "severity": "warning",
  "diagnosis_code": "timing_grid_deviation",
  "evidence_id": "ped_xyz789012345",
  "related_ids": ["rr:001", "sess:002"],
  "metadata": {}
}
```

### DiagnosisTimelineGroup

```json
{
  "diagnosis_code": "timing_grid_deviation",
  "total_events": 5,
  "latest_event_at": "2026-05-15T12:00:00Z",
  "events": [...]
}
```

### PedagogicalTimelineView

```json
{
  "student_id": "student_123",
  "total_events": 10,
  "timeline_events": [...],
  "diagnosis_groups": [...],
  "notes": ["timing_grid_deviation is the most frequent evidence category."],
  "generated_at": "2026-05-15T12:00:00Z"
}
```

## Integration Points

- **Input**: PedagogicalEvidenceLedger (from pedagogical_ledger module)
- **Output**: PedagogicalTimelineView, timeline events, diagnosis groups
- **Consumers**: UI rendering, teacher dashboards, student progress views
