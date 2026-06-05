#!/usr/bin/env python3
"""
Check for hidden dependencies on shared.* imports.

Sprint 40: Governance check to ensure sg-coach doesn't depend on
string_master's shared module.

Exit codes:
    0: No hidden dependencies found
    1: Hidden dependencies detected
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN_IMPORT_PATTERN = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)")
FORBIDDEN_IMPORT_ROOTS = ("shared", "string_master", "zone_tritone")

EXCLUDED_PATTERNS = [
    "*.pyc",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".egg-info",
]


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from search."""
    for part in path.parts:
        if part.startswith(".") or part in ("__pycache__", "node_modules", ".venv", "venv"):
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def find_hidden_imports(root: Path) -> list[tuple[Path, int, str]]:
    """
    Find all hidden shared.* imports in Python files.

    Returns list of (file_path, line_number, line_content) tuples.
    """
    violations: list[tuple[Path, int, str]] = []

    for py_file in root.rglob("*.py"):
        if should_exclude(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments and docstrings
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            # Only match actual import statements
            match = FORBIDDEN_IMPORT_PATTERN.match(line)
            if match and match.group(1).split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                violations.append((py_file, i, stripped))

    return violations


def main() -> int:
    """Run the check and report results."""
    # Find the sg-coach root (parent of scripts/)
    script_dir = Path(__file__).parent
    root = script_dir.parent

    # Check both src and tests
    src_dir = root / "src"
    tests_dir = root / "tests"

    violations: list[tuple[Path, int, str]] = []

    if src_dir.exists():
        violations.extend(find_hidden_imports(src_dir))
    if tests_dir.exists():
        violations.extend(find_hidden_imports(tests_dir))

    if violations:
        print("ERROR: Hidden string_master dependency detected")
        print("(shared.* / string_master.* / zone_tritone.* imports):")
        print()
        for path, line_num, content in violations:
            rel_path = path.relative_to(root)
            print(f"  {rel_path}:{line_num}: {content}")
        print()
        print(f"Total violations: {len(violations)}")
        print()
        print("Fix: Replace 'from shared.zone_tritone import ...'")
        print("     with 'from sg_spec.music.pitch_class import ...'")
        return 1

    print("OK: No hidden shared/string_master/zone_tritone imports found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
