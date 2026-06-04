"""
Test that sg-coach has no hidden shared.* imports.

Sprint 40: Governance test to ensure canonical imports from sg_spec.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


SHARED_IMPORT_PATTERN = re.compile(
    r"(?:from\s+shared\.|import\s+shared\.)",
    re.MULTILINE,
)


def _should_exclude(path: Path) -> bool:
    """Check if path should be excluded from search."""
    for part in path.parts:
        if part.startswith(".") or part in ("__pycache__", "node_modules", ".venv", "venv"):
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def _find_hidden_imports(root: Path) -> list[tuple[Path, int, str]]:
    """Find all hidden shared.* imports in Python files."""
    violations: list[tuple[Path, int, str]] = []

    for py_file in root.rglob("*.py"):
        if _should_exclude(py_file):
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
            if stripped.startswith("from shared.") or stripped.startswith("import shared."):
                violations.append((py_file, i, stripped))

    return violations


class TestNoHiddenSharedImports:
    """Test that no hidden shared.* imports exist."""

    def test_src_has_no_shared_imports(self) -> None:
        """Source code must not import from shared.*."""
        root = Path(__file__).parent.parent
        src_dir = root / "src"

        if not src_dir.exists():
            pytest.skip("src directory not found")

        violations = _find_hidden_imports(src_dir)

        if violations:
            msg_lines = ["Hidden shared.* imports found in src/:"]
            for path, line_num, content in violations:
                rel_path = path.relative_to(root)
                msg_lines.append(f"  {rel_path}:{line_num}: {content}")
            pytest.fail("\n".join(msg_lines))

    def test_tests_have_no_shared_imports(self) -> None:
        """Test code must not import from shared.*."""
        root = Path(__file__).parent.parent
        tests_dir = root / "tests"

        if not tests_dir.exists():
            pytest.skip("tests directory not found")

        violations = _find_hidden_imports(tests_dir)

        if violations:
            msg_lines = ["Hidden shared.* imports found in tests/:"]
            for path, line_num, content in violations:
                rel_path = path.relative_to(root)
                msg_lines.append(f"  {rel_path}:{line_num}: {content}")
            pytest.fail("\n".join(msg_lines))
