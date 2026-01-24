# CI Gates

> **Tip**: When a gate fails locally, re-run with `--debug` to print diagnostics (CI stays quiet).

## check_contracts_governance.py

Enforces contracts governance (Scenario B):

1. `*.schema.sha256` must be single 64-char lowercase hex line
2. Contract schema/hash changes require `contracts/CHANGELOG.md` update with stems mentioned in ADDED lines
3. After `public_released=true`, `*_v1.schema.*` files are immutable

### Usage

```bash
# From repo root
python scripts/ci/check_contracts_governance.py

# With custom base ref (for PRs)
python scripts/ci/check_contracts_governance.py --base-ref origin/main

# Debug mode
python scripts/ci/check_contracts_governance.py --debug
```
