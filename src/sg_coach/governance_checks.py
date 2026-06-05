"""
Cross-repository governance checks.

Sprint 41: Detect violations of governance boundaries.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def assert_no_hidden_shared_imports(root: Path) -> list[str]:
    """
    Check for hidden shared.* imports in Python files.

    Returns list of violation strings (empty if clean).
    """
    violations: list[str] = []

    src_dir = root / "src"
    tests_dir = root / "tests"

    for search_dir in [src_dir, tests_dir]:
        if not search_dir.exists():
            continue

        for py_file in search_dir.rglob("*.py"):
            if _should_exclude(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            for i, line in enumerate(content.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                    continue
                if stripped.startswith("from shared.") or stripped.startswith("import shared."):
                    rel_path = py_file.relative_to(root)
                    violations.append(f"{rel_path}:{i}: {stripped}")

    return violations


def assert_no_pr_snapshot_dirs(root: Path) -> list[str]:
    """
    Check for PR snapshot directories that should not exist.

    Returns list of violation strings (empty if clean).
    """
    violations: list[str] = []
    pattern = re.compile(r"^sg-agentd-pr\d+")

    for item in root.iterdir():
        if item.is_dir() and pattern.match(item.name):
            violations.append(f"PR snapshot directory found: {item.name}/")

    return violations


def assert_no_collapsed_feedback_boundary(route_text: str) -> list[str]:
    """
    Check route code for unsafe collapsed feedback boundaries.

    A collapsed boundary is unsafe if it:
    1. Defines /feedback_and_regen endpoint
    2. Does NOT include deprecation metadata

    Returns list of violation strings (empty if clean).
    """
    violations: list[str] = []

    # Look for combined endpoint definition
    if "feedback_and_regen" in route_text.lower():
        # Check for deprecation markers
        has_deprecated_flag = "deprecated" in route_text.lower()
        has_governance_warning = "collapsed_feedback_regeneration_boundary" in route_text
        has_boundary_metadata = "boundary_metadata" in route_text

        if not (has_deprecated_flag and has_governance_warning):
            violations.append(
                "feedback_and_regen endpoint found without deprecation metadata"
            )

        if not has_boundary_metadata:
            violations.append(
                "feedback_and_regen endpoint found without boundary_metadata"
            )

    return violations


def check_ai_provisional_status_doc(root: Path) -> list[str]:
    """
    Check that AI provisional status documentation exists.

    Returns list of violation strings (empty if clean).
    """
    violations: list[str] = []

    docs_dir = root / "docs"
    expected_file = docs_dir / "AI_PROVISIONAL_STATUS.md"

    if not expected_file.exists():
        violations.append(
            f"Missing required documentation: {expected_file.relative_to(root)}"
        )

    return violations


def run_all_governance_checks(
    repo_root: Path,
    check_shared_imports: bool = True,
    check_pr_snapshots: bool = True,
    check_feedback_boundary: bool = True,
    check_ai_docs: bool = False,
    feedback_route_path: Optional[Path] = None,
) -> dict[str, list[str]]:
    """
    Run all governance checks and return results.

    Returns dict mapping check name to list of violations.
    """
    results: dict[str, list[str]] = {}

    if check_shared_imports:
        results["hidden_shared_imports"] = assert_no_hidden_shared_imports(repo_root)

    if check_pr_snapshots:
        results["pr_snapshot_dirs"] = assert_no_pr_snapshot_dirs(repo_root)

    if check_feedback_boundary and feedback_route_path:
        if feedback_route_path.exists():
            route_text = feedback_route_path.read_text(encoding="utf-8")
            results["collapsed_feedback_boundary"] = assert_no_collapsed_feedback_boundary(route_text)
        else:
            results["collapsed_feedback_boundary"] = [
                f"Feedback route file not found: {feedback_route_path}"
            ]

    if check_ai_docs:
        results["ai_provisional_docs"] = check_ai_provisional_status_doc(repo_root)

    return results


def _should_exclude(path: Path) -> bool:
    """Check if path should be excluded from search."""
    for part in path.parts:
        if part.startswith(".") or part in ("__pycache__", "node_modules", ".venv", "venv"):
            return True
        if part.endswith(".egg-info"):
            return True
    return False


__all__ = [
    "assert_no_hidden_shared_imports",
    "assert_no_pr_snapshot_dirs",
    "assert_no_collapsed_feedback_boundary",
    "check_ai_provisional_status_doc",
    "run_all_governance_checks",
]
