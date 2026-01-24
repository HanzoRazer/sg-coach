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

    # Update goldens (requires changelog bump)
    python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors --update-golden --bump-changelog "reason"
"""
from __future__ import annotations

import argparse
import difflib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
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


def _stable_json_lines(obj: Dict[str, Any]) -> List[str]:
    """
    Stable, reviewer-friendly representation for diffs.
    - sorted keys
    - 2-space indent
    - newline-terminated
    """
    txt = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return txt.splitlines(keepends=True)


def _write_normalized_diff_txt(
    *,
    vector_dir: Path,
    expected_norm: Dict[str, Any],
    produced_norm: Dict[str, Any],
) -> None:
    """
    Writes a unified diff between normalized expected and normalized produced.
    File: <vector_dir>/_diff.txt

    Header includes:
    - vector name
    - exact command to reproduce locally
    """
    a = _stable_json_lines(expected_norm)
    b = _stable_json_lines(produced_norm)

    diff = difflib.unified_diff(
        a,
        b,
        fromfile="expected_intent.normalized.json",
        tofile="produced_intent.normalized.json",
        lineterm="",
    )

    vector_name = vector_dir.name
    rel_path = f"fixtures/golden/groove_vectors/{vector_name}"

    header = [
        f"# Vector: {vector_name}",
        f"# Reproduce: python -m sg_coach.groove_replay_gate_v1 {rel_path}",
        "",
    ]

    out = "\n".join(header + list(diff)) + "\n"
    (vector_dir / "_diff.txt").write_text(out, encoding="utf-8")


def _cleanup_mismatch_artifacts(vector_dir: Path) -> None:
    """
    Keep vector dirs clean: if a vector passes, remove any old mismatch artifacts.
    """
    for name in ("_diff.txt", "_produced.intent.json"):
        p = vector_dir / name
        try:
            if p.exists():
                p.unlink()
        except Exception:
            # Never fail the gate due to cleanup issues.
            pass

def _deep_copy(obj: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(obj))


def _normalize_intent_for_compare(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Golden tests must be stable. Normalize fields that may change even in correct runs.
    """
    out = _deep_copy(intent)
    out.pop("intent_id", None)
    out.pop("generated_at_utc", None)
    return out


def _canonicalize_expected_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    When writing expected_intent.json, keep the file readable and stable by:
    - replacing intent_id + generated_at_utc with placeholders
    """
    out = _deep_copy(intent)
    out["intent_id"] = "gci_IGNORE"
    out["generated_at_utc"] = "IGNORE"
    return out


def _default_changelog_path(repo_root: Path) -> Path:
    return repo_root / "fixtures" / "golden" / "groove_vectors" / "CHANGELOG.md"


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ensure_changelog_exists(changelog_path: Path) -> None:
    if changelog_path.exists():
        return
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(
        (
            "# Groove Vectors Changelog\n\n"
            "This changelog must be updated whenever `expected_intent.json` is updated via `--update-golden`.\n\n"
            "Format:\n"
            "- YYYY-MM-DD — vector_name — short reason\n"
        ),
        encoding="utf-8",
    )


def _changelog_has_vector_entry(changelog_text: str, vector_name: str) -> bool:
    # Very simple, robust guard: vector dir name must appear somewhere in the changelog.
    # This avoids "updated golden but forgot to bump changelog" drift.
    return vector_name in changelog_text


def _append_changelog_entry(changelog_path: Path, vector_name: str, reason: str) -> None:
    _ensure_changelog_exists(changelog_path)
    line = f"- {_today_utc()} — {vector_name} — {reason.strip()}\n"
    with changelog_path.open("a", encoding="utf-8") as f:
        f.write(line)


def _assert_changelog_bumped_or_bump(
    *,
    changelog_path: Path,
    vector_name: str,
    bump_reason: Optional[str],
) -> None:
    """
    Guard rule:
    - If you're updating expected outputs, you MUST either:
      A) already have a changelog entry containing the vector name, OR
      B) pass --bump-changelog "reason" to append a new entry automatically.
    """
    _ensure_changelog_exists(changelog_path)
    text = changelog_path.read_text(encoding="utf-8")

    if _changelog_has_vector_entry(text, vector_name):
        return

    if bump_reason and bump_reason.strip():
        _append_changelog_entry(changelog_path, vector_name, bump_reason)
        return

    raise RuntimeError(
        f"Refusing to update goldens for {vector_name} because changelog not bumped.\n"
        f"Add an entry to {changelog_path} mentioning '{vector_name}', or re-run with:\n"
        f'  --bump-changelog "short reason"\n'
    )


def replay_vector_dir(
    vector_dir: Path,
    *,
    update_golden: bool = False,
    changelog_path: Optional[Path] = None,
    bump_changelog_reason: Optional[str] = None,
) -> ReplayResult:
    prof_p = vector_dir / "profile.json"
    exp_p = vector_dir / "expected_intent.json"
    meta_p = vector_dir / "meta.json"

    if not prof_p.exists() or not exp_p.exists():
        return ReplayResult(False, f"Missing required files in {vector_dir}", [str(vector_dir)])

    profile = _load_json(prof_p)
    expected = _load_json(exp_p)
    meta = _load_json(meta_p) if meta_p.exists() else {}

    horizon_ms = int(meta.get("horizon_ms", expected.get("horizon_ms", 2000)))

    produced = generate_groove_control_intent_v1(profile, horizon_ms=horizon_ms)

    prod_norm = _normalize_intent_for_compare(produced)
    exp_norm = _normalize_intent_for_compare(expected)

    if prod_norm != exp_norm:
        if update_golden:
            if changelog_path is None:
                repo_root = Path(__file__).resolve().parents[2]
                changelog_path = _default_changelog_path(repo_root)

            try:
                _assert_changelog_bumped_or_bump(
                    changelog_path=changelog_path,
                    vector_name=vector_dir.name,
                    bump_reason=bump_changelog_reason,
                )
            except Exception as e:
                return ReplayResult(False, str(e), [vector_dir.name])

            # Write reviewer-friendly diff first (expected_norm -> produced_norm)
            _write_normalized_diff_txt(
                vector_dir=vector_dir,
                expected_norm=exp_norm,
                produced_norm=prod_norm,
            )

            canon = _canonicalize_expected_intent(produced)
            exp_p.write_text(_dump_json(canon), encoding="utf-8")

            # Also write produced debug artifact for convenience
            (vector_dir / "_produced.intent.json").write_text(_dump_json(produced), encoding="utf-8")

            return ReplayResult(True, f"Updated golden: {vector_dir.name}")

        # Always write mismatch artifacts for diagnosis (even without --update-golden)
        _write_normalized_diff_txt(
            vector_dir=vector_dir,
            expected_norm=exp_norm,
            produced_norm=prod_norm,
        )
        (vector_dir / "_produced.intent.json").write_text(_dump_json(produced), encoding="utf-8")

        msg = (
            f"Replay mismatch in {vector_dir.name}\n"
            f"- produced != expected (after normalization)\n"
            f"Artifacts written: _diff.txt, _produced.intent.json\n"
            f"Tip: run with --update-golden (and bump changelog) to accept.\n"
        )
        return ReplayResult(False, msg, [vector_dir.name])

    # If we get here, vector passes — clean up any stale mismatch artifacts
    _cleanup_mismatch_artifacts(vector_dir)
    return ReplayResult(True, f"Replay OK: {vector_dir.name}")


def replay_all(
    root: Path,
    *,
    update_golden: bool = False,
    changelog_path: Optional[Path] = None,
    bump_changelog_reason: Optional[str] = None,
) -> ReplayResult:
    if not root.exists():
        return ReplayResult(False, f"Vectors root not found: {root}")

    failures: List[str] = []
    vec_dirs = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("vector_")])

    if not vec_dirs:
        return ReplayResult(False, f"No vector_* directories found under {root}")

    for vd in vec_dirs:
        res = replay_vector_dir(
            vd,
            update_golden=update_golden,
            changelog_path=changelog_path,
            bump_changelog_reason=bump_changelog_reason,
        )
        if not res.ok:
            failures.extend(res.failures or [vd.name])

    if failures:
        return ReplayResult(False, f"{len(failures)} vector(s) failed replay: {failures}", failures)

    if update_golden:
        return ReplayResult(True, f"Goldens updated OK ({len(vec_dirs)} vector(s))")

    return ReplayResult(True, f"All vectors passed ({len(vec_dirs)})")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Replay Groove Profile -> Intent golden vectors"
    )
    ap.add_argument(
        "path",
        help="Vector dir (vector_*) OR vectors root (contains vector_* dirs).",
    )
    ap.add_argument(
        "--update-golden",
        action="store_true",
        help="Rewrite expected_intent.json from produced outputs (guarded by CHANGELOG).",
    )
    ap.add_argument(
        "--changelog",
        default=None,
        help="Path to groove vectors CHANGELOG.md (default: fixtures/golden/groove_vectors/CHANGELOG.md).",
    )
    ap.add_argument(
        "--bump-changelog",
        default=None,
        help='If changelog has no entry for a vector being updated, append one with this reason.',
    )
    args = ap.parse_args()
    p = Path(args.path)

    # repo root = .../src/sg_coach/.. -> repo
    repo_root = Path(__file__).resolve().parents[2]
    changelog_path = Path(args.changelog) if args.changelog else _default_changelog_path(repo_root)

    if p.is_dir() and p.name.startswith("vector_"):
        res = replay_vector_dir(
            p,
            update_golden=args.update_golden,
            changelog_path=changelog_path,
            bump_changelog_reason=args.bump_changelog,
        )
    else:
        res = replay_all(
            p,
            update_golden=args.update_golden,
            changelog_path=changelog_path,
            bump_changelog_reason=args.bump_changelog,
        )

    if res.ok:
        print(f"[groove-replay] PASS: {res.message}")
        return 0
    print(f"[groove-replay] FAIL: {res.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
