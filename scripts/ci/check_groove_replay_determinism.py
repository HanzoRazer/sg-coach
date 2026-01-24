#!/usr/bin/env python3
# scripts/ci/check_groove_replay_determinism.py
"""
CI gate: Verify all groove vectors replay deterministically.

Runs generate_groove_control_intent_v1() on each profile.json and compares
(after normalization) against expected_intent.json.

Exit codes:
  0 = All vectors pass
  1 = One or more vectors failed replay
"""
from __future__ import annotations

import sys
from pathlib import Path

from sg_coach.groove_replay_gate_v1 import replay_all


def main() -> int:
    root = Path(__file__).resolve().parents[2] / "fixtures" / "golden" / "groove_vectors"
    res = replay_all(root)
    if res.ok:
        print(f"[groove-replay] PASS: {res.message}")
        return 0
    print(f"[groove-replay] FAIL: {res.message}")
    print("Tip: run locally:")
    print(f"  python -m sg_coach.groove_replay_gate_v1 {root}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
