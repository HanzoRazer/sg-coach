#!/usr/bin/env python3
# scripts/ci/check_groove_vectors_complete.py
"""
CI gate: Verify all groove vector directories have required files.

Required files per vector:
  - profile.json
  - expected_intent.json
  - meta.json

Exit codes:
  0 = All vectors complete
  1 = Some vectors missing files
  2 = No vectors found or root missing
"""
from __future__ import annotations

import sys
from pathlib import Path


REQUIRED = ["profile.json", "expected_intent.json", "meta.json"]


def main() -> int:
    root = Path(__file__).resolve().parents[2] / "fixtures" / "golden" / "groove_vectors"
    if not root.exists():
        print(f"[vectors-complete] FAIL: missing vectors root: {root}")
        return 2

    vec_dirs = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("vector_")])
    if not vec_dirs:
        print(f"[vectors-complete] FAIL: no vector_* directories in {root}")
        return 2

    failures = []
    for vd in vec_dirs:
        missing = [f for f in REQUIRED if not (vd / f).exists()]
        if missing:
            failures.append((vd.name, missing))

    if failures:
        print("[vectors-complete] FAIL:")
        for name, miss in failures:
            print(f"  - {name}: missing {miss}")
        return 1

    print(f"[vectors-complete] PASS: {len(vec_dirs)} vector(s) complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
