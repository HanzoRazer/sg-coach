"""
v1.0 Golden Update Guard: Controlled fixture regeneration.

Default behavior: goldens are immutable → replay mismatch fails and prints regeneration command.
Explicit behavior: --update-golden (or env var) → writes assignment_v0_6.json fixtures.

Usage:
    # Strict gate (no writes)
    python -m sg_coach.golden_update_v1_0 fixtures/golden --seed 123

    # Regenerate (explicit)
    python -m sg_coach.golden_update_v1_0 fixtures/golden --seed 123 --update-golden

    # Alternate explicit unlock
    SG_COACH_UPDATE_GOLDEN=1 python -m sg_coach.golden_update_v1_0 fixtures/golden --seed 123
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .replay_gate_v0_8 import replay_vector_dir
from .replay_utils_v0_9 import normalize_assignment_for_compare, seeded_utc_iso
from .golden_meta_v1_1 import ensure_vector_meta, read_vector_meta
from .versioning_v1_2 import CURRENT_GENERATOR_VERSION


@dataclass
class GoldenUpdateResultV1_0:
    """Result of golden update operation."""

    ok: bool
    updated: int
    total: int
    failures: List[str]


def _now_utc_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _fixture_provenance(seed: int | None, now_utc: str) -> Dict[str, Any]:
    """
    Provenance stamp stored inside assignment fixture as _fixture (non-functional).
    """
    git_sha = os.getenv("GIT_SHA", "") or os.getenv("SG_AI_GIT_SHA", "") or ""
    return {
        "generator": "sg-coach",
        "generator_version": CURRENT_GENERATOR_VERSION,
        "seed_used": seed,
        "generated_at_utc": now_utc,
        "git_sha": git_sha,
    }


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Dict[str, Any]) -> None:
    p.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _vector_dirs(golden_root: Path) -> List[Path]:
    return sorted([p for p in golden_root.iterdir() if p.is_dir() and p.name.startswith("vector_")])


def _produce_assignment_json(vector_dir: Path, *, seed: int | None) -> Optional[Dict[str, Any]]:
    """
    v1.1:
      - Uses per-vector seed if vector_meta_v1.json exists (overrides CLI seed)
      - Adds _fixture provenance to the written assignment fixture
      - Still normalizes created_at_utc deterministically
    
    Returns None if the vector doesn't have required fixtures to produce an assignment.
    """
    meta = read_vector_meta(vector_dir)
    effective_seed = int(meta.seed) if meta is not None else seed

    expected_path = vector_dir / "assignment_v0_6.json"
    expected = _load_json(expected_path) if expected_path.exists() else {}

    res = replay_vector_dir(vector_dir, db_path=":memory:", seed=effective_seed, print_diff_on_fail=False)

    if res.ok:
        # produced == expected; re-emit expected (but we will stamp provenance on write)
        out = dict(expected)
    else:
        if res.produced is None:
            # Missing required fixtures - can't produce assignment
            return None
        out = dict(res.produced)

    # Ensure deterministic created_at_utc:
    if expected:
        out = normalize_assignment_for_compare(out, expected, seed=effective_seed)
    else:
        # no expected: seed-stamp created_at_utc if provided
        if effective_seed is not None:
            out["created_at_utc"] = out.get("created_at_utc") or seeded_utc_iso(effective_seed)

    # Add/overwrite provenance stamp (non-functional)
    now_utc = _now_utc_iso()
    out["_fixture"] = _fixture_provenance(effective_seed, now_utc)

    return out


def update_goldens(
    golden_root: Path,
    *,
    seed: int | None = None,
    allow_update: bool = False,
) -> GoldenUpdateResultV1_0:
    """
    Golden update guard:
      - If allow_update=False: never writes. Reports mismatches and prints regeneration command.
      - If allow_update=True: writes/overwrites assignment_v0_6.json for any failing vector.

    Note:
      This generator only updates assignment fixtures (v1.0 scope).
    """
    vecs = _vector_dirs(golden_root)
    failures: List[str] = []
    updated = 0

    for vd in vecs:
        # v1.1: use per-vector seed if available
        meta = read_vector_meta(vd)
        effective_seed = int(meta.seed) if meta is not None else seed

        res = replay_vector_dir(vd, db_path=":memory:", seed=effective_seed, print_diff_on_fail=False)
        if res.ok:
            continue

        failures.append(vd.name)
        if not allow_update:
            continue

        # Ensure per-vector meta exists (v1.1)
        now_utc = _now_utc_iso()
        seed_for_meta = seed if seed is not None else 123
        ensure_vector_meta(vd, seed=seed_for_meta, now_utc_iso=now_utc)

        # Generate produced assignment JSON and write expected fixture
        produced = _produce_assignment_json(vd, seed=seed)
        if produced is None:
            # Missing required fixtures - can't update this vector
            continue
        _write_json(vd / "assignment_v0_6.json", produced)
        updated += 1

    ok = (len(failures) == 0) or allow_update
    return GoldenUpdateResultV1_0(ok=ok, updated=updated, total=len(vecs), failures=failures)


def main() -> int:
    """CLI entrypoint for golden update guard."""
    ap = argparse.ArgumentParser(
        prog="golden_update_v1_0",
        description="Golden fixture update guard with explicit regeneration control",
    )
    ap.add_argument("golden_root", help="Path to fixtures/golden (contains vector_* dirs)")
    ap.add_argument("--seed", type=int, default=None, help="Seed for deterministic timestamps (optional)")
    ap.add_argument(
        "--update-golden",
        action="store_true",
        help="WRITE updated golden fixtures (assignment_v0_6.json). Guarded by policy.",
    )
    args = ap.parse_args()

    # Two-key guard: flag OR env var (useful in local dev)
    env_ok = os.getenv("SG_COACH_UPDATE_GOLDEN", "").strip().lower() in ("1", "true", "yes")
    allow_update = bool(args.update_golden or env_ok)

    res = update_goldens(Path(args.golden_root), seed=args.seed, allow_update=allow_update)

    if res.ok and res.updated == 0 and not res.failures:
        print(f"[golden] PASS ({res.total}/{res.total})")
        return 0

    if not allow_update:
        print(f"[golden] FAIL: {len(res.failures)} vector(s) mismatched: {res.failures}")
        print(
            "[golden] To regenerate fixtures locally:\n"
            f"  python -m sg_coach.golden_update_v1_0 {args.golden_root} --seed {args.seed or 123} --update-golden\n"
            "  (or set SG_COACH_UPDATE_GOLDEN=1)\n"
        )
        return 1

    print(f"[golden] UPDATED {res.updated} fixture(s); mismatched vectors were: {res.failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "GoldenUpdateResultV1_0",
    "update_goldens",
    "main",
]
