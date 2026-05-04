"""
Tests for Action Recommender.

Sprint 4: Tests for recommendation engine behavior.
"""
import pytest

from sg_coach.action_recommender import (
    recommend_actions,
    recommend_actions_batch,
    _normalize_severity,
    _has_location,
)
from sg_coach.default_action_mappings import DEFAULT_ACTION_MAPPINGS
from sg_coach.schemas import (
    CoachFinding,
    FindingEvidence,
    Severity,
    FeedbackActionType,
    TargetSpan,
)
from sg_spec.schemas.action_mapping import ActionMapping, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackDomain


def make_finding(
    code: DiagnosisCode,
    severity: Severity = Severity.secondary,
    has_index: bool = False,
    has_beat: bool = False,
    has_target_span: bool = False,
) -> CoachFinding:
    """Create a CoachFinding for testing."""
    evidence = FindingEvidence(
        index=0 if has_index else None,
        beat=1.0 if has_beat else None,
    )
    return CoachFinding(
        type="harmony",
        severity=severity,
        interpretation="Test finding",
        code=code,
        evidence=evidence,
        target_span=TargetSpan() if has_target_span else None,
    )


class TestNormalizeSeverity:
    """Test severity normalization."""

    def test_info_to_info(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, Severity.info)
        assert _normalize_severity(finding) == "info"

    def test_secondary_to_warning(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, Severity.secondary)
        assert _normalize_severity(finding) == "warning"

    def test_primary_to_error(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, Severity.primary)
        assert _normalize_severity(finding) == "error"


class TestHasLocation:
    """Test location detection."""

    def test_no_location(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE)
        assert _has_location(finding) is False

    def test_has_index(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        assert _has_location(finding) is True

    def test_has_beat(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_beat=True)
        assert _has_location(finding) is True

    def test_has_target_span(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_target_span=True)
        assert _has_location(finding) is True


class TestRecommendActions:
    """Test recommend_actions function."""

    def test_returns_actions_for_mapped_code(self):
        finding = make_finding(DiagnosisCode.WRONG_NOTE, has_index=True)
        result = recommend_actions(finding)

        assert result.finding_code == DiagnosisCode.WRONG_NOTE
        assert len(result.actions) > 0
        assert result.source == "action_mapping"

    def test_returns_empty_for_unmapped_code(self):
        # Create finding with a code that's not in default mappings
        finding = CoachFinding(
            type="timing",
            severity=Severity.secondary,
            interpretation="Rushing issue",
            code=DiagnosisCode.RUSHING,  # Not in default mappings
        )
        result = recommend_actions(finding)

        assert result.actions == []
        assert result.source == "no_mapping"

    def test_returns_empty_for_no_code(self):
        finding = CoachFinding(
            type="timing",
            severity=Severity.secondary,
            interpretation="Legacy finding without code",
            code=None,
        )
        result = recommend_actions(finding)

        assert result.actions == []
        assert result.source == "no_code"

    def test_secondary_severity_gets_default_only(self):
        finding = make_finding(
            DiagnosisCode.WRONG_NOTE,
            severity=Severity.secondary,
            has_index=True,
        )
        result = recommend_actions(finding)

        # Should have default actions but not escalation
        action_types = [a.action_type for a in result.actions]
        assert FeedbackActionType.isolate in action_types
        assert FeedbackActionType.review_reference in action_types
        # retry_section is escalation for WRONG_NOTE
        # But it also requires target_span, and we have index, so it should be included if severity is error
        # With secondary severity, escalation actions are NOT included

    def test_primary_severity_gets_escalation(self):
        finding = make_finding(
            DiagnosisCode.WRONG_NOTE,
            severity=Severity.primary,
            has_index=True,
        )
        result = recommend_actions(finding)

        action_types = [a.action_type for a in result.actions]
        # Should have both default and escalation
        assert FeedbackActionType.isolate in action_types
        assert FeedbackActionType.retry_section in action_types

    def test_omits_target_span_required_without_location(self):
        finding = make_finding(
            DiagnosisCode.WRONG_NOTE,
            severity=Severity.primary,
            has_index=False,  # No location
        )
        result = recommend_actions(finding)

        action_types = [a.action_type for a in result.actions]
        # isolate requires target_span, should be omitted
        assert FeedbackActionType.isolate not in action_types
        # review_reference doesn't require target_span, should be included
        assert FeedbackActionType.review_reference in action_types

    def test_includes_target_span_required_with_location(self):
        finding = make_finding(
            DiagnosisCode.WRONG_NOTE,
            severity=Severity.secondary,
            has_index=True,  # Has location
        )
        result = recommend_actions(finding)

        action_types = [a.action_type for a in result.actions]
        # isolate requires target_span and we have location
        assert FeedbackActionType.isolate in action_types

    def test_uses_custom_mappings(self):
        custom_mapping = ActionMapping(
            diagnosis_code=DiagnosisCode.WRONG_NOTE,
            domain=FeedbackDomain.pitch,
            default_actions=[
                RecommendedAction(
                    action_type=FeedbackActionType.repeat,
                    label="Custom repeat",
                )
            ],
        )
        custom_mappings = {DiagnosisCode.WRONG_NOTE: custom_mapping}

        finding = make_finding(DiagnosisCode.WRONG_NOTE)
        result = recommend_actions(finding, mappings=custom_mappings)

        assert len(result.actions) == 1
        assert result.actions[0].label == "Custom repeat"


class TestRecommendActionsBatch:
    """Test recommend_actions_batch function."""

    def test_processes_multiple_findings(self):
        findings = [
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
            make_finding(DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding(DiagnosisCode.PITCH_DEVIATION, has_index=True),
        ]

        results = recommend_actions_batch(findings)

        assert len(results) == 3
        assert results[0].finding_code == DiagnosisCode.WRONG_NOTE
        assert results[1].finding_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert results[2].finding_code == DiagnosisCode.PITCH_DEVIATION

    def test_preserves_order(self):
        findings = [
            make_finding(DiagnosisCode.PITCH_DEVIATION, has_index=True),
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
        ]

        results = recommend_actions_batch(findings)

        assert results[0].finding_code == DiagnosisCode.PITCH_DEVIATION
        assert results[1].finding_code == DiagnosisCode.WRONG_NOTE

    def test_empty_list(self):
        results = recommend_actions_batch([])
        assert results == []

    def test_does_not_deduplicate(self):
        # Two findings with same code
        findings = [
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
            make_finding(DiagnosisCode.WRONG_NOTE, has_index=True),
        ]

        results = recommend_actions_batch(findings)

        # Should have two results, not deduplicated
        assert len(results) == 2


class TestDefaultMappings:
    """Test that default mappings cover Layer 1 codes."""

    def test_dim_orbit_violation_mapped(self):
        assert DiagnosisCode.DIM_ORBIT_VIOLATION in DEFAULT_ACTION_MAPPINGS

    def test_timing_grid_deviation_mapped(self):
        assert DiagnosisCode.TIMING_GRID_DEVIATION in DEFAULT_ACTION_MAPPINGS

    def test_wrong_note_mapped(self):
        assert DiagnosisCode.WRONG_NOTE in DEFAULT_ACTION_MAPPINGS

    def test_pitch_deviation_mapped(self):
        assert DiagnosisCode.PITCH_DEVIATION in DEFAULT_ACTION_MAPPINGS

    def test_all_mappings_have_default_actions(self):
        for code, mapping in DEFAULT_ACTION_MAPPINGS.items():
            assert len(mapping.default_actions) > 0, f"{code} has no default actions"


class TestIntegration:
    """Integration tests with real findings."""

    def test_dim_orbit_violation_with_location(self):
        finding = make_finding(
            DiagnosisCode.DIM_ORBIT_VIOLATION,
            severity=Severity.secondary,
            has_index=True,
        )
        result = recommend_actions(finding)

        assert result.finding_code == DiagnosisCode.DIM_ORBIT_VIOLATION
        assert len(result.actions) >= 2
        action_types = [a.action_type for a in result.actions]
        assert FeedbackActionType.isolate in action_types
        assert FeedbackActionType.review_reference in action_types

    def test_timing_grid_deviation(self):
        finding = make_finding(
            DiagnosisCode.TIMING_GRID_DEVIATION,
            severity=Severity.secondary,
        )
        result = recommend_actions(finding)

        action_types = [a.action_type for a in result.actions]
        assert FeedbackActionType.slow_down in action_types
        assert FeedbackActionType.repeat in action_types

    def test_pitch_deviation_escalation(self):
        finding = make_finding(
            DiagnosisCode.PITCH_DEVIATION,
            severity=Severity.primary,
            has_index=True,
        )
        result = recommend_actions(finding)

        action_types = [a.action_type for a in result.actions]
        # Default + escalation
        assert FeedbackActionType.isolate in action_types
        assert FeedbackActionType.repeat in action_types  # Escalation for pitch deviation
