"""
Documentation governance tests for the Sprint 40 coaching method governance.

Sprint 40: Composite coaching method — one integrated system.

Documentation-existence and content tests only. They assert that the coaching
method governance document exists and encodes the required governance rules.
"""
from __future__ import annotations

from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
GOVERNANCE_DOC = DOCS_DIR / "coaching_method_governance.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestCoachingMethodGovernanceDoc:
    """coaching_method_governance.md exists and encodes the rules."""

    def test_governance_doc_exists(self) -> None:
        assert GOVERNANCE_DOC.exists(), f"missing {GOVERNANCE_DOC.name}"

    def test_diagnosis_before_prescription(self) -> None:
        assert "diagnosis before prescription" in _read(GOVERNANCE_DOC).lower()

    def test_mentions_four_layer_model(self) -> None:
        assert "four-layer" in _read(GOVERNANCE_DOC).lower()

    def test_preserves_teacher_authority(self) -> None:
        assert "teacher authority" in _read(GOVERNANCE_DOC).lower()

    def test_measurable_outcomes(self) -> None:
        assert "measurable outcome" in _read(GOVERNANCE_DOC).lower()

    def test_rhythm_and_song_are_integration_tests(self) -> None:
        text = _read(GOVERNANCE_DOC).lower()
        assert "integration test" in text
        assert "rhythm" in text
        assert "song performance" in text

    def test_ear_training_is_future_domain(self) -> None:
        text = _read(GOVERNANCE_DOC).lower()
        assert "ear training" in text
        assert "future learning domain" in text
