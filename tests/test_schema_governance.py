"""
Tests for CoachFinding Schema Governance

Verifies that evaluators emit findings with all required governance fields.
"""
import uuid
from datetime import datetime, timezone

import pytest

from sg_coach.schemas import (
    CoachFinding,
    FindingEvidence,
    FeedbackDomain,
    FeedbackSeverity,
    FeedbackRenderHint,
    FeedbackActionType,
    DiagnosisCode,
    Severity,
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    TimingErrorStats,
    SuggestedAction,
    severity_to_feedback_severity,
)
from sg_coach.diminished_evaluator import build_context, evaluate_notes
from sg_coach.timing_evaluator import evaluate_timing_grid


class TestSeverityMapping:
    """Test severity to FeedbackSeverity mapping."""

    def test_info_maps_to_info(self):
        assert severity_to_feedback_severity(Severity.info) == FeedbackSeverity.info

    def test_secondary_maps_to_warning(self):
        assert severity_to_feedback_severity(Severity.secondary) == FeedbackSeverity.warning

    def test_primary_maps_to_error(self):
        assert severity_to_feedback_severity(Severity.primary) == FeedbackSeverity.error


class TestCoachFindingNormalization:
    """Test CoachFinding normalization properties."""

    def test_normalized_domain_from_explicit(self):
        finding = CoachFinding(
            type="harmony",
            severity=Severity.secondary,
            interpretation="Test",
            domain=FeedbackDomain.pitch,
        )
        assert finding.normalized_domain == FeedbackDomain.pitch

    def test_normalized_domain_from_type(self):
        finding = CoachFinding(
            type="timing",
            severity=Severity.secondary,
            interpretation="Test",
        )
        assert finding.normalized_domain == FeedbackDomain.timing

    def test_normalized_message_from_explicit(self):
        finding = CoachFinding(
            type="harmony",
            severity=Severity.secondary,
            interpretation="Legacy message",
            message="New message",
        )
        assert finding.normalized_message == "New message"

    def test_normalized_message_from_interpretation(self):
        finding = CoachFinding(
            type="harmony",
            severity=Severity.secondary,
            interpretation="Legacy message",
        )
        assert finding.normalized_message == "Legacy message"

    def test_feedback_severity_property(self):
        finding = CoachFinding(
            type="timing",
            severity=Severity.primary,
            interpretation="Test",
        )
        assert finding.feedback_severity == FeedbackSeverity.error


class TestDiminishedEvaluatorGovernance:
    """Test diminished evaluator emits governance-compliant findings."""

    def test_emits_diagnosis_code(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])  # C is outside orbit
        finding = result.to_coach_finding()

        assert finding is not None
        assert finding.code == DiagnosisCode.DIM_ORBIT_VIOLATION

    def test_emits_domain_harmony(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.domain == FeedbackDomain.harmony

    def test_emits_source_evaluator(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.source_evaluator == "diminished_evaluator"

    def test_evidence_includes_key(self):
        context = build_context("G")
        # G's dim orbit is F#, A, C, Eb (PCs 6, 9, 0, 3)
        # Use G (PC 7) which is outside the orbit
        result = evaluate_notes(context, [7])
        finding = result.to_coach_finding()

        assert finding is not None
        assert finding.evidence.key == "G"

    def test_evidence_includes_expected_set(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.evidence.expected_set is not None
        assert "B" in finding.evidence.expected_set
        assert "D" in finding.evidence.expected_set

    def test_evidence_includes_performed_set(self):
        context = build_context("C")
        result = evaluate_notes(context, [0, 4])  # C, E outside orbit
        finding = result.to_coach_finding()

        assert finding.evidence.performed_set is not None
        assert len(finding.evidence.performed_set) == 2

    def test_evidence_includes_aggregate_stats(self):
        context = build_context("C")
        result = evaluate_notes(context, [11, 2, 0])  # B, D in orbit, C outside
        finding = result.to_coach_finding()

        assert finding.evidence.aggregate_stats is not None
        assert "notes_evaluated" in finding.evidence.aggregate_stats
        assert "notes_in_orbit" in finding.evidence.aggregate_stats
        assert "violation_count" in finding.evidence.aggregate_stats

    def test_has_render_hint(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.render_hint == FeedbackRenderHint.summary

    def test_has_suggested_actions(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert len(finding.suggested_actions) >= 1
        action_types = [a.action_type for a in finding.suggested_actions]
        assert FeedbackActionType.isolate in action_types

    def test_confidence_is_one(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.confidence == 1.0

    def test_title_is_set(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        assert finding.title is not None
        assert "orbit" in finding.title.lower() or "diminished" in finding.title.lower()


class TestTimingEvaluatorGovernance:
    """Test timing evaluator emits governance-compliant findings."""

    def test_emits_diagnosis_code(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],  # 60ms late
            threshold_ms=40.0,
        )
        finding = result.to_coach_finding()

        assert finding is not None
        assert finding.code == DiagnosisCode.TIMING_GRID_DEVIATION

    def test_emits_domain_timing(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.domain == FeedbackDomain.timing

    def test_emits_source_evaluator(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.source_evaluator == "timing_evaluator"

    def test_evidence_includes_unit(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.evidence.unit == "ms"

    def test_evidence_includes_threshold(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
            threshold_ms=40.0,
        )
        finding = result.to_coach_finding()

        assert finding.evidence.threshold == 40.0

    def test_evidence_includes_offset_and_direction(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.evidence.offset_ms is not None
        assert finding.evidence.direction in ["early", "late", "on_time"]

    def test_evidence_includes_index(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.evidence.index is not None

    def test_evidence_includes_aggregate_stats(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5, 1.0],
            performed_times=[0.0, 0.56, 1.0],
        )
        finding = result.to_coach_finding()

        assert finding.evidence.aggregate_stats is not None
        assert "average_abs_error_ms" in finding.evidence.aggregate_stats
        assert "max_abs_error_ms" in finding.evidence.aggregate_stats
        assert "tempo_bpm" in finding.evidence.aggregate_stats

    def test_has_render_hint_timeline(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.render_hint == FeedbackRenderHint.timeline

    def test_has_suggested_actions(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert len(finding.suggested_actions) >= 1
        action_types = [a.action_type for a in finding.suggested_actions]
        assert FeedbackActionType.slow_down in action_types

    def test_confidence_is_one(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.confidence == 1.0

    def test_title_is_set(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        assert finding.title is not None
        assert "timing" in finding.title.lower()


class TestNoMessageOnlyFindings:
    """Verify that findings are never message-only."""

    def test_diminished_finding_has_structured_evidence(self):
        context = build_context("C")
        result = evaluate_notes(context, [0])
        finding = result.to_coach_finding()

        # Must have metric and value at minimum
        assert finding.evidence.metric is not None
        assert finding.evidence.value is not None
        # Must have domain-specific structured data
        assert finding.evidence.key is not None or finding.evidence.expected_set is not None

    def test_timing_finding_has_structured_evidence(self):
        result = evaluate_timing_grid(
            tempo_bpm=120.0,
            expected_times=[0.0, 0.5],
            performed_times=[0.0, 0.56],
        )
        finding = result.to_coach_finding()

        # Must have metric and value at minimum
        assert finding.evidence.metric is not None
        assert finding.evidence.value is not None
        # Must have timing-specific structured data
        assert finding.evidence.offset_ms is not None or finding.evidence.threshold is not None


class TestLegacyCompatibility:
    """Test that legacy fields still work."""

    def test_old_coachfinding_construction_still_works(self):
        # Old-style construction without governance fields
        finding = CoachFinding(
            type="timing",
            severity=Severity.secondary,
            evidence=FindingEvidence(metric="test", value=10.0),
            interpretation="Test message",
        )
        assert finding.type == "timing"
        assert finding.severity == Severity.secondary
        assert finding.interpretation == "Test message"

    def test_new_fields_are_optional(self):
        # Old-style construction - new fields should default to None/empty
        finding = CoachFinding(
            type="harmony",
            severity=Severity.info,
            interpretation="Test",
        )
        assert finding.code is None
        assert finding.domain is None
        assert finding.title is None
        assert finding.message is None
        assert finding.render_hint is None
        assert finding.suggested_actions == []
        assert finding.confidence is None
        assert finding.source_evaluator is None
