# src/sg_coach/groove_replay_gate_v1.py
"""
Replay gate for Groove Profile -> Intent golden vectors.

Validates that generate_groove_control_intent_v1() produces byte-identical
output (after normalization) against expected_intent.json fixtures.

Usage:
    # Single vector
    python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors/vector_001_stabilize_soft_drift

    # All vectors
    python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from sg_coach.groove_intent_engine_v1 import generate_groove_control_intent_v1


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    message: str
    failures: Optional[List[str]] = None


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _dump_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _normalize_intent_for_compare(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Golden tests must be stable. Normalize fields that may change even in correct runs.
    If you later decide intent_id/generated_at_utc should be compared, remove these lines.
    """
    out = json.loads(json.dumps(intent))  # deep copy via json
    # These are deterministically generated in our baseline engine, but keep normalization anyway.
    out.pop("intent_id", None)
    out.pop("generated_at_utc", None)
    return out


def replay_vector_dir(vector_dir: Path) -> ReplayResult:
    prof_p = vector_dir / "profile.json"
    exp_p = vector_dir / "expected_intent.json"
    meta_p = vector_dir / "meta.json"

    if not prof_p.exists() or not exp_p.exists():
        return ReplayResult(False, f"Missing required files in {vector_dir}", [str(vector_dir)])

    profile = _load_json(prof_p)
    expected = _load_json(exp_p)
    meta = _load_json(meta_p) if meta_p.exists() else {}

    # Optional: allow horizon_ms override per vector
    horizon_ms = int(meta.get("horizon_ms", expected.get("horizon_ms", 2000)))

    produced = generate_groove_control_intent_v1(profile, horizon_ms=horizon_ms)

    prod_norm = _normalize_intent_for_compare(produced)
    exp_norm = _normalize_intent_for_compare(expected)

    if prod_norm != exp_norm:
        # helpful diff payloads (small and deterministic)
        msg = (
            f"Replay mismatch in {vector_dir.name}\n"
            f"- produced != expected (after normalization)\n"
            f"Tip: open produced/expected JSON and diff.\n"
        )
        # write debug artifacts next to vector dir (ignored by CI if you want)
        (vector_dir / "_produced.intent.json").write_text(_dump_json(produced), encoding="utf-8")
        return ReplayResult(False, msg, [vector_dir.name])

    return ReplayResult(True, f"Replay OK: {vector_dir.name}")


def replay_all(root: Path) -> ReplayResult:
    if not root.exists():
        return ReplayResult(False, f"Vectors root not found: {root}")

    failures: List[str] = []
    vec_dirs = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("vector_")])

    if not vec_dirs:
        return ReplayResult(False, f"No vector_* directories found under {root}")

    for vd in vec_dirs:
        res = replay_vector_dir(vd)
        if not res.ok:
            failures.extend(res.failures or [vd.name])

    if failures:
        return ReplayResult(False, f"{len(failures)} vector(s) failed replay: {failures}", failures)

    return ReplayResult(True, f"All vectors passed ({len(vec_dirs)})")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Replay Groove Profile -> Intent golden vectors"
    )
    ap.add_argument(
        "path",
        help="Vector dir (vector_*) OR vectors root (contains vector_* dirs).",
    )
    args = ap.parse_args()
    p = Path(args.path)

    if p.is_dir() and p.name.startswith("vector_"):
        res = replay_vector_dir(p)
    else:
        res = replay_all(p)

    if res.ok:
        print(f"[groove-replay] PASS: {res.message}")
        return 0
    print(f"[groove-replay] FAIL: {res.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
