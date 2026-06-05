# Session Workspace Governance

Sprint 36: Canonical Session Workspace Projection.

## Overview

Session Workspace provides a deterministic composition layer that assembles runtime coaching structures into unified workspace projections for UX consumption. The system combines guided session views, pedagogical narratives, and timeline views into canonical workspace layouts without AI generation or probabilistic composition.

## Core Governance Rules

1. **Workspaces are projection layers only.** Workspace projections do not become canonical evidence, do not mutate source structures, and do not replace structured data.

2. **Source structures remain authoritative.** Workspace projections derive from governed runtime structures: GuidedPracticeSessionView, PedagogicalNarrative, PedagogicalTimelineView.

3. **Workspace composition must remain deterministic.** All pane ordering, visibility, and layout composition derives from explicit rules and mappings. No probabilistic or AI generation.

4. **AI workspace layout generation is prohibited.** No LLM composition, no stochastic pane arrangement, no AI-driven UX decisions in this layer.

5. **Workspace builders must remain inspectable.** Pane ordering and visibility rules must be auditable and predictable.

6. **Workspace projections must never mutate source data.** Read-only transformation from input structures to workspace output.

## Schema Structure

### SessionWorkspaceProjection (Top-Level)

```
workspace_id: str (swp_<12hex>)
student_id: Optional[str]
runtime_session_id: Optional[str]
audience: WorkspaceAudience (student, teacher, mixed)
generated_at: datetime
guided_session: GuidedPracticeSessionView
narrative: Optional[PedagogicalNarrative]
timeline: Optional[PedagogicalTimelineView]
layout: WorkspaceLayout
notes: list[str] (max 5)
metadata: dict
version: str
```

### WorkspaceLayout

```
layout_id: str (swl_<12hex>)
audience: WorkspaceAudience
panes: list[WorkspacePane]
notes: list[str]
metadata: dict
version: str
```

### WorkspacePane

```
pane_id: str (swpane_<12hex>)
pane_type: WorkspacePaneType
title: str
visible: bool
order_index: int
summary: Optional[str]
metadata: dict
version: str
```

## ID Formats

- Workspace: `swp_<12hex>`
- Layout: `swl_<12hex>`
- Pane: `swpane_<12hex>`

## Pane Types and Ordering

| Pane Type | Order Index | Source |
|-----------|-------------|--------|
| assignment | 0 | GuidedPracticeAssignmentView |
| playback | 1 | GuidedPracticePlaybackView |
| adaptive_guidance | 2 | GuidedPracticeAdaptiveView |
| teacher_mediation | 3 | GuidedPracticeTeacherMediationView |
| narrative | 4 | PedagogicalNarrative |
| timeline | 5 | PedagogicalTimelineView |

## Builder Functions

### Build Workspace Panes

```python
from sg_coach import build_workspace_panes

panes = build_workspace_panes(
    guided_session=session_view,       # GuidedPracticeSessionView
    narrative=narrative,               # Optional[PedagogicalNarrative]
    timeline=timeline,                 # Optional[PedagogicalTimelineView]
    audience=WorkspaceAudience.mixed,  # Target audience
)
```

### Build Workspace Layout

```python
from sg_coach import build_workspace_layout

layout = build_workspace_layout(
    panes=panes,                       # list[WorkspacePane]
    audience=WorkspaceAudience.mixed,  # Target audience
)
```

### Build Session Workspace Projection

```python
from sg_coach import build_session_workspace_projection

projection = build_session_workspace_projection(
    guided_session=session_view,       # GuidedPracticeSessionView
    narrative=narrative,               # Optional[PedagogicalNarrative]
    timeline=timeline,                 # Optional[PedagogicalTimelineView]
    audience=WorkspaceAudience.mixed,  # Target audience
)
```

## Pane Visibility Rules

### Assignment Pane
- Visible: `assignment is not None`
- Hidden: No assignment data present

### Playback Pane
- Visible: `playback is not None and playback.playback_available`
- Hidden: No playback data or playback not available

### Adaptive Guidance Pane
- Visible: `adaptive_guidance is not None and adaptive_guidance.recommendation_count > 0`
- Hidden: No recommendations active

### Teacher Mediation Pane
- Visible (teacher/mixed audience): `teacher_mediation is not None and teacher_mediation.mediation_count > 0`
- Hidden (student audience): Always hidden regardless of mediation data
- Hidden: No mediation data present

### Narrative Pane
- Visible: `narrative is not None`
- Hidden: No narrative provided

### Timeline Pane
- Visible: `timeline is not None and timeline.total_events > 0`
- Hidden: No timeline data or no events

## Audience Semantics

### student

Teacher-only panes (teacher_mediation) are always hidden. All other visibility rules apply normally.

### teacher

All panes visible according to their individual visibility rules.

### mixed

Same as teacher — no audience-based hiding except what individual pane rules specify.

## Pane Summary Templates

### Assignment
- No assignment: "No active assignment"
- Active session: "Active practice session: {title}"
- Inactive: "Practice assignment: {title}"

### Playback
- Not available: "Playback not available"
- Available: "Playback available with {count} finding overlays"

### Adaptive Guidance
- No guidance: "No adaptive guidance active"
- Active: "Adaptive guidance active with {count} recommendations"
- With critical: "... ({critical_count} critical)"

### Teacher Mediation
- No mediation: "No teacher mediation"
- Active: "Teacher mediation active with {count} decisions"

### Narrative
- No narrative: "No coaching narrative available"
- Present: "{narrative.title}"

### Timeline
- No events: "No timeline evidence available"
- Has events: "Timeline contains {count} pedagogical events"

## Notes Generation Rules

Notes are generated from visible panes only, maximum 5 notes:

| Condition | Note |
|-----------|------|
| Playback visible | "Playback review is available." |
| Teacher mediation visible | "Teacher mediation pane is active." |
| Narrative visible | "Narrative coaching explanation is available." |
| Timeline visible with events | "Timeline evidence contains recent pedagogical activity." |
| Adaptive guidance with critical | "Critical adaptive guidance requires attention." |

## CLI Usage

```bash
# Build session workspace projection
sg-coach workspace session \
    --session-view session_view.json \
    --narrative narrative.json \
    --timeline timeline.json \
    --audience mixed \
    --pretty
```

## Metadata Population

### Workspace Metadata
- `source_session_view_id`: From guided_session.view_id
- `narrative_id`: From narrative.narrative_id (if provided)
- `timeline_student_id`: From timeline.student_id (if provided)

### Pane Metadata

| Pane Type | Metadata Fields |
|-----------|-----------------|
| assignment | assignment_id |
| playback | runtime_session_id |
| adaptive_guidance | recommendation_count |
| teacher_mediation | mediation_count |
| narrative | narrative_id |
| timeline | total_events |

## Limitations

- No dynamic pane reordering
- No personalized layout preferences
- No multi-column layouts
- No drag-and-drop state
- No pane collapse/expand state
- No frontend rendering

## Future Work

Future governed workspace systems may extend this deterministic foundation:

- User-customizable pane ordering (requires separate governance)
- Multi-column responsive layouts (requires separate governance)
- Pane state persistence (collapse, minimize)
- Workspace templates for different contexts

These remain out of scope for Sprint 36 and require explicit governance approval.

## Integration Points

- **Inputs**: GuidedPracticeSessionView, PedagogicalNarrative, PedagogicalTimelineView
- **Output**: SessionWorkspaceProjection
- **Consumers**: Student practice UX, teacher review UX, coaching dashboards
