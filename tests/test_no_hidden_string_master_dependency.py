"""
Guard: sg-coach must not depend on the legacy string_master monorepo.

Sprint 41: sg-coach is reproducible from installed packages alone
(`sg-spec`, `sg-curriculum`, and its own `src/`). It must not import from
`shared`, `string_master`, or `zone_tritone`, and its test setup must not inject
`string_master` onto `sys.path`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sg_coach.governance_checks import assert_no_string_master_dependency

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestNoStringMasterDependency:
    def test_no_forbidden_imports_in_src_and_tests(self) -> None:
        violations = assert_no_string_master_dependency(REPO_ROOT)
        assert violations == [], (
            "Hidden string_master/shared/zone_tritone imports found:\n"
            + "\n".join(violations)
        )

    def test_conftest_does_not_inject_string_master(self) -> None:
        conftest = REPO_ROOT / "tests" / "conftest.py"
        text = conftest.read_text(encoding="utf-8")
        # Flag only actual sys.path mutation, not prose mentioning sys.path.
        mutations = ("sys.path.insert", "sys.path.append", "sys.path +=", "sys.path =")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            for mut in mutations:
                assert mut not in stripped, (
                    f"conftest.py:{i} re-introduces a sys.path hack: {stripped}"
                )

    def test_guard_detects_a_planted_violation(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("from zone_tritone import diminished\n")
        (src / "also_bad.py").write_text("import string_master.engine\n")
        violations = assert_no_string_master_dependency(tmp_path)
        assert len(violations) == 2

    def test_guard_ignores_comments_and_strings(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "ok.py").write_text(
            "# theory truth (in zone_tritone)\n"
            'EXAMPLE = "from shared.zone_tritone import foo"\n'
            "from sg_spec.music.pitch_class import pc_from_name\n"
        )
        assert assert_no_string_master_dependency(tmp_path) == []
