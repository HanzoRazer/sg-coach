"""
v0.8 Replay Gate: Deterministic replay for golden vector directories.

Updated in v0.9 to return ReplayDiffV0_9 with structured JSON diff.

Provides:
- replay_vector_dir(): Replay a golden vector and return structured diff
- CLI entrypoint for local replay testing

Usage:
    python -m sg_coach.replay_gate_v0_8 fixtures/golden/vector_006 --db :memory:
    python -m sg_coach.replay_gate_v0_8 fixtures/golden/vector_006 --seed 123 --diff
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from .sqlite_store_v0_8 import SQLiteCoachStoreV0_8, SqliteStoreConfigV0_8
from .replay_utils_v0_9 import ReplayDiffV0_9, json_diff, normalize_assignment_for_compare


# Keep legacy type for backward compatibility
@dataclass
class ReplayResultV0_8:
    """Result of a replay operation (legacy, use ReplayDiffV0_9)."""

    ok: bool
    message: str


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def replay_vector_dir(
    vector_dir: Path,
    *,
    db_path: str = ":memory:",
    seed: int | None = None,
    print_diff_on_fail: bool = False,
) -> ReplayDiffV0_9:
    """
    Replay contract:
      vector_dir contains:
        - evaluation.json
        - feedback.json
        - assignment_v0_6.json (expected)
      optional:
        - history_assignments.json
        - history_evaluations.json

    Output:
      ReplayDiffV0_9 with a unified JSON diff on mismatch.
    """
    required = ["evaluation.json", "feedback.json", "assignment_v0_6.json"]
    for name in required:
        if not (vector_dir / name).exists():
            return ReplayDiffV0_9(False, f"Missing required fixture: {name}")

    store = SQLiteCoachStoreV0_8(SqliteStoreConfigV0_8(db_path=db_path))

    try:
        ev = EvaluationV0_3.model_validate(_load_json(vector_dir / "evaluation.json"))
        fb = CoachFeedbackV0.model_validate(_load_json(vector_dir / "feedback.json"))

        store.get_or_create_session(ev.session_id, ev.instrument_id)

        # Seed history (optional) — direct inserts for replay-only use
        ha = vector_dir / "history_assignments.json"
        if ha.exists():
            history = _load_json(ha)
            for item in history:
                store._conn.execute(
                    "INSERT INTO assignments(session_id, instrument_id, created_at_utc, payload_json) VALUES(?,?,?,?)",
                    (
                        ev.session_id,
                        ev.instrument_id,
                        item.get("created_at_utc"),
                        json.dumps(item, separators=(",", ":"), sort_keys=True),
                    ),
                )
            store._conn.commit()

        he = vector_dir / "history_evaluations.json"
        if he.exists():
            for item in _load_json(he):
                store.append_evaluation(EvaluationV0_3.model_validate(item))

        produced = store.next_assignment(ev, fb)
        prod_json = produced.model_dump(mode="json")

        expected = _load_json(vector_dir / "assignment_v0_6.json")
        prod_norm = normalize_assignment_for_compare(prod_json, expected, seed=seed)

        if prod_norm != expected:
            d = json_diff(prod_norm, expected)
            if print_diff_on_fail:
                print(d)
            return ReplayDiffV0_9(
                ok=False,
                reason="Replay mismatch: produced assignment != expected",
                produced=prod_norm,
                expected=expected,
                diff_text=d,
            )

        return ReplayDiffV0_9(ok=True, reason="Replay OK")

    finally:
        store.close()


def main() -> int:
    """CLI entrypoint for replay gate."""
    ap = argparse.ArgumentParser(
        prog="replay_gate_v0_8",
        description="Replay a golden vector directory and verify deterministic output",
    )
    ap.add_argument(
        "vector_dir",
        help="Path to a golden vector directory (e.g., fixtures/golden/vector_006)",
    )
    ap.add_argument(
        "--db", default=":memory:", help="SQLite db path (default: :memory:)"
    )
    ap.add_argument(
        "--seed", type=int, default=None, help="Seed for deterministic timestamps (optional)"
    )
    ap.add_argument(
        "--diff", action="store_true", help="Print unified diff on mismatch"
    )
    args = ap.parse_args()

    res = replay_vector_dir(
        Path(args.vector_dir),
        db_path=args.db,
        seed=args.seed,
        print_diff_on_fail=args.diff,
    )
    if res.ok:
        print(f"[replay] PASS: {res.reason}")
        return 0

    print(f"[replay] FAIL: {res.reason}")
    if res.diff_text and not args.diff:
        print(res.diff_text)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ReplayResultV0_8",
    "ReplayDiffV0_9",
    "replay_vector_dir",
    "main",
]
