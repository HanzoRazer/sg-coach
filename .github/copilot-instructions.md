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

## Source of Truth

**Schemas live in `sg-spec`** at `sg_spec.schemas.*`. This repo contains:
- Layer 1 coaching pipeline (Sprints 1-4)
- Groove Layer contracts

```python
# Canonical import paths:
from sg_spec.schemas.coach_schemas import CoachEvaluation, CoachFinding
from sg_spec.schemas.action_mapping import ActionRecommendationSet
from sg_coach import evaluate_session, attach_recommendations
from sg_coach.schemas import SessionRecord, Severity
```

**Core modules:**

| Module | Purpose |
|--------|---------|
| `coach_policy.py` | `evaluate_session()` — main coaching pipeline |
| `action_recommender.py` | `recommend_actions()` — finding → actions |
| `recommendation_integration.py` | `attach_recommendations()` — attach to evaluation |
| `diminished_evaluator.py` | DIM_ORBIT_VIOLATION detection |
| `timing_evaluator.py` | TIMING_GRID_DEVIATION detection |
| `pitch_evaluator.py` | WRONG_NOTE / PITCH_DEVIATION detection |
| `groove_intent_engine_v1.py` | Profile → Intent mapper |
| `groove_replay_gate_v1.py` | Golden vector replay |

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

- **Import from sg_coach** in tests: `from sg_coach import evaluate_session, attach_recommendations`
- **Import schemas** from `sg_coach.schemas` or `sg_spec.schemas.*`
- **Test naming**: `test_<module>_<scenario>.py` — one module per file
- **conftest.py** sets up path for `shared` module from string_master

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
