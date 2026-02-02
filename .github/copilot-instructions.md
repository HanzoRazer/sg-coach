# AI Agent Instructions for sg-coach

## Project Identity

**Package**: `sg-coach` — Smart Guitar Practice Coach  
**Role**: Mode 1 deterministic evaluation spine + Groove Layer contracts.  
**No LLM required** — all logic is rules-based and templated.

---

## Architecture

### Three-Layer Coaching Contract

```
SessionRecord (facts) → CoachEvaluation (interpretation) → PracticeAssignment (intent)
```

| Layer | Owner | Description |
|-------|-------|-------------|
| `SessionRecord` | Runtime (zt-band) | Immutable facts — what happened |
| `CoachEvaluation` | `coach_policy.py` | Deterministic findings — what it means |
| `PracticeAssignment` | `planner_v0_6.py` | Adaptive intent — what's next |

### Groove Layer Contract (Profile → Intent → Control)

```
GrooveProfileV1 (persistent) → GrooveControlIntentV1 (ephemeral) → MidiControlPlan / ArrangerControlPlan
```

- **Profile**: Rhythmic personality traits (HOW player grooves)
- **Intent**: Prescriptive control output (WHAT system does next), bounded by `horizon_ms`
- **MidiControlPlan**: zt-band adapter output (CC messages, clock mode, humanize settings)
- **ArrangerControlPlan**: Style/density/energy for arranger engine

---

## Source of Truth

**Schemas live in `sg-spec`** — this repo re-exports via thin stubs:
```python
# src/sg_coach/schemas.py, coach_policy.py, planner_v0_6.py, etc.
from sg_spec.ai.coach.schemas import *  # Re-export
```
**Never add logic to stub files** — they exist only for backward compatibility.

**JSON Schema contracts** (v1-locked, immutable):
- `contracts/groove_profile_v1.schema.json` — SHA256 in CHANGELOG
- `contracts/groove_control_intent_v1.schema.json` — SHA256 in CHANGELOG

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `groove_intent_engine_v1.py` | Profile → Intent mapper (deterministic, rule-based) |
| `groove_replay_gate_v1.py` | Golden vector replay with unified diff output |
| `coach_policy.py` | Session → Evaluation (Mode 1 rules) — stub |
| `planner_v0_6.py` | History-aware planner with anti-oscillation — stub |
| `ota_payload.py` | OTA bundle building (manifest, HMAC, zip) — stub |

---

## Developer Workflow

```bash
pip install -e ".[dev]"     # Editable install (requires sg-spec)
pytest                       # ~86 tests
pytest --cov=sg_coach        # With coverage
```

### Debugging with `--debug`

When gates or CLI commands fail, use `--debug` for per-vector scan details:
```bash
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors --debug
```

### Replay Gates

```bash
# Single vector
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors/vector_001_stabilize_soft_drift

# All vectors (13 total)
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors

# Update goldens (requires changelog bump)
python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors --update-golden --bump-changelog "reason"
```

---

## Golden Vector Pattern

Groove vectors in `fixtures/golden/groove_vectors/vector_*/`:
```
vector_001_stabilize_soft_drift/
├── profile.json          # Input: GrooveProfileV1
├── expected_intent.json  # Expected: GrooveControlIntentV1
└── vector_meta_v1.json   # Provenance + ENGINE_IDENTITY
```

**Replay gate enforces byte-identical output** (after JSON normalization with sorted keys).

---

## CI Gates (`scripts/ci/`)

| Gate | Purpose |
|------|---------|
| `check_contracts_governance.py` | SHA256 validation of locked schemas |
| `check_groove_vectors_complete.py` | All vectors have required files |
| `check_groove_replay_determinism.py` | Replay produces identical output |
| `check_sg_coach_vectors_complete.py` | Coach vector completeness |
| `check_sg_coach_replay_determinism.py` | Coach replay determinism |

**Bootstrap sentinel**: `.sg_coach_bootstrap` bypasses gates during setup (forbidden on main/master).

---

## Conventions

- **Imports**: Use `from sg_coach.xxx import ...` (stubs re-export from sg-spec)
- **Pydantic**: `model_config = ConfigDict(extra="forbid")` everywhere
- **Versioned modules**: `planner_v0_6.py` = stable API; create v0.7 for breaking changes
- **Contract hashes**: `sha256:<hex>` format, validated in CI
- **Extensions field**: Only forward-growth space in v1-locked schemas
- **ENGINE_IDENTITY**: `v1+salt:v1` — bump salt only for intentional mapping changes

---

## Critical Invariants

1. **Determinism**: Same inputs → byte-identical outputs (essential for OTA)
2. **v1-locked immutability**: Never modify locked schemas; create v2 instead
3. **Changelog required**: Every schema change needs entry in `contracts/CHANGELOG.md`
4. **Anti-oscillation**: Planner enters commit windows on flip-flop detection

---

## Integration Points

**Consumed by zt-band** (`string_master_v.4.0`):
```python
from sg_coach.groove_intent_engine_v1 import generate_groove_control_intent_v1
from zt_band.adapters import build_midi_control_plan, build_arranger_control_plan

intent = generate_groove_control_intent_v1(profile)
midi_plan = build_midi_control_plan(intent)        # CC messages, clock mode
arranger_plan = build_arranger_control_plan(intent) # style, density, energy
```

**Schema source** (`sg-spec`):
```python
from sg_spec.schemas.groove_layer import GrooveProfileV1, GrooveControlIntentV1
```

---

## Adding New Contracts

1. Create JSON Schema in `contracts/<name>_v1.schema.json`
2. Add SHA256 entry to `contracts/CHANGELOG.md` with status `v1-locked`
3. Create matching Pydantic model in `sg-spec`
4. Add golden vectors in `fixtures/golden/` if mapper exists
5. Wire CI gates for governance and replay
