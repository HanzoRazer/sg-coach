# Workspace Export Governance

Sprint 37: Workspace Export & Share Package.

## Overview

Workspace Export provides portable, deterministic JSON packages for completed Smart Guitar session workspaces. The system creates snapshot exports that can be archived, inspected, or rendered later without requiring live stores or runtime state.

## Purpose

Export packages enable:

- Offline review of coaching sessions
- Archival of completed practice reviews
- Handoff between systems
- Inspection without live stores
- Future rendering by external UIs

## Core Governance Rules

1. **Export packages are snapshots.** They capture a point-in-time view of workspace state.

2. **Export builders must not mutate source projections.** All exports create copies; original data remains unchanged.

3. **JSON is canonical in v1.** No PDF, HTML, ZIP, or other formats. JSON-first approach ensures portability and inspection.

4. **Redaction must not change pedagogical meaning.** Removing personal identifiers must preserve evidence traceability and learning content.

5. **Export packages are not evidence ledgers.** They are portable review artifacts, not canonical evidence stores.

6. **Signing, compression, and rendering are deferred.** These capabilities require separate governance approval.

## Schema Structure

### WorkspaceExportPackage (Top-Level)

```
manifest: WorkspaceExportManifest
workspace: SessionWorkspaceProjection
narrative: PedagogicalNarrative | None
timeline: PedagogicalTimelineView | None
metadata: dict
version: str
```

### WorkspaceExportManifest

```
export_id: str (wexp_<12hex>)
format: WorkspaceExportFormat (json)
redaction_level: WorkspaceExportRedactionLevel
generated_at: datetime
workspace_id: str | None
student_id: str | None
runtime_session_id: str | None
included_sections: list[str]
artifact_counts: dict[str, int]
metadata: dict
version: str
```

## ID Format

Export ID: `wexp_<12hex>`

Example: `wexp_a1b2c3d4e5f6`

## Included Sections

Sections are listed in deterministic order:

1. `workspace` (always first)
2. `narrative` (if present)
3. `timeline` (if present)
4. Visible workspace pane types in order_index order

Example:
```json
[
  "workspace",
  "narrative",
  "timeline",
  "assignment",
  "playback",
  "adaptive_guidance"
]
```

Duplicates are removed while preserving order.

## Artifact Counts

Standard artifact count keys:

| Key | Description |
|-----|-------------|
| workspace_panes_total | Total number of workspace panes |
| workspace_panes_visible | Number of visible panes |
| workspace_notes | Number of workspace notes |
| narrative_sections | Number of narrative sections |
| narrative_notes | Number of narrative notes |
| timeline_events | Total timeline events |
| diagnosis_groups | Number of diagnosis groups |
| timeline_notes | Number of timeline notes |

If a section is absent, its count is 0.

## Redaction Levels

### none

No changes. All data preserved as-is.

### student_safe

Remove teacher-only information while preserving student-facing content.

Removed metadata keys:
- `teacher_internal_notes`
- `private_teacher_notes`
- `internal_notes`
- `mediation_private_notes`

Preserved:
- Student IDs
- Pedagogical summaries
- Learning content
- Evidence IDs

### anonymized

Remove all personal identifiers.

Set to None:
- `student_id`
- `teacher_id`
- `runtime_session_id`

Removed metadata keys containing:
- `student_id`
- `teacher_id`
- `student_name`
- `teacher_name`
- `email`
- `phone`
- `runtime_session_id`

Preserved:
- Pedagogical IDs (evidence_id, assignment_id, etc.)
- Learning content
- Evidence traceability

## Redaction Implementation

Redaction is applied recursively to:
- Manifest
- Workspace (including nested structures)
- Narrative (including sections)
- Timeline (including events)
- All metadata dictionaries

Redaction uses `model_copy(deep=True)` to ensure source data is never mutated.

## Builder Functions

### Build Export Manifest

```python
from sg_coach import build_workspace_export_manifest

manifest = build_workspace_export_manifest(
    workspace=workspace,
    narrative=narrative,
    timeline=timeline,
    redaction_level=WorkspaceExportRedactionLevel.none,
)
```

### Build Export Package

```python
from sg_coach import build_workspace_export_package

package = build_workspace_export_package(
    workspace=workspace,
    narrative=narrative,
    timeline=timeline,
    redaction_level=WorkspaceExportRedactionLevel.student_safe,
)
```

### Apply Redaction

```python
from sg_coach import redact_workspace_export_package

redacted = redact_workspace_export_package(
    package,
    WorkspaceExportRedactionLevel.anonymized,
)
```

## CLI Usage

```bash
# Export workspace to stdout
sg-coach workspace export \
    --workspace workspace.json \
    --pretty

# Export with narrative and timeline
sg-coach workspace export \
    --workspace workspace.json \
    --narrative narrative.json \
    --timeline timeline.json \
    --pretty

# Export with redaction
sg-coach workspace export \
    --workspace workspace.json \
    --redaction student_safe \
    --pretty

# Export to file
sg-coach workspace export \
    --workspace workspace.json \
    --output export.json \
    --pretty

# Anonymized export
sg-coach workspace export \
    --workspace workspace.json \
    --redaction anonymized \
    --output anonymous_export.json
```

## Output Behavior

- If `--output` provided: Write to file, overwrite if exists
- If `--output` omitted: Print JSON to stdout
- `--pretty` enables indented JSON output

## Limitations

- JSON format only (no PDF, HTML, ZIP)
- No compression
- No cryptographic signing
- No cloud sharing
- No email/notification workflows
- No frontend rendering
- No permissions/authentication

## Future Work

Future governed export systems may extend this foundation:

- PDF export (requires separate governance)
- HTML rendering (requires separate governance)
- ZIP archives with assets (requires separate governance)
- Cloud sharing workflows (requires separate governance)
- Cryptographic signing (requires separate governance)
- Email/share workflows (requires separate governance)

These remain out of scope for Sprint 37.

## Integration Points

- **Inputs**: SessionWorkspaceProjection, PedagogicalNarrative, PedagogicalTimelineView
- **Output**: WorkspaceExportPackage (JSON)
- **Consumers**: External review tools, archive systems, handoff workflows
