# Learning Store Governance

Sprint 6: Persistent memory for LearningSignals.

## Purpose

Make the adaptive system remember what it learns by persisting LearningSignals to durable storage.

```
LearningSignal
→ LearningSignalStore
→ query()
→ aggregate_effectiveness()
→ ActionEffectivenessProfile
```

## Append-Only Rule

```
LearningSignalStore is append-only.
```

- Existing rows are never modified
- Existing rows are never deleted
- Each signal is stored as one JSON line
- New signals are appended to the end

## JSONL Format

Storage uses JSON Lines format:

```jsonl
{"id":"ls_abc123","source_finding_code":"timing_grid_deviation",...}
{"id":"ls_def456","source_finding_code":"wrong_note",...}
```

Benefits:
- Simple and debuggable
- Git-inspectable
- Human-readable
- Easy to migrate to SQLite later

## User vs Global Signals

```
user_id=None means global signal.
```

| Signal Type | user_id | Purpose |
|-------------|---------|---------|
| User-specific | "user_123" | Personal learning history |
| Global | None | System-wide defaults |

## Query Behavior

### Filter Combination

All filters combine with AND logic:

```python
query = LearningSignalQuery(
    user_id="user_123",
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
)
# Returns: signals matching BOTH conditions
```

### include_global Semantics

When `query.user_id` is set:

| include_global | Returns |
|----------------|---------|
| True (default) | user_id matches OR user_id is None |
| False | user_id matches only |

### Limit

`limit` applies after filtering.

## Aggregation Behavior

### aggregate_user_effectiveness()

```
Only signals matching that user_id.
No global blending in v1.
```

Uses `include_global=False` explicitly.

### aggregate_global_effectiveness()

```
Only signals where user_id is None.
```

Does not include any user-specific signals.

## Privacy Notes

- User signals are isolated by user_id
- No cross-user queries in v1
- No user data in global aggregation
- Future: privacy dashboard, data export, deletion

## Concurrency

```
Concurrent writes are out of scope for v1.
```

Assume single-threaded access. Document that concurrent writes may corrupt the file.

## Migration Path to SQLite

When needed:
1. Create SQLite schema matching LearningSignal fields
2. Implement SQLiteLearningSignalStore with same interface
3. Migrate existing JSONL to SQLite
4. Swap store implementation

The LearningSignalStore interface remains stable.

## Governance Rules

1. LearningSignalStore is append-only
2. Stored signals must be traceable to source_event_id when available
3. user_id=None means global signal
4. User-specific aggregation must not silently include other users
5. Global aggregation uses only user_id=None signals in v1
6. No adaptive ranking changes in this sprint
7. No curriculum decisions in this sprint

## Error Handling

```
Invalid JSON raises immediately.
```

Do not skip or log silently in v1. Corrupted storage should be fixed, not ignored.

## Definition of Done

- [x] LearningSignal has optional user/session/instrument context
- [x] LearningSignalStore persists JSONL append-only signals
- [x] Signals can be queried by user/session/code/action
- [x] Global and user aggregation helpers exist
- [x] All tests pass
- [x] Docs committed
- [ ] No adaptive ranking change added
- [ ] No curriculum integration added
- [ ] No agentd wiring added

## Future Integration

### sg-agentd (Future)

```
Decides when to persist signals during runtime.
Manages store lifecycle and paths.
```

### sg-curriculum (Future)

```
Consumes aggregated profiles for personalization.
Blends user + global effectiveness.
```

### Privacy Dashboard (Future)

```
View, export, delete personal learning data.
GDPR compliance features.
```
