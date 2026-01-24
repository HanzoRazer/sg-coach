"""
v1.2 Meta Gate: Enforcement gates for golden fixture hygiene.

Gates:
- META_REQUIRED: Every vector_* must have vector_meta_v1.json
- FIXTURE_PROVENANCE: Every assignment_v0_6.json must have _fixture with matching generator_version

Usage:
    python -m sg_coach.meta_gate_v1_2 fixtures/golden
    python -m sg_coach.meta_gate_v1_2 fixtures/golden --debug
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .golden_meta_v1_1 import META_FILENAME
from .versioning_v1_2 import CURRENT_GENERATOR_VERSION


@dataclass
class GateFailureV1_2:
    """A single gate violation."""

    code: str
    vector: str
    message: str


def _vector_dirs(golden_root: Path) -> List[Path]:
    return sorted([p for p in golden_root.iterdir() if p.is_dir() and p.name.startswith("vector_")])


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def check_meta_required(golden_root: Path) -> List[GateFailureV1_2]:
    """Gate #1: Every vector_* must have vector_meta_v1.json."""
    failures: List[GateFailureV1_2] = []
    for vd in _vector_dirs(golden_root):
        meta = vd / META_FILENAME
        if not meta.exists():
            failures.append(
                GateFailureV1_2(
                    code="META_REQUIRED",
                    vector=vd.name,
                    message=f"Missing {META_FILENAME}. Create it (seed + notes) before accepting vectors.",
                )
            )
    return failures


def check_fixture_provenance(golden_root: Path) -> List[GateFailureV1_2]:
    """
    Gate #2: Fixture provenance policy.

    Policy:
      - If assignment_v0_6.json exists, it MUST include _fixture
      - _fixture.generator_version MUST match CURRENT_GENERATOR_VERSION exactly
    """
    failures: List[GateFailureV1_2] = []
    for vd in _vector_dirs(golden_root):
        af = vd / "assignment_v0_6.json"
        if not af.exists():
            # Not enforced here (some vectors might be pre-assignment), but you can tighten later.
            continue

        try:
            data = _load_json(af)
        except Exception as e:
            failures.append(
                GateFailureV1_2(
                    code="FIXTURE_JSON_INVALID",
                    vector=vd.name,
                    message=f"assignment_v0_6.json is not valid JSON: {e}",
                )
            )
            continue

        fx = data.get("_fixture", None)
        if not isinstance(fx, dict):
            failures.append(
                GateFailureV1_2(
                    code="FIXTURE_PROVENANCE_MISSING",
                    vector=vd.name,
                    message="assignment_v0_6.json missing _fixture provenance object.",
                )
            )
            continue

        gv = fx.get("generator_version", None)
        if gv != CURRENT_GENERATOR_VERSION:
            failures.append(
                GateFailureV1_2(
                    code="FIXTURE_VERSION_MISMATCH",
                    vector=vd.name,
                    message=f"_fixture.generator_version={gv!r} must equal {CURRENT_GENERATOR_VERSION!r}. "
                            "Regenerate fixtures with golden_update.",
                )
            )

    return failures


def run_gates(golden_root: Path) -> Tuple[bool, List[GateFailureV1_2]]:
    """
    Run all v1.2 gates on a golden root directory.

    Returns:
        (ok, failures): ok is True if all gates pass, failures is list of violations.
    """
    failures: List[GateFailureV1_2] = []
    failures.extend(check_meta_required(golden_root))
    failures.extend(check_fixture_provenance(golden_root))
    return (len(failures) == 0, failures)


def main() -> int:
    """CLI entrypoint for meta gate."""
    ap = argparse.ArgumentParser(
        prog="meta_gate_v1_2",
        description="Enforce golden fixture hygiene: meta required + provenance policy",
    )
    ap.add_argument("golden_root", help="Path to fixtures/golden (contains vector_* dirs)")
    ap.add_argument("--debug", action="store_true", help="Print per-vector scan info (optional)")
    args = ap.parse_args()

    root = Path(args.golden_root)
    ok, failures = run_gates(root)

    if ok:
        print(f"[meta-gate] PASS (generator_version={CURRENT_GENERATOR_VERSION})")
        return 0

    print(f"[meta-gate] FAIL ({len(failures)} violations)", flush=True)
    for f in failures:
        print(f"  - [{f.code}] {f.vector}: {f.message}")

    print(
        "\n[meta-gate] Hint: to create meta + regenerate fixtures locally:\n"
        f"  python -m sg_coach.golden_update_v1_0 {root} --seed 123 --update-golden\n"
    )

    if args.debug:
        print("\n[meta-gate] DEBUG scan:")
        for vd in _vector_dirs(root):
            print(f"  - {vd.name}: meta={'yes' if (vd / META_FILENAME).exists() else 'no'} "
                  f"assignment={'yes' if (vd / 'assignment_v0_6.json').exists() else 'no'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "GateFailureV1_2",
    "check_meta_required",
    "check_fixture_provenance",
    "run_gates",
    "main",
]
