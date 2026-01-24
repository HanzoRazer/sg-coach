#!/usr/bin/env python3
"""
Contracts Governance Gate (Scenario B)

Enforces:
  1) *.schema.sha256 format = single 64-char lowercase hex line
  2) If any contract schema/hash changes:
       - contracts/CHANGELOG.md must change
       - ADDED lines must mention each changed contract stem
  3) If contracts are public_released=true:
       - *_v1.schema.json and *_v1.schema.sha256 are immutable

Exit codes:
  0 pass
  1 violations
  2 execution error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class Violation:
    code: str
    message: str


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def run_git(args: List[str], cwd: Path) -> str:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{p.stdout}\n{p.stderr}")
    return p.stdout


def _in_ci() -> bool:
    """GitHub Actions and most CI providers set CI=true."""
    return str(os.getenv("CI", "")).lower() in {"1", "true", "yes"}


def _should_auto_debug() -> bool:
    """Only auto-debug locally (TTY) and not in CI."""
    try:
        return (not _in_ci()) and sys.stdout.isatty()
    except Exception:
        return False


def changed_files(repo_root: Path, base_ref: str) -> List[str]:
    out = run_git(["diff", "--name-only", f"{base_ref}...HEAD"], cwd=repo_root)
    return [x.strip() for x in out.splitlines() if x.strip()]


def is_contract_schema(p: str) -> bool:
    return p.startswith("contracts/") and p.endswith(".schema.json")


def is_contract_sha(p: str) -> bool:
    return p.startswith("contracts/") and p.endswith(".schema.sha256")


def contract_stem(p: str) -> str:
    name = Path(p).name
    if name.endswith(".schema.json"):
        return name[:-len(".schema.json")]
    if name.endswith(".schema.sha256"):
        return name[:-len(".schema.sha256")]
    return name


def is_v1_contract(p: str) -> bool:
    return bool(re.search(r"_v1\.schema\.(json|sha256)$", p))


def read_contracts_version(repo_root: Path) -> Tuple[bool, str]:
    fp = repo_root / "contracts" / "CONTRACTS_VERSION.json"
    if not fp.exists():
        return False, ""
    data = json.loads(fp.read_text(encoding="utf-8"))
    return bool(data.get("public_released", False)), str(data.get("tag", ""))


# ---------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------

def check_sha256_format(repo_root: Path) -> List[Violation]:
    v: List[Violation] = []
    contracts_dir = repo_root / "contracts"
    if not contracts_dir.exists():
        return v
    for fp in contracts_dir.glob("*.schema.sha256"):
        raw = fp.read_text(encoding="utf-8").strip()
        if not HEX64_RE.match(raw):
            v.append(Violation(
                "SHA256_FORMAT",
                f"{fp.as_posix()} must contain exactly one 64-char lowercase hex line."
            ))
    return v


def check_changelog_required(repo_root: Path, changed: List[str], base_ref: str) -> List[Violation]:
    v: List[Violation] = []
    touched = [p for p in changed if is_contract_schema(p) or is_contract_sha(p)]
    if not touched:
        return v

    if "contracts/CHANGELOG.md" not in changed:
        return [Violation(
            "CHANGELOG_REQUIRED",
            "Contract schema/hash changed but contracts/CHANGELOG.md was not updated."
        )]

    # Require stems to appear in ADDED lines for this PR (deleted lines do not satisfy documentation).
    raw = run_git(["diff", f"{base_ref}...HEAD", "--", "contracts/CHANGELOG.md"], cwd=repo_root)
    added_lines = "\n".join(
        ln[1:] for ln in raw.splitlines()
        if ln.startswith("+") and not ln.startswith("+++ ")
    )

    stems = sorted({contract_stem(p) for p in touched})
    missing = [s for s in stems if s not in added_lines]

    if missing:
        v.append(Violation(
            "CHANGELOG_MISSING_MENTIONS",
            "contracts/CHANGELOG.md ADDED lines must mention each changed contract: "
            + ", ".join(missing)
        ))

    return v


def check_v1_immutability(repo_root: Path, changed: List[str]) -> List[Violation]:
    v: List[Violation] = []
    public, tag = read_contracts_version(repo_root)
    if not public:
        return v

    v1_changes = [p for p in changed if is_v1_contract(p)]
    for p in v1_changes:
        v.append(Violation(
            "V1_IMMUTABLE",
            f"{p} is immutable after public release (tag={tag or '<none>'}). "
            "Create a new version instead."
        ))

    return v


# ---------------------------------------------------------------------
# main
# ---------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_contracts_governance",
        description="Contracts Governance Gate (Scenario B)",
    )
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument(
        "--base-ref",
        default="origin/main",
        help="Base ref for diff (default: origin/main). For PRs use origin/main or the PR base branch.",
    )
    ap.add_argument("--debug", action="store_true", help="Print extra diagnostics (local troubleshooting).")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()

    try:
        changed = changed_files(repo_root, args.base_ref)
    except Exception as e:
        print(f"[contracts-gov] ERROR: {e}", file=sys.stderr)
        return 2

    violations: List[Violation] = []
    try:
        violations.extend(check_sha256_format(repo_root))
        violations.extend(check_changelog_required(repo_root, changed, args.base_ref))
        violations.extend(check_v1_immutability(repo_root, changed))
    except Exception as e:
        print(f"[contracts-gov] ERROR: {e}", file=sys.stderr)
        return 2

    if not violations:
        print("[contracts-gov] PASS")
        return 0

    print(f"[contracts-gov] FAIL ({len(violations)} violations)", file=sys.stderr)
    for vi in violations:
        print(f"  - [{vi.code}] {vi.message}", file=sys.stderr)

    print("\n[contracts-gov] Hint: re-run with --debug for details.", file=sys.stderr)

    # Auto-debug locally on failure (keeps CI logs clean).
    debug = bool(args.debug) or _should_auto_debug()
    if debug:
        try:
            public, tag = read_contracts_version(repo_root)
            contract_changes = [p for p in changed if is_contract_schema(p) or is_contract_sha(p)]
            print("\n[contracts-gov] DEBUG", file=sys.stderr)
            print(f"  repo_root={repo_root}", file=sys.stderr)
            print(f"  base_ref={args.base_ref}", file=sys.stderr)
            print(f"  changed_files={len(changed)}", file=sys.stderr)
            print(f"  contract_changes={len(contract_changes)}", file=sys.stderr)
            print(f"  public_released={public} tag={tag or '<none>'}", file=sys.stderr)
            if contract_changes:
                print("  contract_change_stems=" + ", ".join(sorted({contract_stem(p) for p in contract_changes})), file=sys.stderr)
        except Exception as e:
            print(f"[contracts-gov] DEBUG ERROR: {e}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
