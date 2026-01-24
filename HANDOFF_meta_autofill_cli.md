# Handoff: `sgc meta-autofill` CLI Subcommand

**Date**: January 23, 2026  
**Author**: AI Assistant (GitHub Copilot)  
**For**: String Master Developer  
**Status**: ✅ Complete — synced to `string_master_v.4.0`

---

## Summary

Added `meta-autofill` as a first-class CLI subcommand to `sg-coach`. This creates missing `vector_meta_v1.json` files in golden vector directories **without rewriting fixtures**.

**Verified working:**
```bash
sgc meta-autofill src/sg_coach/fixtures/golden --dry-run --debug
# Shows 5 vectors missing meta files
```

---

## What Was Changed

### File: `src/sg_coach/cli.py`

1. **Added import**:
   ```python
   from .meta_autofill_v1_2 import autofill_meta
   ```

2. **Added command handler** `cmd_meta_autofill()`:
   - Calls `autofill_meta()` from existing `meta_autofill_v1_2.py`
   - Supports `--dry-run`, `--seed`, `--notes`, `--debug` flags
   - Prints report of scanned/created/skipped vectors

3. **Registered subcommand** in `build_parser()`:
   ```python
   p_m = sub.add_parser("meta-autofill", ...)
   p_m.add_argument("golden_root", ...)
   p_m.add_argument("--seed", type=int, default=123, ...)
   p_m.add_argument("--notes", default="", ...)
   p_m.add_argument("--dry-run", action="store_true", ...)
   p_m.add_argument("--debug", action="store_true", ...)
   p_m.set_defaults(func=cmd_meta_autofill)
   ```

4. **Updated docstring** to list the new command

---

## Usage

```bash
# Preview what would be created
sgc meta-autofill fixtures/golden --dry-run --debug

# Create missing meta files
sgc meta-autofill fixtures/golden --seed 123 --notes "backfilled meta" --debug
```

Equivalent to running:
```bash
python -m sg_coach.meta_autofill_v1_2 fixtures/golden --dry-run --debug
```

---

## ✅ Installation Conflict Resolved

Files synced to `string_master_v.4.0/src/sg_coach/cli.py` — the active Python import location.

---

## Files in This Change

| File | Status |
|------|--------|
| `string_master_v.4.0/src/sg_coach/cli.py` | Modified (active runtime) |
| `Downloads/sg-coach/src/sg_coach/cli.py` | Modified (repo source) |
| `src/sg_coach/meta_autofill_v1_2.py` | Existing (unchanged, provides `autofill_meta`) |
| `src/sg_coach/golden_meta_v1_1.py` | Existing (unchanged, provides `META_FILENAME`) |

---

## Testing

```bash
# Verify subcommand is registered
sgc --help

# Test dry-run (use actual fixture path)
sgc meta-autofill src/sg_coach/fixtures/golden --dry-run --debug

# Run tests
pytest tests/ -v
```

---

## Next Step

To create the 5 missing `vector_meta_v1.json` files:
```bash
sgc meta-autofill src/sg_coach/fixtures/golden --seed 123 --notes "backfilled meta"
```
