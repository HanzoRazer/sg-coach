"""
v1.2 Meta Autofill: Create missing vector_meta_v1.json without touching fixtures.

This is a non-CI utility for backfilling meta files in existing vector directories.
It does NOT rewrite assignment_v0_6.json or any other fixture.

Usage:
    # Preview what would be created
    python -m sg_coach.meta_autofill_v1_2 fixtures/golden --dry-run --debug

    # Create missing meta files
    python -m sg_coach.meta_autofill_v1_2 fixtures/golden --seed 123 --notes "backfilled meta"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .golden_meta_v1_1 import META_FILENAME, ensure_vector_meta


@dataclass
class AutofillReportV1_2:
    """Report from meta autofill operation."""

    scanned: int
    created: int
    skipped: int
    touched_vectors: List[str]


def _now_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _vector_dirs(golden_root: Path) -> List[Path]:
    return sorted([p for p in golden_root.iterdir() if p.is_dir() and p.name.startswith("vector_")])


def autofill_meta(
    golden_root: Path,
    *,
    seed: int = 123,
    notes: str = "",
    dry_run: bool = False,
) -> AutofillReportV1_2:
    """
    Create missing vector_meta_v1.json files only.
    Does NOT rewrite assignment_v0_6.json or any other fixture.
    """
    created = 0
    skipped = 0
    touched: List[str] = []

    now = _now_utc_iso()

    for vd in _vector_dirs(golden_root):
        meta_path = vd / META_FILENAME
        if meta_path.exists():
            skipped += 1
            continue

        touched.append(vd.name)
        if dry_run:
            continue

        # Create meta with provided seed/notes
        ensure_vector_meta(vd, seed=int(seed), now_utc_iso=now, notes=notes)
        created += 1

        # Safety: ensure we didn't accidentally create/modify any fixtures here
        # (This function intentionally never writes assignment files.)

    return AutofillReportV1_2(
        scanned=len(_vector_dirs(golden_root)),
        created=created if not dry_run else 0,
        skipped=skipped,
        touched_vectors=touched,
    )


def main() -> int:
    """CLI entrypoint for meta autofill."""
    ap = argparse.ArgumentParser(
        prog="meta_autofill_v1_2",
        description="Create missing vector_meta_v1.json files without touching fixtures",
    )
    ap.add_argument("golden_root", help="Path to fixtures/golden (contains vector_* dirs)")
    ap.add_argument("--seed", type=int, default=123, help="Default seed to write into new vector meta files")
    ap.add_argument("--notes", default="", help="Optional notes to store in new meta files")
    ap.add_argument("--dry-run", action="store_true", help="Report what would change but do not write")
    ap.add_argument("--debug", action="store_true", help="Print per-vector status")
    args = ap.parse_args()

    root = Path(args.golden_root)
    rep = autofill_meta(root, seed=args.seed, notes=args.notes, dry_run=args.dry_run)

    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(f"[meta-autofill] {mode} scanned={rep.scanned} created={rep.created} skipped={rep.skipped}")

    if rep.touched_vectors:
        print("[meta-autofill] missing meta in:", ", ".join(rep.touched_vectors))

    if args.debug:
        for vd in _vector_dirs(root):
            meta = vd / META_FILENAME
            print(f"  - {vd.name}: meta={'yes' if meta.exists() else 'no'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AutofillReportV1_2",
    "autofill_meta",
    "main",
]
