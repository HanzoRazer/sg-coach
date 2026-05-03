"""
Tests for Pitch Accuracy Evaluator

Verifies WRONG_NOTE and PITCH_DEVIATION detection with governance compliance.
"""
import uuid

import pytest

from sg_coach.pitch_evaluator import (
    evaluate_pitch_accuracy,
    DEFAULT_CENTS_THRESHOLD,
    _normalize_note_string,
    _notes_match,
    _calculate_cents_error,
)
from sg_coach.exercise_classifier import is_pitch_exercise
from sg_coach.coach_policy import evaluate_session
from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    TimingErrorStats,
    DiagnosisCode,
    FeedbackDomain,
    FeedbackRenderHint,
    FeedbackActionType,
)


def make_pitch_session(program_name: str) -> SessionRecord:
    """Create a minimal SessionRecord for pitch testing."""
    return SessionRecord(
        session_id=uuid.uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name=program_name),
        timing=SessionTiming(bpm=120.0, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=8,
            notes_played=8,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=10.0, std=5.0, max=20.0),
        ),
    )


class TestNoteNormalization:
    """Test note string normalization."""

    def test_normalize_whitespace(self):
        assert _normalize_note_string("  E4  ") == "E4"

    def test_normalize_case(self):
        assert _normalize_note_string("e4") == "E4"

    def test_normalize_none(self):
        assert _normalize_note_string(None) is None

    def test_normalize_empty(self):
        assert _normalize_note_string("") is None
        assert _normalize_note_string("   ") is None


class TestNoteMatching:
    """Test note identity matching."""

    def test_midi_match(self):
        assert _notes_match({"midi": 60}, {"midi": 60}) is True

    def test_midi_mismatch(self):
        assert _notes_match({"midi": 60}, {"midi": 61}) is False

    def test_string_match(self):
        assert _notes_match({"note": "E4"}, {"note": "E4"}) is True

    def test_string_mismatch(self):
        assert _notes_match({"note": "E4"}, {"note": "Eb4"}) is False

    def test_midi_takes_precedence(self):
        # MIDI says match, strings differ
        assert _notes_match(
            {"midi": 60, "note": "C4"},
            {"midi": 60, "note": "B#3"},
        ) is True

    def test_unknown_when_no_data(self):
        assert _notes_match({}, {}) is None
        assert _notes_match({"pitch_hz": 440.0}, {"pitch_hz": 440.0}) is None


class TestCentsCalculation:
    """Test cents error calculation."""

    def test_perfect_unison(self):
        assert _calculate_cents_error(440.0, 440.0) == 0.0

    def test_semitone_sharp(self):
        # A4 to A#4 (ratio ~1.0595) = ~100 cents
        cents = _calculate_cents_error(440.0, 466.16)
        assert 99 < cents < 101

    def test_semitone_flat(self):
        # A4 to Ab4 (ratio ~0.9439) = ~-100 cents
        cents = _calculate_cents_error(440.0, 415.3)
        assert -101 < cents < -99

    def test_quarter_tone(self):
        # Quarter tone = 50 cents
        cents = _calculate_cents_error(440.0, 452.89)
        assert 49 < cents < 51


class TestMatchingNotesNoFinding:
    """Test that matching notes produce no findings."""

    def test_matching_midi_no_finding(self):
        expected = [{"midi": 60}, {"midi": 62}, {"midi": 64}]
        performed = [{"midi": 60}, {"midi": 62}, {"midi": 64}]
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0

    def test_matching_strings_no_finding(self):
        expected = [{"note": "C4"}, {"note": "D4"}, {"note": "E4"}]
        performed = [{"note": "C4"}, {"note": "D4"}, {"note": "E4"}]
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0

    def test_matching_pitch_no_finding(self):
        expected = [{"pitch_hz": 261.63}, {"pitch_hz": 293.66}]
        performed = [{"pitch_hz": 261.63}, {"pitch_hz": 293.66}]
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0


class TestWrongNoteDetection:
    """Test WRONG_NOTE emission."""

    def test_wrong_note_emits_finding(self):
        expected = [{"note": "E4", "midi": 64}]
        performed = [{"note": "Eb4", "midi": 63}]
        findings = evaluate_pitch_accuracy(expected, performed)

        assert len(findings) == 1
        assert findings[0].code == DiagnosisCode.WRONG_NOTE

    def test_wrong_note_message(self):
        expected = [{"note": "E4"}]
        performed = [{"note": "Eb4"}]
        findings = evaluate_pitch_accuracy(expected, performed)

        assert "E4" in findings[0].message
        assert "Eb4" in findings[0].message

    def test_wrong_note_evidence(self):
        expected = [{"note": "E4", "midi": 64}]
        performed = [{"note": "Eb4", "midi": 63}]
        findings = evaluate_pitch_accuracy(expected, performed)

        evidence = findings[0].evidence
        assert evidence.metric == "wrong_note"
        assert evidence.expected is not None
        assert evidence.actual is not None
        assert evidence.index == 0


class TestPitchDeviationDetection:
    """Test PITCH_DEVIATION emission."""

    def test_sharp_pitch_emits_finding(self):
        # 30 cents sharp (> 25 default threshold)
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 447.69}]  # ~30 cents sharp
        findings = evaluate_pitch_accuracy(expected, performed)

        assert len(findings) == 1
        assert findings[0].code == DiagnosisCode.PITCH_DEVIATION

    def test_flat_pitch_emits_finding(self):
        # 30 cents flat (> 25 default threshold)
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 432.43}]  # ~30 cents flat
        findings = evaluate_pitch_accuracy(expected, performed)

        assert len(findings) == 1
        assert findings[0].code == DiagnosisCode.PITCH_DEVIATION
        assert findings[0].evidence.direction == "flat"

    def test_pitch_within_threshold_no_finding(self):
        # 20 cents sharp (< 25 default threshold)
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 445.1}]  # ~20 cents sharp
        findings = evaluate_pitch_accuracy(expected, performed)

        assert len(findings) == 0

    def test_pitch_deviation_evidence(self):
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 447.69}]
        findings = evaluate_pitch_accuracy(expected, performed)

        evidence = findings[0].evidence
        assert evidence.metric == "pitch_deviation"
        assert evidence.unit == "cents"
        assert evidence.threshold == DEFAULT_CENTS_THRESHOLD
        assert evidence.expected == 440.0
        assert evidence.actual == 447.69
        assert evidence.direction == "sharp"
        assert evidence.index == 0


class TestNoDoubleReporting:
    """Test that wrong note and pitch deviation don't double-report."""

    def test_wrong_note_skips_pitch_check(self):
        # Different note AND different pitch - should only emit WRONG_NOTE
        expected = [{"note": "E4", "midi": 64, "pitch_hz": 329.63}]
        performed = [{"note": "Eb4", "midi": 63, "pitch_hz": 311.13}]
        findings = evaluate_pitch_accuracy(expected, performed)

        assert len(findings) == 1
        assert findings[0].code == DiagnosisCode.WRONG_NOTE
        # Should NOT have PITCH_DEVIATION


class TestThresholdOverride:
    """Test cents threshold override."""

    def test_stricter_threshold(self):
        # 20 cents sharp - passes default but fails strict 15
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 445.1}]

        default_findings = evaluate_pitch_accuracy(expected, performed)
        assert len(default_findings) == 0

        strict_findings = evaluate_pitch_accuracy(expected, performed, cents_threshold=15.0)
        assert len(strict_findings) == 1
        assert strict_findings[0].evidence.threshold == 15.0

    def test_looser_threshold(self):
        # 30 cents sharp - fails default but passes loose 50
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 447.69}]

        default_findings = evaluate_pitch_accuracy(expected, performed)
        assert len(default_findings) == 1

        loose_findings = evaluate_pitch_accuracy(expected, performed, cents_threshold=50.0)
        assert len(loose_findings) == 0


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_missing_pitch_hz_no_crash(self):
        expected = [{"note": "E4"}]
        performed = [{"note": "E4"}]  # No pitch_hz
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0  # Should not crash

    def test_missing_note_identity_no_crash(self):
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 440.0}]  # No note/midi
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0  # Should not crash

    def test_empty_lists_no_crash(self):
        findings = evaluate_pitch_accuracy([], [])
        assert len(findings) == 0

    def test_mismatched_lengths(self):
        expected = [{"note": "C4"}, {"note": "D4"}, {"note": "E4"}]
        performed = [{"note": "C4"}, {"note": "D4"}]  # One short
        findings = evaluate_pitch_accuracy(expected, performed)
        assert len(findings) == 0  # Pairs that exist match


class TestGovernanceFields:
    """Test that findings include required governance fields."""

    def test_wrong_note_has_code(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].code == DiagnosisCode.WRONG_NOTE

    def test_wrong_note_has_domain(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].domain == FeedbackDomain.pitch

    def test_wrong_note_has_title(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].title is not None
        assert "note" in findings[0].title.lower()

    def test_wrong_note_has_source_evaluator(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].source_evaluator == "pitch_evaluator"

    def test_wrong_note_has_render_hint(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].render_hint == FeedbackRenderHint.inline

    def test_wrong_note_has_suggested_actions(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert len(findings[0].suggested_actions) >= 1
        action_types = [a.action_type for a in findings[0].suggested_actions]
        assert FeedbackActionType.isolate in action_types

    def test_wrong_note_has_confidence(self):
        findings = evaluate_pitch_accuracy(
            [{"note": "E4"}],
            [{"note": "Eb4"}],
        )
        assert findings[0].confidence == 1.0

    def test_pitch_deviation_has_all_fields(self):
        findings = evaluate_pitch_accuracy(
            [{"pitch_hz": 440.0}],
            [{"pitch_hz": 447.69}],
        )
        f = findings[0]
        assert f.code == DiagnosisCode.PITCH_DEVIATION
        assert f.domain == FeedbackDomain.pitch
        assert f.title is not None
        assert f.message is not None
        assert f.source_evaluator == "pitch_evaluator"
        assert f.render_hint is not None
        assert len(f.suggested_actions) >= 1
        assert f.confidence == 1.0


class TestExerciseClassifier:
    """Test pitch exercise classification."""

    def test_pitch_accuracy_pattern(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="pitch_accuracy_basic.ztprog")
        assert is_pitch_exercise(ref) is True

    def test_pitch_sequence_pattern(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="pitch_sequence_C.ztprog")
        assert is_pitch_exercise(ref) is True

    def test_pitch_layer1b_pattern(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="exercises/pitch_layer1b_intro.ztprog")
        assert is_pitch_exercise(ref) is True

    def test_note_accuracy_pattern(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="note_accuracy_drill.ztprog")
        assert is_pitch_exercise(ref) is True

    def test_single_note_pitch_pattern(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="single_note_pitch_test.ztprog")
        assert is_pitch_exercise(ref) is True

    def test_non_pitch_exercise(self):
        ref = ProgramRef(type=ProgramType.ztprog, name="blues_turnaround_E.ztprog")
        assert is_pitch_exercise(ref) is False


class TestPipelineIntegration:
    """Test pitch evaluator integration with evaluate_session."""

    def test_pitch_gated_session_emits_wrong_note(self):
        session = make_pitch_session("pitch_accuracy_basic.ztprog")
        expected = [{"note": "E4", "midi": 64}]
        performed = [{"note": "Eb4", "midi": 63}]

        result = evaluate_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
        )

        pitch_findings = [f for f in result.findings if f.code == DiagnosisCode.WRONG_NOTE]
        assert len(pitch_findings) == 1

    def test_pitch_gated_session_emits_deviation(self):
        session = make_pitch_session("pitch_accuracy_basic.ztprog")
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 455.0}]  # ~58 cents sharp

        result = evaluate_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
        )

        pitch_findings = [f for f in result.findings if f.code == DiagnosisCode.PITCH_DEVIATION]
        assert len(pitch_findings) == 1

    def test_non_pitch_exercise_no_pitch_findings(self):
        session = make_pitch_session("blues_turnaround_E.ztprog")
        expected = [{"note": "E4"}]
        performed = [{"note": "Eb4"}]  # Would be wrong note

        result = evaluate_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
        )

        pitch_findings = [f for f in result.findings
                         if f.code in (DiagnosisCode.WRONG_NOTE, DiagnosisCode.PITCH_DEVIATION)]
        assert len(pitch_findings) == 0

    def test_missing_pitch_events_no_crash(self):
        session = make_pitch_session("pitch_accuracy_basic.ztprog")

        # No pitch events provided - should still work
        result = evaluate_session(session)

        assert result.session_id == session.session_id
        assert result.coach_version.startswith("coach-rules@")

    def test_threshold_override_in_session(self):
        session = make_pitch_session("pitch_accuracy_basic.ztprog")
        expected = [{"pitch_hz": 440.0}]
        performed = [{"pitch_hz": 445.1}]  # ~20 cents sharp

        # Default threshold (25) - no finding
        result_default = evaluate_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
        )
        pitch_findings_default = [f for f in result_default.findings
                                  if f.code == DiagnosisCode.PITCH_DEVIATION]
        assert len(pitch_findings_default) == 0

        # Strict threshold (15) - should find
        result_strict = evaluate_session(
            session,
            expected_pitch_events=expected,
            performed_pitch_events=performed,
            pitch_cents_threshold=15.0,
        )
        pitch_findings_strict = [f for f in result_strict.findings
                                 if f.code == DiagnosisCode.PITCH_DEVIATION]
        assert len(pitch_findings_strict) == 1
