# AI Agent Instructions for sg-coach

## Project Identity

**Package**: `sg-coach` v1.2.0 — Smart Guitar Practice Coach  
**Role**: Mode 1 deterministic evaluation spine + Groove Layer contracts.  
**No LLM required** — all logic is rules-based and templated.

## Architecture

### Coaching Pipeline

```
SessionRecord (facts) → CoachEvaluation (interpretation) → PracticeAssignment (intent)
```

### Groove Layer Pipeline

```
GrooveProfileV1 (persistent) → GrooveControlIntentV1 (ephemeral) → MidiControlPlan / ArrangerControlPlan
```

## Source of Truth & Stub Pattern

**All schemas and coach logic live in `sg-spec`**. This repo contains only 2 logic files; the other 28 modules are 3-line re-export stubs. **Never add logic to stubs.**

```python
# Exact stub pattern (e.g., src/sg_coach/schemas.py):
# sg_coach.schemas — re-exported from sg_spec.ai.coach.schemas
"""Backward compatibility stub. Use sg_spec.ai.coach.schemas directly."""
from sg_spec.ai.coach.schemas import *
```

**Logic modules** (the only files with real code in this repo):

| Module | Purpose |
|--------|---------|
| `groove_intent_engine_v1.py` | Profile → Intent mapper (`ENGINE_IDENTITY = "v1+salt:v1"`) |
| `groove_replay_gate_v1.py` | Golden vector replay with unified diff output |

## Critical Invariants

1. **Determinism**: Same inputs → byte-identical outputs. No RNG anywhere — uses Knuth hash, hardcoded fallback timestamp `datetime(2026, 1, 24, 10, 30, 0, tzinfo=timezone.utc)`, stable intent IDs (`gci_` + truncated SHA256)
2. **v1-locked immutability**: Never modify `contracts/*.schema.json` — create v2 instead
3. **Changelog required**: Every schema/golden change needs `contracts/CHANGELOG.md` entry
4. **ENGINE_IDENTITY**: `v1+salt:v1` — bump salt only for intentional mapping changes

## Developer Workflow

### Version Gap Warning

Local dev uses Python 3.14, CI uses 3.11. Known friction points:
- Type syntax: `list[str]` works in 3.14, may need `from __future__ import annotations` for 3.11
- Match statements: Full pattern matching in 3.14, limited in 3.11
- Exception groups: 3.11+ only

Run `python3.11 -m pytest` locally before pushing to catch CI failures early.

```bash
pip install -e ".[dev]"     # Editable install (requires sg-spec first)
pytest                       # Full suite (25+ test files)
pytest --cov=sg_coach        # With coverage
```

**OTA bundle CLI**: see `sgc --help` or `README.md` § OTA Commands.

**Pre-PR gates** (run locally):
```bash
python scripts/ci/check_groove_replay_determinism.py
python scripts/ci/check_contracts_governance.py
```

**Replay gate commands:**
```bash
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors           # All 13 vectors
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors --debug    # Debug failures
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors --update-golden --bump-changelog "reason"
```

## Golden Vector Pattern

**Groove vectors** in `fixtures/golden/groove_vectors/vector_NNN_<scenario>/`:
```
vector_001_stabilize_soft_drift/
├── profile.json          # Input: GrooveProfileV1
├── expected_intent.json  # Expected output (intent_id → "gci_IGNORE", generated_at_utc → "IGNORE")
└── meta.json             # ENGINE_IDENTITY + provenance
```

**Coach vectors** in `tests/golden/` (4 files: `input.json`, `expected.json`, `config.json`, `meta.json`).

On mismatch the gate writes `actual_intent.json` + `diff.txt` into the vector dir (auto-cleaned on pass).

## CI Gates (`scripts/ci/`)

| Gate | Purpose |
|------|---------|
| `check_contracts_governance.py` | SHA256 validation of locked schemas + CHANGELOG enforcement |
| `check_groove_vectors_complete.py` | All vectors have required files |
| `check_groove_replay_determinism.py` | Byte-identical replay output |
| `check_sg_coach_vectors_complete.py` | Coach vector completeness |
| `check_sg_coach_replay_determinism.py` | Double-run determinism (runs twice, bitwise-compares stdout/stderr/report.json) |

Exit codes: 0 = pass, 1 = violation, 2 = execution error. Bootstrap sentinel `.sg_coach_bootstrap` bypasses gates during setup (forbidden on main/master).

## Testing Conventions

- **Import from stubs** in tests: `from sg_coach.planner_v0_6 import plan_next_v0_6` (not from `sg_spec` directly)
- **Shared fixtures** in `tests/sgc_fixtures.py` — `make_session_record(bpm=120.0, error_by_step={...})`
- **Test naming**: `test_<module>_<scenario>.py` — one module per file
- **No conftest.py** — simple fixtures via `sgc_fixtures.py`

## Planner Versioning

**Current canonical: `assignment_v0_6.py` / `plan_next_v0_6`**. Legacy stubs (`v0_4`, `v0_5`) retained for rollback compatibility through 2026-Q2. Later versions layer features on v0.6 (not replacements): v0.7 adds commit state reducer, v0.8 adds SQLite store + replay gate, v0.9 adds replay-all, v1.0+ adds fixture generators and meta gates.

## OTA & Key Management

HMAC signing key management is **currently undefined** — tests use hardcoded secrets. No `$SG_OTA_KEY_PATH` env var or key rotation script exists yet. If you need signed OTA bundles in production, this needs design work first.

## Conventions

- **Build**: Hatchling (not setuptools), Python ≥3.10, wheel packages only `src/sg_coach`
- **Pydantic**: `model_config = ConfigDict(extra="forbid")` everywhere
- **Contract hashes**: `sha256:<hex>` format in `contracts/CHANGELOG.md`
- **Module runner**: `python -m sg_coach` invokes CLI via `__main__.py`
- **Public API**: `__init__.py` re-exports ~80 symbols — this is the API boundary

## Integration Points

```
sg-spec (schema source of truth) → sg-coach (contracts + engine) → zt-band (MIDI adapters)
```

```python
# Consumed by zt-band:
from sg_coach.groove_intent_engine_v1 import generate_groove_control_intent_v1
intent = generate_groove_control_intent_v1(profile)
```

## Adding New Contracts

1. Create JSON Schema in `contracts/<name>_v1.schema.json`
2. Add SHA256 + entry in `contracts/CHANGELOG.md` with `v1-locked` status
3. Create matching Pydantic model in `sg-spec`
4. Add golden vectors in `fixtures/golden/` if mapper exists
5. Wire CI gates for governance and replay
