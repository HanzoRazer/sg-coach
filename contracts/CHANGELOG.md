# Contracts Changelog

Schema governance log for sg-coach contract artifacts.

## Format

Each entry includes:
- **Schema file**: Path relative to `contracts/`
- **SHA256**: Hash for integrity verification (`sha256:<hex>`)
- **Status**: `v1-locked` | `draft` | `deprecated`
- **Notes**: Breaking change warnings, migration notes

---

## 2026-01-24

### groove_control_intent_v1.schema.json

- **SHA256**: `sha256:3659ba6528e0b9174b006e7534e716c37be5eedee5ae1669cbe95a355d35cb4f`
- **Status**: `v1-locked`
- **Notes**: Prescriptive control output derived from Groove Profile.
  - Defines Profile → Intent boundary (what vs what-to-do-next)
  - Ephemeral (no learning state leaks)
  - Latency-safe via `horizon_ms` (50–60000ms validity window)
  - Control modes: follow, assist, stabilize, challenge, recover
  - Reason codes for debug/analysis tracing
  - Never export to ToolBox (SG internal contract)

### groove_profile_v1.schema.json

- **SHA256**: `sha256:afa948a4c6e52b0713d2df11a3a948342c9423fd864188a0c99cf753de57f7c4`
- **Status**: `v1-locked`
- **Notes**: Initial release. Groove Layer personality profile for SG-only use.
  - Device-local identity compatible (B2)
  - Append-only `extensions` field for forward compatibility
  - `model` block optional for generator provenance
  - Never export to ToolBox (SG internal contract)

---

## Governance Rules

1. **v1-locked schemas are immutable** — create v2 for breaking changes
2. **SHA256 must match** — CI gate validates hash on PR
3. **Append-only evolution** — use `extensions` for new optional fields
4. **Changelog required** — every schema change needs an entry here
