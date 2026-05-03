"""
Tests for Diminished Evaluator Pipeline Integration

Verifies that evaluate_session() correctly routes to diminished_evaluator
for diminished-navigation exercises.
"""
import uuid
from datetime import datetime, timezone

import pytest

from sg_coach.coach_policy import evaluate_session, _evaluate_diminished_harmony
from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    TimingErrorStats,
)


def make_session(program_name: str) -> SessionRecord:
    """Create a minimal SessionRecord for testing."""
    return SessionRecord(
        session_id=uuid.uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name=program_name),
        timing=SessionTiming(bpm=120.0, grid=16),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=32,
            notes_played=32,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=10.0, std=5.0, max=20.0),
        ),
    )


class TestDiminishedPipelineGating:
    """Test that diminished evaluator only runs for appropriate exercises."""

    def test_diminished_exercise_with_notes_produces_finding(self):
        session = make_session("exercises/diminished/orbit_awareness_C.ztprog")
        # C is outside C's dim orbit (B D F Ab)
        performed_notes = [0]  # C = pitch class 0

        findings = _evaluate_diminished_harmony(session, performed_notes)

        assert len(findings) == 1
        assert findings[0].type == "harmony"
        assert "diminished orbit" in findings[0].interpretation

    def test_diminished_exercise_clean_notes_no_finding(self):
        session = make_session("exercises/diminished/orbit_awareness_C.ztprog")
        # B, D, F, Ab are all in C's dim orbit
        performed_notes = [11, 2, 5, 8]

        findings = _evaluate_diminished_harmony(session, performed_notes)

        assert len(findings) == 0

    def test_non_diminished_exercise_no_evaluation(self):
        session = make_session("blues_turnaround_E.ztprog")
        # Even with "bad" notes, should not trigger diminished evaluator
        performed_notes = [0, 1, 2, 3]

        findings = _evaluate_diminished_harmony(session, performed_notes)

        assert len(findings) == 0

    def test_diminished_exercise_without_notes_no_finding(self):
        session = make_session("exercises/diminished/orbit_awareness_C.ztprog")

        # No notes provided - cannot evaluate
        findings = _evaluate_diminished_harmony(session, None)

        assert len(findings) == 0


class TestEvaluateSessionIntegration:
    """Test full evaluate_session() with diminished evaluator wired in."""

    def test_evaluate_session_includes_diminished_findings(self):
        session = make_session("exercises/diminished/orbit_awareness_C.ztprog")
        performed_notes = [0]  # C outside orbit

        result = evaluate_session(session, performed_notes)

        # Should have timing findings (from existing rules) + harmony finding
        harmony_findings = [f for f in result.findings if f.type == "harmony"]
        assert len(harmony_findings) == 1
        assert "diminished orbit" in harmony_findings[0].interpretation

    def test_evaluate_session_without_notes_still_works(self):
        session = make_session("exercises/diminished/orbit_awareness_C.ztprog")

        # No notes - diminished eval skipped, timing eval runs
        result = evaluate_session(session)

        # Should still have timing-based evaluation
        assert result.coach_version.startswith("coach-rules@")
        assert result.session_id == session.session_id

    def test_evaluate_session_non_diminished_exercise(self):
        session = make_session("blues_turnaround_E.ztprog")
        performed_notes = [0, 1, 2]  # Would be "bad" for diminished

        result = evaluate_session(session, performed_notes)

        # Should NOT have harmony findings from diminished evaluator
        harmony_findings = [f for f in result.findings if f.type == "harmony"]
        assert len(harmony_findings) == 0


class TestPipelineDocumentation:
    """Test that pipeline is correctly documented."""

    def test_evaluate_session_has_pipeline_docstring(self):
        doc = evaluate_session.__doc__
        assert "Pipeline" in doc or "Layer 1" in doc
        assert "timing" in doc.lower()
        assert "harmony" in doc.lower() or "diminished" in doc.lower()


class TestTimingGridPipeline:
    """Test timing grid evaluator integration in evaluate_session()."""

    def test_timing_exercise_with_deviations_produces_finding(self):
        session = make_session("timing_grid_basic.ztprog")
        expected_times = [0.0, 0.5, 1.0]
        performed_times = [0.0, 0.56, 1.0]  # 60ms late on second note

        result = evaluate_session(
            session,
            expected_times=expected_times,
            performed_times=performed_times,
        )

        timing_findings = [f for f in result.findings if f.type == "timing"]
        # Should have at least one finding from timing evaluator
        assert any("deviation" in f.interpretation.lower() or "late" in f.interpretation.lower()
                   for f in timing_findings)

    def test_timing_exercise_clean_no_finding(self):
        session = make_session("timing_grid_basic.ztprog")
        expected_times = [0.0, 0.5, 1.0]
        performed_times = [0.01, 0.51, 0.99]  # All within threshold

        result = evaluate_session(
            session,
            expected_times=expected_times,
            performed_times=performed_times,
        )

        # Should not have deviation findings
        deviation_findings = [f for f in result.findings
                             if "deviation" in f.interpretation.lower()]
        assert len(deviation_findings) == 0

    def test_non_timing_exercise_no_timing_evaluation(self):
        session = make_session("blues_turnaround_E.ztprog")
        expected_times = [0.0, 0.5]
        performed_times = [0.0, 0.6]  # Would be "bad" timing

        result = evaluate_session(
            session,
            expected_times=expected_times,
            performed_times=performed_times,
        )

        # Should NOT have timing grid deviation findings
        deviation_findings = [f for f in result.findings
                             if "deviation" in f.interpretation.lower()]
        assert len(deviation_findings) == 0

    def test_timing_threshold_override(self):
        session = make_session("timing_grid_basic.ztprog")
        expected_times = [0.0, 0.5]
        performed_times = [0.0, 0.525]  # 25ms late

        # Default 40ms - should pass
        result_default = evaluate_session(
            session,
            expected_times=expected_times,
            performed_times=performed_times,
            timing_threshold_ms=40.0,
        )
        deviation_default = [f for f in result_default.findings
                            if "deviation" in f.interpretation.lower()]
        assert len(deviation_default) == 0

        # Strict 20ms - should fail
        result_strict = evaluate_session(
            session,
            expected_times=expected_times,
            performed_times=performed_times,
            timing_threshold_ms=20.0,
        )
        deviation_strict = [f for f in result_strict.findings
                           if "deviation" in f.interpretation.lower()]
        assert len(deviation_strict) == 1
