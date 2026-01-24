"""
Tests for Mode-1 coach policy (evaluate_session).
"""
from __future__ import annotations

from uuid import uuid4

from sg_coach.schemas import (
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    TimingErrorStats,
    SessionEvents,
    ProgramRef,
    ProgramType,
    Severity,
)
from sg_coach.coach_policy import evaluate_session, STEP_ERROR_THRESHOLD_MS


def _session(
    error_by_step: dict | None = None,
    mean_error: float = 12.0,
    notes_dropped: int = 0,
) -> SessionRecord:
    """Create a test session with sensible defaults."""
    if error_by_step is None:
        error_by_step = {}

    return SessionRecord(
        session_id=uuid4(),
        instrument_id="test-guitar-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="golden_vector_program",
        ),
        timing=SessionTiming(
            bpm=120.0,
            grid=16,
        ),
        duration_s=300,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=100 - notes_dropped,
            notes_dropped=notes_dropped,
            timing_error_ms=TimingErrorStats(mean=mean_error, std=8.0, max=38.0),
            error_by_step=error_by_step,
        ),
        events=SessionEvents(late_drops=0, panic_triggered=False),
    )


def test_mode1_finds_worst_step_above_threshold():
    """Step with high error should produce a primary finding."""
    # Step 8 has error above threshold
    s = _session(error_by_step={
        "0": 5.0,
        "4": -10.0,
        "8": 45.0,  # Above threshold
        "12": 8.0,
    })
    ev = evaluate_session(s)

    assert len(ev.findings) >= 1
    primary = ev.findings[0]
    assert primary.severity == Severity.primary
    assert primary.type == "timing"
    assert primary.evidence.step == 8
    assert "step 8" in primary.interpretation.lower()


def test_mode1_no_findings_when_all_below_threshold():
    """No timing findings when all steps are below threshold."""
    s = _session(error_by_step={
        "0": 5.0,
        "4": -10.0,
        "8": 15.0,
        "12": -8.0,
    })
    ev = evaluate_session(s)

    # Should have no timing findings
    timing_findings = [f for f in ev.findings if f.type == "timing"]
    assert len(timing_findings) == 0
    assert "Consistent timing" in ev.strengths[0]


def test_mode1_finds_dropped_notes():
    """Dropped notes should produce a finding."""
    s = _session(notes_dropped=15)  # 15% drop rate
    ev = evaluate_session(s)

    drop_findings = [f for f in ev.findings if f.type == "consistency"]
    assert len(drop_findings) == 1
    assert drop_findings[0].evidence.metric == "notes_dropped"
    assert drop_findings[0].evidence.value == 15


def test_mode1_focus_recommendation_from_primary():
    """Focus recommendation should be derived from primary finding."""
    s = _session(error_by_step={"8": 50.0})  # High error on step 8
    ev = evaluate_session(s)

    assert "step_8" in ev.focus_recommendation.concept
    assert "step 8" in ev.focus_recommendation.reason.lower()


def test_mode1_confidence_increases_with_data():
    """More per-step data should increase confidence."""
    s_sparse = _session(error_by_step={"0": 5.0})
    s_dense = _session(error_by_step={str(i): 5.0 for i in range(16)})

    ev_sparse = evaluate_session(s_sparse)
    ev_dense = evaluate_session(s_dense)

    assert ev_dense.confidence > ev_sparse.confidence
