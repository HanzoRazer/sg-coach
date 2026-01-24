"""
v0.9 Replay-All: Run every vector_* directory and print summary.

Provides:
- replay_all(): batch replay with per-vector isolation
- CLI entrypoint for self-diagnosing golden vector suites

Usage:
    python -m sg_coach.replay_all_v0_9 fixtures/golden --seed 123
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .replay_gate_v0_8 import replay_vector_dir
from .replay_utils_v0_9 import ReplayDiffV0_9
from .golden_meta_v1_1 import read_vector_meta


@dataclass
class ReplayAllResultV0_9:
    """Summary of replay-all batch run."""

    ok: bool
    total: int
    failed: int
    failures: List[str]


def replay_all(
    golden_root: Path,
    *,
    seed: int | None = None,
    db_dir: Path | None = None,
    print_diffs: bool = False,
) -> ReplayAllResultV0_9:
    """
    Replay every vector_* directory under golden_root.

    - Uses distinct sqlite db file per vector if db_dir provided; else in-memory.
    - Returns a summary and prints concise failure reasons.
    """
    vec_dirs = sorted([p for p in golden_root.iterdir() if p.is_dir() and p.name.startswith("vector_")])

    failures: List[str] = []
    for vd in vec_dirs:
        # v1.1: warn if vector_meta missing
        m = read_vector_meta(vd)
        if m is None:
            print(f"[replay-all] WARN {vd.name}: missing vector_meta_v1.json (seed will come from CLI/default)")

        db_path = ":memory:"
        if db_dir is not None:
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / f"{vd.name}.db")

        res = replay_vector_dir(vd, db_path=db_path, seed=seed, print_diff_on_fail=print_diffs)
        if not res.ok:
            failures.append(vd.name)
            print(f"[replay-all] FAIL {vd.name}: {res.reason}")
            if res.diff_text and not print_diffs:
                # print diff anyway (self-diagnosing default)
                print(res.diff_text)

    total = len(vec_dirs)
    failed = len(failures)
    ok = failed == 0

    if ok:
        print(f"[replay-all] PASS ({total}/{total})")
    else:
        print(f"[replay-all] FAIL ({total - failed}/{total}) failures={failures}")
        print("[replay-all] Hint: to regenerate goldens locally:")
        print("  python -m sg_coach.golden_update_v1_0 <fixtures/golden> --seed 123 --update-golden")

    return ReplayAllResultV0_9(ok=ok, total=total, failed=failed, failures=failures)


def main() -> int:
    """CLI entrypoint for replay-all."""
    ap = argparse.ArgumentParser(
        prog="replay_all_v0_9",
        description="Replay all vector_* directories and print summary",
    )
    ap.add_argument("golden_root", help="Path to fixtures/golden (contains vector_* dirs)")
    ap.add_argument("--seed", type=int, default=None, help="Seed for deterministic timestamps (optional)")
    ap.add_argument("--db-dir", default=None, help="Directory for per-vector sqlite db files (optional)")
    ap.add_argument("--diff", action="store_true", help="Print diffs as they happen")
    args = ap.parse_args()

    db_dir = Path(args.db_dir) if args.db_dir else None
    res = replay_all(Path(args.golden_root), seed=args.seed, db_dir=db_dir, print_diffs=args.diff)
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ReplayAllResultV0_9",
    "replay_all",
    "main",
]
