#!/usr/bin/env python3
"""
sg-coach Vector Completeness Gate

Fails if any tests/golden/vector_* is missing required files.

Default expected files per vector:
  - session.json
  - assignment.json
  - evaluation.json
  - vector_meta_v1.json   (required by v1.2)

Exit codes:
  0 pass
  1 violations
  2 execution error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


REQUIRED_FILES = [
    "session.json",
    "assignment.json",
    "evaluation.json",
    "vector_meta_v1.json",
]

# Bootstrap sentinel: if this file exists at repo root, gate skips when no vectors found
BOOTSTRAP_SENTINEL = ".sg_coach_bootstrap"


@dataclass
class Violation:
    vector: str
    message: str


def _is_vector_dir(p: Path) -> bool:
    return p.is_dir() and p.name.startswith("vector_")


def _load_json(fp: Path) -> None:
    # Gate only checks parseability; semantic checks belong to replay gate.
    json.loads(fp.read_text(encoding="utf-8"))


def check_vectors(golden_root: Path, repo_root: Path, debug: bool = False) -> List[Violation]:
    v: List[Violation] = []
    if not golden_root.exists():
        # Check bootstrap sentinel before failing
        sentinel = repo_root / BOOTSTRAP_SENTINEL
        if sentinel.exists():
            print(f"[vectors] SKIP: golden root not found, bootstrap sentinel present ({BOOTSTRAP_SENTINEL})")
            return []
        return [Violation("<root>", f"Golden root not found: {golden_root}")]

    vector_dirs = sorted([p for p in golden_root.iterdir() if _is_vector_dir(p)])
    if not vector_dirs:
        # Check bootstrap sentinel before failing
        sentinel = repo_root / BOOTSTRAP_SENTINEL
        if sentinel.exists():
            print(f"[vectors] SKIP: no vectors yet, bootstrap sentinel present ({BOOTSTRAP_SENTINEL})")
            return []
        return [Violation("<root>", f"No vector_* directories found (create fixtures or add {BOOTSTRAP_SENTINEL} to temporarily allow empty)")]

    for vd in vector_dirs:
        missing = [name for name in REQUIRED_FILES if not (vd / name).exists()]
        if missing:
            v.append(Violation(vd.name, f"Missing required files: {', '.join(missing)}"))
            continue

        # Parse check (fast)
        for name in REQUIRED_FILES:
            fp = vd / name
            try:
                _load_json(fp)
            except Exception as e:
                v.append(Violation(vd.name, f"Invalid JSON in {name}: {e}"))
                break

        if debug:
            print(f"[vectors] {vd.name}: OK", file=sys.stderr)

    return v


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_sg_coach_vectors_complete",
        description="sg-coach Vector Completeness Gate",
    )
    ap.add_argument(
        "golden_root",
        nargs="?",
        default="tests/golden",
        help="Path to golden fixtures (contains vector_* dirs). Default: tests/golden",
    )
    ap.add_argument("--repo-root", default=".", help="Repo root for bootstrap sentinel check. Default: .")
    ap.add_argument("--debug", action="store_true", help="Print per-vector status")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()

    # Guard: bootstrap sentinel must never exist on main/master
    branch = os.environ.get("GITHUB_REF_NAME", "")
    sentinel = repo_root / BOOTSTRAP_SENTINEL
    if branch in ("main", "master") and sentinel.exists():
        print(f"[vectors] FAIL: {BOOTSTRAP_SENTINEL} must never be present on {branch}", file=sys.stderr)
        return 1

    try:
        violations = check_vectors(Path(args.golden_root), repo_root=repo_root, debug=args.debug)
    except Exception as e:
        print(f"[vectors] ERROR: {e}", file=sys.stderr)
        return 2

    if not violations:
        print("[vectors] PASS")
        return 0

    print(f"[vectors] FAIL ({len(violations)} violations)", file=sys.stderr)
    for vi in violations:
        print(f"  - {vi.vector}: {vi.message}", file=sys.stderr)

    print("\n[vectors] Hint: run with --debug for per-vector status.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
