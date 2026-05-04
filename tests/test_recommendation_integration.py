"""
Tests for Recommendation Integration.

Sprint 4: Tests for attach_recommendations() and CoachEvaluation.recommendations.
"""
import pytest
from uuid import uuid4

from sg_coach.recommendation_integration import attach_recommendations
from sg_coach.default_action_mappings import DEFAULT_ACTION_MAPPINGS
from sg_coach.schemas import (
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    Severity,
    FeedbackActionType,
    TargetSpan,
)
from sg_spec.schemas.action_mapping import ActionMapping, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackDomain


def make_finding(
    code: DiagnosisCode = DiagnosisCode.WRONG_NOTE,
    severity: Severity = Severity.secondary,
    has_index: bool = False,
) -> CoachFinding:
    """Create a CoachFinding for testing."""
    evidence = FindingEvidence(index=0 if has_index else None)
    return CoachFinding(
        type="harmony",
        severity=severity,
        interpretation="Test finding",
        code=code,
        evidence=evidence,
    )


def make_evaluation(findings: list = None) -> CoachEvaluation:
    """Create a CoachEvaluation for testing."""
    return CoachEvaluation(
        session_id=uuid4(),
        coach_version="test@0.1.0",
        findings=findings or [],
        focus_recommendation=FocusRecommendation(
            concept="Test concept",
            reason="Test reason",
        ),
        confidence=1.0,
    )


class TestAttachRecommendations:
    """Test attach_recommendations function."""

    def test_empty_findings_returns_empty_recommendations(self):
        evaluation = make_evaluation(findings=[])
        result = attach_recommendations(evaluation)

        assert result.recommendations == []

    def test_populates_recommendations_for_mapped_code(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        evaluation = make_evaluation(findings=[finding])

        result = attach_recommendations(evaluation)

        assert result.recommendations is not None
        assert len(result.recommendations) == 1
        assert result.recommendations[0].finding_code == DiagnosisCode.WRONG_NOTE
        assert len(result.recommendations[0].actions) > 0

    def test_preserves_finding_order(self):
        findings = [
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
            make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding(DiagnosisCode.PITCH_DEVIATION, has_index=True),
        ]
        evaluation = make_evaluation(findings=findings)

        result = attach_recommendations(evaluation)

        assert len(result.recommendations) == 3
        assert result.recommendations[0].finding_code == DiagnosisCode.WRONG_NOTE
        assert result.recommendations[1].finding_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result.recommendations[2].finding_code == DiagnosisCode.PITCH_DEVIATION

    def test_returns_new_evaluation_immutable(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        original = make_evaluation(findings=[finding])
        original_dict = original.model_dump()

        result = attach_recommendations(original)

        # Original should be unchanged
        assert original.recommendations is None
        assert original.model_dump() == original_dict
        # Result should have recommendations
        assert result.recommendations is not None

    def test_preserves_all_original_fields(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        original = make_evaluation(findings=[finding])

        result = attach_recommendations(original)

        # All fields should match except recommendations
        assert result.session_id == original.session_id
        assert result.coach_version == original.coach_version
        assert result.findings == original.findings
        assert result.strengths == original.strengths
        assert result.weaknesses == original.weaknesses
        assert result.focus_recommendation == original.focus_recommendation
        assert result.confidence == original.confidence

    def test_uses_custom_mappings(self):
        custom_mapping = ActionMapping(
            diagnosis_code=DiagnosisCode.WRONG_NOTE,
            domain=FeedbackDomain.pitch,
            default_actions=[
                RecommendedAction(
                    action_type=FeedbackActionType.repeat,
                    label="Custom action",
                )
            ],
        )
        custom_mappings = {DiagnosisCode.WRONG_NOTE: custom_mapping}

        finding = make_finding(DiagnosisCode.WRONG_NOTE)
        evaluation = make_evaluation(findings=[finding])

        result = attach_recommendations(evaluation, mappings=custom_mappings)

        assert len(result.recommendations) == 1
        assert len(result.recommendations[0].actions) == 1
        assert result.recommendations[0].actions[0].label == "Custom action"

    def test_unmapped_code_returns_empty_actions(self):
        finding = CoachFinding(
            type="timing",
            severity=Severity.secondary,
            interpretation="Rushing issue",
            code=DiagnosisCode.RUSHING,
        )
        evaluation = make_evaluation(findings=[finding])

        result = attach_recommendations(evaluation)

        assert len(result.recommendations) == 1
        assert result.recommendations[0].actions == []
        assert result.recommendations[0].source == "no_mapping"

    def test_mixed_mapped_and_unmapped(self):
        findings = [
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
            CoachFinding(
                type="timing",
                severity=Severity.secondary,
                interpretation="Rushing issue",
                code=DiagnosisCode.RUSHING,
            ),
        ]
        evaluation = make_evaluation(findings=findings)

        result = attach_recommendations(evaluation)

        assert len(result.recommendations) == 2
        # First should have actions
        assert len(result.recommendations[0].actions) > 0
        # Second should be empty
        assert result.recommendations[1].actions == []


class TestIdempotency:
    """Test that reattaching recommendations is idempotent."""

    def test_reattach_produces_same_result(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        evaluation = make_evaluation(findings=[finding])

        once = attach_recommendations(evaluation)
        twice = attach_recommendations(once)

        # Convert to dicts for comparison (recommendations should be equal)
        once_recs = [r.model_dump() for r in once.recommendations]
        twice_recs = [r.model_dump() for r in twice.recommendations]
        assert once_recs == twice_recs


class TestRecommendationsField:
    """Test CoachEvaluation.recommendations field behavior."""

    def test_default_is_none(self):
        evaluation = make_evaluation()
        assert evaluation.recommendations is None

    def test_can_set_to_empty_list(self):
        evaluation = CoachEvaluation(
            session_id=uuid4(),
            coach_version="test@0.1.0",
            findings=[],
            focus_recommendation=FocusRecommendation(
                concept="Test concept",
                reason="Test reason",
            ),
            confidence=1.0,
            recommendations=[],
        )
        assert evaluation.recommendations == []

    def test_serializes_to_json(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        evaluation = make_evaluation(findings=[finding])
        result = attach_recommendations(evaluation)

        json_data = result.model_dump_json()
        assert "recommendations" in json_data
        assert "wrong_note" in json_data  # Enum serializes as value (lowercase)

    def test_deserializes_without_recommendations(self):
        json_data = {
            "session_id": str(uuid4()),
            "coach_version": "test@0.1.0",
            "findings": [],
            "strengths": [],
            "weaknesses": [],
            "focus_recommendation": {"concept": "Test", "reason": "Test"},
            "confidence": 1.0,
        }
        evaluation = CoachEvaluation.model_validate(json_data)
        assert evaluation.recommendations is None


class TestIntegration:
    """Integration tests with full pipeline."""

    def test_full_pipeline_with_multiple_findings(self):
        findings = [
            CoachFinding(
                type="harmony",
                severity=Severity.secondary,
                interpretation="Orbit violation",
                code=DiagnosisCode.DIM_ORBIT_VIOLATION,
                evidence=FindingEvidence(index=0),
            ),
            CoachFinding(
                type="timing",
                severity=Severity.primary,
                interpretation="Timing issue",
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                evidence=FindingEvidence(beat=2.0),
            ),
            CoachFinding(
                type="harmony",
                severity=Severity.secondary,
                interpretation="Wrong note",
                code=DiagnosisCode.WRONG_NOTE,
                evidence=FindingEvidence(index=5),
            ),
        ]
        evaluation = make_evaluation(findings=findings)

        result = attach_recommendations(evaluation)

        # All three should have recommendations
        assert len(result.recommendations) == 3

        # Check first (DIM_ORBIT_VIOLATION)
        rec0 = result.recommendations[0]
        assert rec0.finding_code == DiagnosisCode.DIM_ORBIT_VIOLATION
        action_types = [a.action_type for a in rec0.actions]
        assert FeedbackActionType.isolate in action_types

        # Check second (TIMING_GRID_DEVIATION with primary severity)
        rec1 = result.recommendations[1]
        assert rec1.finding_code == DiagnosisCode.TIMING_GRID_DEVIATION
        action_types = [a.action_type for a in rec1.actions]
        assert FeedbackActionType.slow_down in action_types
        # Primary severity should include escalation
        assert FeedbackActionType.retry_section in action_types

        # Check third (WRONG_NOTE)
        rec2 = result.recommendations[2]
        assert rec2.finding_code == DiagnosisCode.WRONG_NOTE
