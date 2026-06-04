# Frontend State Governance

Sprint 38: Canonical Frontend State Projection.

## Overview

Frontend State Projection provides framework-independent UI state contracts for Smart Guitar session workspaces. The system creates deterministic initial UI states that can be consumed by any frontend implementation without dictating UI behavior policy.

## Purpose

Frontend state enables:

- Framework-independent UI state initialization
- Deterministic pane selection and visibility
- Preserved pane identity from workspace projections
- Navigation state contracts for focus management
- Portable UI state for future frontend implementations

## Core Governance Rules

1. **Frontend state mirrors canonical workspace structure.** Pane identity and visibility derive directly from workspace projections.

2. **Frontend state is framework-independent.** No React, Vue, Angular, or other framework-specific constructs are permitted.

3. **Frontend state must remain deterministic.** Given the same workspace input, the same frontend state must be produced.

4. **Frontend state builders must never mutate workspace projections.** All state is derived; source data remains unchanged.

5. **Pane ordering derives from canonical workspace ordering.** The `order_index` from workspace panes is preserved.

6. **Frontend state does not replace pedagogical evidence.** It is a UI state layer, not a data layer.

7. **Browser/framework concerns are prohibited.** No DOM, events, rendering hints, or platform-specific code.

## Schema Structure

### WorkspaceFrontendState (Top-Level)

```
frontend_state_id: str (wfs_<12hex>)
workspace_id: str | None
generated_at: datetime
pane_states: list[FrontendPaneState]
navigation: WorkspaceNavigationState
notes: list[str] (max 5)
metadata: dict
version: str
```

### FrontendPaneState

```
pane_id: str (matches workspace pane)
visible: bool (default True)
expanded: bool (default True)
selected: bool (default False)
order_index: int (from workspace)
metadata: dict
version: str
```

### WorkspaceNavigationState

```
active_pane_id: str | None
focused_section_id: str | None
selected_evidence_id: str | None
selected_timeline_event_id: str | None
metadata: dict
version: str
```

## ID Format

Frontend State ID: `wfs_<12hex>`

Example: `wfs_a1b2c3d4e5f6`

## Pane State Rules

### Visibility

- All workspace panes are included in `pane_states`
- Hidden workspace panes have `visible = False`
- Visible workspace panes have `visible = True`

### Selection

- Exactly one visible pane has `selected = True`
- The first visible pane (by order_index) is selected
- If no panes are visible, no pane is selected
- Hidden panes are never selected

### Expansion

- All panes start with `expanded = True`
- Expansion state is UI-level, not pedagogical

### Ordering

- Pane states are sorted by `order_index`
- Order derives from workspace layout

## Navigation State Rules

### Active Pane

- `active_pane_id` is set to the selected pane's `pane_id`
- If no pane is selected, `active_pane_id` is `None`

### Focus Fields

- `focused_section_id` starts as `None`
- `selected_evidence_id` starts as `None`
- `selected_timeline_event_id` starts as `None`

These fields are placeholders for runtime navigation; builders do not set them.

## Notes Templates

Frontend state notes follow deterministic templates:

| Condition | Template |
|-----------|----------|
| visible_count > 0 | "Workspace contains {N} visible pane(s)." |
| hidden_count > 0 | "Workspace contains {N} hidden pane(s)." |
| selected_pane exists | "Initial focus: pane {pane_id}." |
| narrative present | "Narrative content is available for review." |
| timeline.total_events > 0 | "Timeline evidence is available for review." |

Notes are limited to 5 entries.

## Builder Functions

### Build Frontend Pane States

```python
from sg_coach import build_frontend_pane_states

pane_states = build_frontend_pane_states(panes=workspace.layout.panes)
```

### Build Workspace Navigation State

```python
from sg_coach import build_workspace_navigation_state

navigation = build_workspace_navigation_state(pane_states=pane_states)
```

### Build Workspace Frontend State

```python
from sg_coach import build_workspace_frontend_state

frontend_state = build_workspace_frontend_state(workspace=workspace)
```

## CLI Usage

```bash
# Build frontend state to stdout
sg-coach workspace frontend-state \
    --workspace workspace.json \
    --pretty

# Build frontend state to file
sg-coach workspace frontend-state \
    --workspace workspace.json \
    --output frontend_state.json \
    --pretty
```

## Output Behavior

- If `--output` provided: Write to file, overwrite if exists
- If `--output` omitted: Print JSON to stdout
- `--pretty` enables indented JSON output

## Limitations

- No framework-specific bindings
- No DOM or browser APIs
- No event handlers or callbacks
- No animation or transition hints
- No responsive layout rules
- No accessibility markup
- No internationalization

## What Frontend State Is NOT

Frontend state is NOT:

- A replacement for workspace projections
- A pedagogical evidence container
- A reactive state management system
- A UI component library
- A CSS/styling specification
- A routing or navigation framework

## Integration Points

- **Input**: SessionWorkspaceProjection
- **Output**: WorkspaceFrontendState (JSON)
- **Consumers**: Frontend applications, UI frameworks, mobile apps

## Future Work

Future governed UI systems may extend this foundation:

- State transitions (requires separate governance)
- Animation hints (requires separate governance)
- Accessibility contracts (requires separate governance)
- Mobile-specific state (requires separate governance)
- Real-time state sync (requires separate governance)

These remain out of scope for Sprint 38.
