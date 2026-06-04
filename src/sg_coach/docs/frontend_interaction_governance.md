# Frontend Interaction Event Governance

Sprint 39: Frontend Interaction Event Contract.

## Overview

Frontend Interaction Events provide the canonical contract for recording and replaying user interaction intents over the frontend state model. The system creates deterministic UI intent logs that can be replayed to reconstruct frontend state without requiring framework-specific browser events.

## Purpose

Interaction events enable:

- Recording UI intent without framework coupling
- Deterministic state replay from event logs
- Append-only interaction history
- Debugging and auditing UI state changes
- Future multi-device sync foundations

## Core Governance Rules

1. **Interaction events describe UI intent only.** They do not render UI or execute framework-specific code.

2. **Interaction events never mutate pedagogical evidence.** They update `WorkspaceFrontendState` only, not `SessionWorkspaceProjection`, `PedagogicalEvidenceLedger`, or any runtime/queue state.

3. **Frontend state updates remain deterministic.** Given the same initial state and event sequence, the same final state must be produced.

4. **Event replay must be reproducible.** Events are applied in order; the result is independent of external factors.

5. **Framework-specific browser events are out of scope.** No DOM events, click handlers, touch events, or rendering hints.

## Schema Structure

### FrontendInteractionType (Enum)

```
select_pane
expand_pane
collapse_pane
select_evidence
select_timeline_event
clear_selection
```

### FrontendInteractionEvent

```
event_id: str (fie_<12hex>)
frontend_state_id: str | None
workspace_id: str | None
interaction_type: FrontendInteractionType
pane_id: str | None
evidence_id: str | None
timeline_event_id: str | None
timestamp: datetime
metadata: dict
version: str
```

## ID Format

Event ID: `fie_<12hex>`

Example: `fie_a1b2c3d4e5f6`

## Interaction Event Semantics

### select_pane

- Sets target pane `selected=True`
- Clears `selected=False` on all other panes
- Updates `navigation.active_pane_id` to target pane
- Requires: `pane_id` field
- Hidden panes cannot be selected (returns warning)

### expand_pane

- Sets target pane `expanded=True`
- Requires: `pane_id` field
- Idempotent if already expanded

### collapse_pane

- Sets target pane `expanded=False`
- Requires: `pane_id` field
- Selected pane may remain selected while collapsed
- Does not clear `active_pane_id`

### select_evidence

- Sets `navigation.selected_evidence_id` to target
- `evidence_id=None` clears selection

### select_timeline_event

- Sets `navigation.selected_timeline_event_id` to target
- `timeline_event_id=None` clears selection

### clear_selection

- Clears `navigation.focused_section_id`
- Clears `navigation.selected_evidence_id`
- Clears `navigation.selected_timeline_event_id`
- Does NOT clear `navigation.active_pane_id`
- Does NOT clear pane `selected` state

## Warning Behavior

When an interaction cannot be applied:

- Return unchanged state
- Add warning to `metadata["interaction_warnings"]` list
- Warnings accumulate across multiple events

Warning format:

```json
{
  "event_id": "fie_...",
  "interaction_type": "select_pane",
  "warning": "pane_id_not_found",
  "target_id": "unknown_pane"
}
```

Warning codes:

| Code | Description |
|------|-------------|
| pane_id_not_found | Target pane does not exist |
| pane_not_visible | Target pane is hidden |
| pane_id_required | pane_id field missing |
| frontend_state_id_mismatch | Event frontend_state_id differs |
| workspace_id_mismatch | Event workspace_id differs |

## ID Mismatch Validation

Soft validation:

- If `event.frontend_state_id` is present and differs from `state.frontend_state_id`: return unchanged with warning
- If `event.workspace_id` is present and differs from `state.workspace_id`: return unchanged with warning
- If either field is `None`: allow event application

## State Identity

- `frontend_state_id` is preserved across event applications
- `generated_at` is updated to the event's timestamp
- Same logical state evolves through events

## Store Behavior

### File Format

- Single JSONL file: `frontend_interactions.jsonl`
- One event per line
- Append-only

### Filtering

- Filter by `workspace_id`
- Filter by `frontend_state_id`
- Filters are optional

### Replay

- `replay_events(initial_state, events)` returns final state
- Events are applied in order
- Initial state is not mutated

## Builder Functions

### Generate Event ID

```python
from sg_coach import generate_event_id

event_id = generate_event_id()
```

### Apply Interaction

```python
from sg_coach import apply_frontend_interaction

new_state = apply_frontend_interaction(
    state=current_state,
    event=interaction_event,
)
```

### Store Operations

```python
from sg_coach import FrontendInteractionStore

store = FrontendInteractionStore(Path("interactions.jsonl"))

store.append_event(event)

events = store.list_events(workspace_id="swp_...")

final_state = store.replay_events(initial_state, events)
```

## CLI Usage

### Apply Single Event

```bash
sg-coach frontend-event apply \
    --state frontend_state.json \
    --event event.json \
    --pretty
```

### Replay Event Log

```bash
sg-coach frontend-event replay \
    --state initial_state.json \
    --events events.jsonl \
    --pretty
```

## Limitations

- No framework-specific event handlers
- No browser DOM events
- No websocket or real-time sync
- No drag/drop interactions
- No persistence beyond JSONL
- No visual rendering
- No animation or transition events

## What Interaction Events Are NOT

Interaction events are NOT:

- Browser DOM events
- React/Vue/Angular event objects
- Real-time sync messages
- State management actions (Redux, MobX)
- Animation keyframes
- Accessibility announcements

## Integration Points

- **Input**: `WorkspaceFrontendState`, `FrontendInteractionEvent`
- **Output**: Updated `WorkspaceFrontendState`, JSONL log
- **Consumers**: Future frontend applications, debugging tools, audit systems

## Future Work

Future governed interaction systems may extend this foundation:

- Drag/drop events (requires separate governance)
- Real-time sync (requires separate governance)
- Undo/redo stack (requires separate governance)
- Multi-device coordination (requires separate governance)
- Gesture events (requires separate governance)

These remain out of scope for Sprint 39.
