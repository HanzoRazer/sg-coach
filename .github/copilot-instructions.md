# AI Agent Instructions for sg-coach

## Project Identity

**Package**: `sg-coach` v1.2.0 — Smart Guitar Practice Coach  
**Role**: Mode 1 deterministic evaluation spine. Consumes session data, produces coaching evaluations and practice assignments.  
**No LLM required** for core functionality; all logic is rules-based and templated.

---

## Architecture: Three-Layer Contract

```
SessionRecord (facts) → CoachEvaluation (interpretation) → PracticeAssignment (intent)
```

| Layer | Owner | Source of Truth |
|-------|-------|-----------------|
| `SessionRecord` | Runtime (zt-band) | What happened — immutable facts |
| `CoachEvaluation` | Coach (`coach_policy.py`) | What it means — deterministic findings |
| `PracticeAssignment` | Planner (`planner_v0_6.py`) | What's next — adaptive intent |

**INVARIANT**: These layers never blur. Each has strict ownership boundaries.

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `schemas.py` | **Single source of truth** for all Pydantic models (Session, Evaluation, Assignment) |
| `coach_policy.py` | Mode 1 evaluator: `SessionRecord → CoachEvaluation` |
| `planner_v0_6.py` | History-aware planner with anti-oscillation logic |
| `sqlite_store_v0_8.py` | Persistent session state (sessions, evaluations, assignments) |
| `ota_payload.py` | OTA bundle building (manifest, HMAC signing, zip packaging) |
| `groove_contracts.py` | Bridge types between Groove Layer and Coach |
| `contract.py` | `COACH_CONTRACT_VERSION` — bump when determinism changes |

---

## Developer Workflow

```bash
pip install -e ".[dev]"     # Editable install with dev deps
pytest                       # Run all tests (fast, ~50 tests)
pytest --cov=sg_coach        # With coverage
```

### CLI Commands

```bash
sg-coach export-bundle --session session.json   # Build envelope
sg-coach ota-bundle --in session.json --out bundle/  # Build OTA folder
sg-coach ota-verify-zip --zip bundle.zip        # Verify integrity
```

---

## Golden Vector Testing Pattern

Golden fixtures in `tests/golden/vector_*/` define deterministic test vectors:

```
vector_006/
├── evaluation.json      # Input: CoachEvaluation
├── feedback.json        # Input: CoachFeedback
├── assignment_v0_6.json # Expected output
└── vector_meta_v1.json  # Provenance + seed
```

**Replay gate** (`replay_gate_v0_8.py`): Replays vectors and diffs against expected output.  
**Update guard** (`golden_update_v1_0.py`): Regenerate only with explicit `--update-golden` or `SG_COACH_UPDATE_GOLDEN=1`.

---

## Conventions

- **Imports**: Use absolute imports from `sg_coach` (e.g., `from sg_coach.schemas import ...`)
- **Pydantic models**: Use `model_config = ConfigDict(extra="forbid")` to reject unknown fields
- **Test fixtures**: Use `sgc_fixtures.py::make_session_record()` for test data
- **Versioned modules**: Files like `planner_v0_6.py` indicate stable API versions; create new versions rather than breaking existing ones

---

## Critical Invariants

1. **Determinism**: Same inputs → same outputs (byte-identical for OTA)
2. **Contract version**: Bump `COACH_CONTRACT_VERSION` only when deterministic behavior changes
3. **SHA256 hashes**: All artifacts use `sha256:<hex>` format (validated in `ProgramRef`)
4. **Anti-oscillation**: Planner detects flip-flop patterns and enters commit windows

---

## Integration with zt-band

sg-coach is **consumed by** the `zt-band` accompaniment engine in `string_master_v.4.0`:
- zt-band produces `SessionRecord` after practice
- sg-coach evaluates and plans next assignment
- OTA bundles are deployed to Smart Guitar firmware

Import pattern in zt-band:
```python
from sg_coach.schemas import SessionRecord, PracticeAssignment
from sg_coach import evaluate_session, plan_assignment
```
