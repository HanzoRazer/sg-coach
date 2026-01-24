# Governance Gates

Tip: When a gate fails locally, re-run with `--debug` to print diagnostics (CI stays quiet).

## Available Gates

| Gate | Script | Purpose |
|------|--------|---------|
| Contracts Governance | `scripts/ci/check_contracts_governance.py` | Enforce changelog, sha256 format, v1 immutability |

## How to Run

```bash
python scripts/ci/check_contracts_governance.py --base-ref origin/main
```

For local debugging on failure:

```bash
python scripts/ci/check_contracts_governance.py --base-ref origin/main --debug
```

## CI Integration

In GitHub Actions, ensure checkout has full history so `origin/main` exists:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```
