# Pedagogical Evidence Ledger Governance

Sprint 29: Pedagogical Evidence Ledger

## Purpose

The Pedagogical Evidence Ledger unifies all pedagogical evidence from multiple sources into a single, deterministic, append-only structure. It stores evidence, not conclusions. Entries are append-only and never mutated; corrections occur through additional entries.

## Core Rules

1. **Append-only**: Entries are never modified or deleted
2. **Evidence, not conclusions**: The ledger stores raw evidence; interpretation happens downstream
3. **Source-neutral IDs**: Evidence IDs use format `ped_<12hex>`, independent of source
4. **Provenance tracking**: Each entry includes `source:actual_id` provenance
5. **Deterministic output**: Same inputs always produce same outputs

## Evidence Sources

| Source | Provenance Format | Severity Mapping |
|--------|-------------------|------------------|
| runtime_review | `runtime_review:{runtime_session_id}` | From finding severity |
| longitudinal_review | `longitudinal_review:{runtime_session_id}` | From trend status |
| queue_event | `queue_event:{event_id}` | From event type |
| teacher_review | `teacher_review:{review_id}` | `informational` |
| assignment_outcome | `assignment_outcome:{event_id}` | From outcome status |
| practice_assignment | `practice_assignment:{assignment_id}` | `informational` |
| curriculum_recommendation | `curriculum_recommendation:{diagnosis_code}:{content_id}` | `informational` |

## Severity Mapping

| Status/Type | Severity |
|------------|----------|
| abandoned, worsening | `critical` |
| repeated, deferred, stable | `warning` |
| completed, improved | `informational` |

## Timestamp Normalization

When source artifacts lack canonical timestamps:
- Use source timestamp if available
- Otherwise use `datetime.now(timezone.utc)` at conversion time

**Governance rule**: Ledger normalization may generate deterministic evidence-layer metadata, but must never mutate the source artifact itself.

## Store Behavior

The `PedagogicalLedgerStore` persists entries as JSONL (one JSON object per line):
- `append_entry()` / `append_entries()` — add entries atomically
- `list_entries()` — returns entries sorted by timestamp ascending
- `load_ledger()` — rebuilds ledger from stored entries
- `build_summary()` — generates counts by source and diagnosis

## CLI Commands

```bash
# Build ledger from sources
sg-coach ledger build \
  --runtime-reviews reviews.json \
  --queue-events events.json \
  --teacher-reviews teacher.json \
  --student-id student_123 \
  --pretty

# Generate summary from ledger
sg-coach ledger summary \
  --ledger ledger.json \
  --pretty
```

Input format is auto-detected: JSON array (`[...]`) or NDJSON (one object per line).

## Schema Exports

From `sg_spec.schemas.pedagogical_ledger`:
- `PedagogicalEvidenceSource` — enum of 7 source types
- `PedagogicalEvidenceSeverity` — informational | warning | critical
- `PedagogicalEvidenceEntry` — single evidence entry
- `PedagogicalEvidenceLedger` — collection with student_id and generated_at
- `PedagogicalEvidenceSummary` — counts by source and diagnosis

From `sg_coach`:
- `ledger_entries_from_runtime_review(report)` — one entry per finding
- `ledger_entries_from_longitudinal_review(review)` — one per trend + outcome trajectory
- `ledger_entry_from_queue_event(event)` — single entry
- `ledger_entries_from_teacher_review(review)` — one per annotation/recommendation
- `ledger_entry_from_assignment_outcome(event)` — single entry
- `ledger_entry_from_practice_assignment(assignment)` — single entry
- `ledger_entry_from_curriculum_recommendation(recommendation)` — single entry
- `build_pedagogical_evidence_ledger(...)` — merges all sources, sorts by timestamp
- `build_pedagogical_evidence_summary(ledger)` — counts by source and diagnosis
- `PedagogicalLedgerStore` — append-only JSONL persistence
