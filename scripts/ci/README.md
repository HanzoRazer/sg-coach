# CI Gates Overview

This directory contains **repository-local CI gate scripts** that enforce
architecture boundaries, governance rules, and contract invariants.

All gates are designed to be:

- **Deterministic**
- **Repo-local** (no GitHub API calls, no cross-repo fetches)
- **Fail-fast with actionable errors**
- **Runnable locally** the same way CI runs them

These scripts are authoritative enforcement of the governance documents in
`docs/governance/`.

---

## How CI Gates Are Used

CI gates are invoked from GitHub Actions workflows (usually `core_ci.yml`).

Typical pattern:

```yaml
- name: <GATE_NAME>
  run: python scripts/ci/<gate_script>.py --base-ref origin/main
```

Locally, you can run the same commands directly.

---

## Available CI Gates

### 1. Contracts Governance Gate (Scenario B)

**Script**
```
scripts/ci/check_contracts_governance.py
```

**Purpose**  
Enforces schema governance rules for all files under `contracts/`.

**What it enforces**

- `.schema.sha256` files must:
  - exist for every governed schema
  - contain exactly one line
  - be 64 lowercase hex characters

- Any change to:
  - `contracts/*.schema.json`
  - `contracts/*.schema.sha256`
  
  requires a corresponding change to:
  - `contracts/CHANGELOG.md`

- The CHANGELOG diff must mention each changed contract stem

- If `contracts/CONTRACTS_VERSION.json` has:
  ```json
  { "public_released": true }
  ```
  then:
  - `*_v1.schema.json` is immutable
  - `*_v1.schema.sha256` is immutable

**Run locally**
```bash
python scripts/ci/check_contracts_governance.py \
  --repo-root . \
  --base-ref origin/main
```

**Common failure hint**  
If the gate fails, re-run with:
```bash
python scripts/ci/check_contracts_governance.py --debug
```

---

### 2. Art Studio Scope Gate

**Script**
```
scripts/ci/check_art_studio_scope.py
```

**Purpose**  
Prevents leakage of restricted Art Studio / manufacturing concepts into
non-authorized areas.

**What it enforces**

- No forbidden imports
- No forbidden symbols crossing the Art Studio boundary
- Enforces architectural separation at the code level

**Run locally**
```bash
python scripts/ci/check_art_studio_scope.py --repo-root .
```

---

### 3. Viewer Pack Schema Parity Gate

**Script**
```
scripts/validate/check_viewer_pack_schema_parity.py
```

**Purpose**  
Ensures viewer pack schemas remain in strict parity with their canonical form.

**What it enforces**

- Schema structure parity
- Prevents silent divergence between producer and consumer expectations

**Run locally**
```bash
python scripts/validate/check_viewer_pack_schema_parity.py --mode check
```

---

### 4. Workflow API Base Gate

**Script**
```
scripts/ci/check_workflow_api_base.py
```

**Purpose**  
Ensures workflow APIs are rooted at approved base paths.

**Run locally**
```bash
python scripts/ci/check_workflow_api_base.py
```

---

### 5. Workflow API Paths Gate

**Script**
```
scripts/ci/check_workflow_api_paths.py
```

**Purpose**  
Validates workflow API endpoint paths for consistency and policy compliance.

**Run locally**
```bash
python scripts/ci/check_workflow_api_paths.py
```

---

## Debugging CI Gate Failures

**General guidance:**

1. Re-run the exact command locally
2. Add `--debug` if supported
3. Read the first failure — gates are fail-fast by design
4. Fix intent first (CHANGELOG, schema versioning, boundary)
5. Re-run before pushing

CI gates are intentionally strict.  
If you are fighting a gate, it usually means the design intent is unclear.

---

## Adding a New CI Gate

When adding a new gate:

1. Place the script in `scripts/ci/`
2. Ensure it:
   - exits `0` on success
   - exits `1` on violation
   - exits `2` on execution error
3. Document it in this README
4. Add it to the appropriate workflow

**Gates are policy, not suggestions.**

---

### 6. sg-coach Vector Completeness Gate

**Script**
```
scripts/ci/check_sg_coach_vectors_complete.py
```

**Purpose**  
Ensures every `tests/golden/vector_*` directory contains the required files.

**What it enforces**

- Each vector must contain:
  - `session.json`
  - `assignment.json`
  - `evaluation.json`
  - `vector_meta_v1.json` (required by v1.2)
- All JSON files must be valid JSON

**Run locally**
```bash
python scripts/ci/check_sg_coach_vectors_complete.py tests/golden --debug
```

> **Bootstrap only:** create an empty `.sg_coach_bootstrap` file at repo root to temporarily allow CI to pass with no `vector_*` fixtures; **this file must never be committed to `main`** and should be removed as soon as fixtures exist.

---

### 7. sg-coach Replay Determinism Gate

**Purpose**  
Ensures sg-coach replay is fully deterministic for a fixed seed.  
This gate verifies **both**:

1. CLI output (stdout + stderr) is identical across runs
2. A machine-readable `report.json` produced by replay is identical (normalized JSON)

This prevents "looks fine in logs, but state drifted internally" failures.

---

**Script**
```bash
python scripts/ci/check_sg_coach_replay_determinism.py \
  --repo-root . \
  --fixtures tests/golden \
  --seed 123
```

**Requirements on Replay Command**

The replay entrypoint must:

- Accept a deterministic seed:
  ```
  --seed <int>
  ```

- Emit a JSON report to a provided path:
  ```
  --report-json <path>
  ```

The gate will **fail** if the report file is missing.

**What Is Compared**

| Artifact | Comparison Method |
|----------|-------------------|
| stdout + stderr | Exact string match |
| report.json | Parsed + normalized JSON diff |

Normalization uses:
- `sort_keys=True`
- stable separators
- no ignored fields

**Failure Modes**

| Failure | Meaning | Fix |
|---------|---------|-----|
| CLI output differs | Non-deterministic logic | Seed randomness, remove wall-clock time |
| report differs | Internal state drift | Stabilize ordering, seed timestamps |
| report missing | Replay not wired correctly | Ensure replay writes `--report-json` |

**Debugging**

Re-run locally with debug enabled:

```bash
python scripts/ci/check_sg_coach_replay_determinism.py \
  --fixtures tests/golden \
  --seed 123 \
  --debug
```

The debug mode prints:
- exact replay commands
- temp artifact paths
- captured stdout/stderr locations

**Why This Gate Exists**

This gate guarantees:
- Golden vectors are replayable
- Failures are self-diagnosing
- CI results are trustworthy
- Coaching logic does not drift silently

**If replay is not deterministic, CI must fail.**

---

## Philosophy

These gates exist to ensure:

- Contracts are treated as APIs
- Manufacturing boundaries are never crossed accidentally
- Smart Guitar, ToolBox, and SG-AI remain cleanly separated systems
- Drift is caught before it ships

**If a gate feels annoying, that is usually a sign it is doing its job.**
