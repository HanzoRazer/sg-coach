"""
Tests for governance checks module.

Sprint 41: Cross-repository governance enforcement.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sg_coach.governance_checks import (
    assert_no_hidden_shared_imports,
    assert_no_pr_snapshot_dirs,
    assert_no_collapsed_feedback_boundary,
    check_ai_provisional_status_doc,
)


class TestAssertNoHiddenSharedImports:
    """Test hidden shared import detection."""

    def test_detects_shared_imports(self, tmp_path: Path) -> None:
        """Detects from shared.* imports."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        bad_file = src_dir / "bad_module.py"
        bad_file.write_text(
            "from shared.zone_tritone import foo\n"
            "import shared.coach_schemas\n"
        )

        violations = assert_no_hidden_shared_imports(tmp_path)

        assert len(violations) == 2
        assert "from shared.zone_tritone" in violations[0]
        assert "import shared.coach_schemas" in violations[1]

    def test_passes_when_no_shared_imports(self, tmp_path: Path) -> None:
        """No violations when using canonical imports."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        good_file = src_dir / "good_module.py"
        good_file.write_text(
            "from sg_spec.music.pitch_class import pc_from_name\n"
            "import sg_spec.schemas\n"
        )

        violations = assert_no_hidden_shared_imports(tmp_path)

        assert len(violations) == 0

    def test_ignores_comments(self, tmp_path: Path) -> None:
        """Comments mentioning shared.* are ignored."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        file_with_comment = src_dir / "commented.py"
        file_with_comment.write_text(
            "# from shared.zone_tritone import foo\n"
            "# This used to be import shared.coach_schemas\n"
        )

        violations = assert_no_hidden_shared_imports(tmp_path)

        assert len(violations) == 0

    def test_ignores_docstrings(self, tmp_path: Path) -> None:
        """Docstrings mentioning shared.* are ignored."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        file_with_docstring = src_dir / "docstring.py"
        file_with_docstring.write_text(
            '"""from shared.zone_tritone import foo"""\n'
        )

        violations = assert_no_hidden_shared_imports(tmp_path)

        assert len(violations) == 0


class TestAssertNoPrSnapshotDirs:
    """Test PR snapshot directory detection."""

    def test_detects_pr_snapshot_dirs(self, tmp_path: Path) -> None:
        """Detects sg-agentd-pr* directories."""
        (tmp_path / "sg-agentd-pr22").mkdir()
        (tmp_path / "sg-agentd-pr23-capabilities").mkdir()
        (tmp_path / "sg-agentd-pr30-open-cli").mkdir()

        violations = assert_no_pr_snapshot_dirs(tmp_path)

        assert len(violations) == 3

    def test_passes_when_no_snapshot_dirs(self, tmp_path: Path) -> None:
        """No violations when no PR snapshot dirs exist."""
        (tmp_path / "sg_agentd").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()

        violations = assert_no_pr_snapshot_dirs(tmp_path)

        assert len(violations) == 0

    def test_ignores_unrelated_dirs(self, tmp_path: Path) -> None:
        """Ignores directories not matching the pattern."""
        (tmp_path / "sg-spec").mkdir()
        (tmp_path / "sg-coach").mkdir()
        (tmp_path / "pr-notes").mkdir()

        violations = assert_no_pr_snapshot_dirs(tmp_path)

        assert len(violations) == 0


class TestAssertNoCollapsedFeedbackBoundary:
    """Test collapsed feedback boundary detection."""

    def test_detects_unsafe_combined_boundary(self) -> None:
        """Detects feedback_and_regen without deprecation."""
        route_code = '''
@router.post("/feedback_and_regen")
async def feedback_and_regen(request):
    pass
'''
        violations = assert_no_collapsed_feedback_boundary(route_code)

        assert len(violations) == 2
        assert "deprecation" in violations[0].lower()
        assert "boundary_metadata" in violations[1].lower()

    def test_passes_deprecated_boundary(self) -> None:
        """Passes when deprecated and boundary_metadata present."""
        route_code = '''
@router.post("/feedback_and_regen")
async def feedback_and_regen(request):
    # collapsed_feedback_regeneration_boundary
    # deprecated = True
    # boundary_metadata = ...
    pass
'''
        violations = assert_no_collapsed_feedback_boundary(route_code)

        assert len(violations) == 0

    def test_passes_when_no_combined_endpoint(self) -> None:
        """No violations when combined endpoint doesn't exist."""
        route_code = '''
@router.post("/feedback")
async def feedback(request):
    pass

@router.post("/regenerate")
async def regenerate(request):
    pass
'''
        violations = assert_no_collapsed_feedback_boundary(route_code)

        assert len(violations) == 0


class TestCheckAiProvisionalStatusDoc:
    """Test AI provisional status doc check."""

    def test_detects_missing_doc(self, tmp_path: Path) -> None:
        """Detects when AI_PROVISIONAL_STATUS.md is missing."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        violations = check_ai_provisional_status_doc(tmp_path)

        assert len(violations) == 1
        assert "AI_PROVISIONAL_STATUS.md" in violations[0]

    def test_passes_when_doc_exists(self, tmp_path: Path) -> None:
        """No violations when doc exists."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "AI_PROVISIONAL_STATUS.md").write_text("# AI Provisional Status\n")

        violations = check_ai_provisional_status_doc(tmp_path)

        assert len(violations) == 0
