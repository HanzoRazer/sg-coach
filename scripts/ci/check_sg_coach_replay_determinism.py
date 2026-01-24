#!/usr/bin/env python3
"""
sg-coach Replay Determinism Gate (Mode B)

Runs replay twice with the same seed and fails if:
  1) stdout/stderr differ
  2) machine-readable report differs (normalized JSON)
  3) report is missing (replay did not emit it)

Assumptions:
  - The replay entrypoint supports a report output flag OR env var.
  - This gate passes report path via a CLI arg:
        --report-json <path>
    If your CLI uses a different name, edit REPORT_FLAG below.

Exit codes:
  0 pass
  1 violations
  2 execution error
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class RunResult:
    rc: int
    out_path: Path
    err_path: Path
    report_path: Path


def _read(fp: Path) -> str:
    return fp.read_text(encoding="utf-8", errors="replace")


def _run(
    cmd: List[str],
    cwd: Path,
    env: dict,
    out_path: Path,
    err_path: Path,
) -> int:
    with out_path.open("w", encoding="utf-8") as fout, err_path.open("w", encoding="utf-8") as ferr:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=fout,
            stderr=ferr,
            text=True,
        )
    return p.returncode


def _load_and_normalize_json(fp: Path) -> str:
    """
    Normalized JSON string for stable comparisons:
      - parse JSON
      - dump with sort_keys=True and stable separators
    """
    obj = json.loads(fp.read_text(encoding="utf-8"))
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_sg_coach_replay_determinism",
        description="sg-coach Replay Determinism Gate (Mode B: CLI + report.json)",
    )
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument("--fixtures", default="tests/golden", help="Golden fixtures root. Default: tests/golden")
    ap.add_argument("--seed", type=int, default=123, help="Seed for deterministic replay")
    ap.add_argument("--debug", action="store_true", help="Print commands + artifact paths")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    fixtures = (repo_root / args.fixtures).resolve()

    # Check if fixtures exist and have vectors
    if not fixtures.exists():
        print(f"[replay] SKIP: fixtures path not found: {fixtures}", file=sys.stderr)
        print("[replay] PASS (no vectors to replay)")
        return 0

    vector_dirs = [p for p in fixtures.iterdir() if p.is_dir() and p.name.startswith("vector_")]
    if not vector_dirs:
        print("[replay] SKIP: no vector_* directories found", file=sys.stderr)
        print("[replay] PASS (no vectors to replay)")
        return 0

    # ------------------------------------------------------------
    # EDIT THESE TWO LINES ONLY if your CLI differs
    # ------------------------------------------------------------
    # Preferred if you have sgc installed:
    #   BASE_CMD = ["sgc", "replay-all", str(fixtures)]
    # Fallback module form:
    BASE_CMD = [sys.executable, "-m", "sg_coach.replay_gate_v0_8", str(fixtures)]

    # The replay command must accept:
    #   --seed <int>  and  --report-json <path>
    # If your flag differs, change REPORT_FLAG:
    REPORT_FLAG = "--report-json"

    # Extra determinism
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"

    try:
        with tempfile.TemporaryDirectory(prefix="sgc_replay_gate_") as td:
            td_path = Path(td)

            # Run 1 artifacts
            out1 = td_path / "run1.stdout.txt"
            err1 = td_path / "run1.stderr.txt"
            rep1 = td_path / "run1.report.json"

            # Run 2 artifacts
            out2 = td_path / "run2.stdout.txt"
            err2 = td_path / "run2.stderr.txt"
            rep2 = td_path / "run2.report.json"

            cmd1 = [*BASE_CMD, "--seed", str(args.seed), REPORT_FLAG, str(rep1)]
            cmd2 = [*BASE_CMD, "--seed", str(args.seed), REPORT_FLAG, str(rep2)]

            if args.debug:
                print("[replay] cmd1:", " ".join(cmd1), file=sys.stderr)
                print("[replay] cmd2:", " ".join(cmd2), file=sys.stderr)
                print("[replay] fixtures:", fixtures, file=sys.stderr)

            rc1 = _run(cmd1, cwd=repo_root, env=env, out_path=out1, err_path=err1)
            rc2 = _run(cmd2, cwd=repo_root, env=env, out_path=out2, err_path=err2)

            # Both runs must succeed
            if rc1 != 0 or rc2 != 0:
                print("[replay] FAIL: replay command returned non-zero", file=sys.stderr)
                print(f"  run1 rc={rc1}", file=sys.stderr)
                print(f"  run2 rc={rc2}", file=sys.stderr)
                print("\n[replay] stderr run1:\n" + _read(err1), file=sys.stderr)
                print("\n[replay] stderr run2:\n" + _read(err2), file=sys.stderr)
                return 1

            # Report file must exist
            if not rep1.exists() or not rep2.exists():
                print("[replay] FAIL: replay did not emit report.json as required by gate", file=sys.stderr)
                print(f"  expected: {rep1}", file=sys.stderr)
                print(f"  expected: {rep2}", file=sys.stderr)
                print("[replay] Fix: ensure replay_gate_v0_8 writes a JSON report to the path passed via "
                      f"{REPORT_FLAG}.", file=sys.stderr)
                return 1

            # 1) Deterministic CLI output
            s1 = _read(out1) + "\n---STDERR---\n" + _read(err1)
            s2 = _read(out2) + "\n---STDERR---\n" + _read(err2)
            if s1 != s2:
                print("[replay] FAIL: nondeterministic CLI output (run1 != run2)", file=sys.stderr)
                print("[replay] Hint: re-run locally with --debug to capture artifacts.", file=sys.stderr)
                return 1

            # 2) Deterministic report output (normalized JSON)
            n1 = _load_and_normalize_json(rep1)
            n2 = _load_and_normalize_json(rep2)
            if n1 != n2:
                print("[replay] FAIL: nondeterministic report.json (run1 != run2)", file=sys.stderr)
                print("[replay] Hint: ensure timestamps are seedable and report ordering is stable.", file=sys.stderr)
                return 1

            print("[replay] PASS")
            return 0

    except Exception as e:
        print(f"[replay] ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
