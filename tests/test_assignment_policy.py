"""
Tests for sg_coach.assignment_policy (Mode-1 deterministic planner).
"""
from __future__ import annotations

from uuid import uuid4

from sg_coach.assignment_policy import plan_assignment
from sg_coach.schemas import (
    CoachEvaluation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    TimingErrorStats,
)


def _make_evaluation(concept: str = "grid_alignment", reason: str = "test") -> CoachEvaluation:
    """Minimal CoachEvaluation for testing."""
    return CoachEvaluation.model_validate({
        "session_id": str(uuid4()),
        "coach_version": "coach-rules@0.1.0",
        "focus_recommendation": {"concept": concept, "reason": reason},
        "confidence": 0.85,
    })


def _make_session(mean_ms: float, *, duration_s: int = 240, grid: int = 16) -> SessionRecord:
    """Minimal SessionRecord for testing."""
    return SessionRecord(
        session_id=uuid4(),
        instrument_id="sg-000142",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="salsa_minor_Dm",
            hash="sha256:abc123",
        ),
        timing=SessionTiming(
            bpm=110,
            grid=grid,
            strict=True,
            late_drop_ms=35,
            ghost_vel_max=22,
            panic_enabled=True,
        ),
        duration_s=duration_s,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=100,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=mean_ms, std=6.0, max=40.0),
            error_by_step={"7": 32.0} if mean_ms >= 14.0 else {},
        ),
        events={"late_drops": 2, "panic_triggered": False},
    )


def test_plan_assignment_end_to_end():
    """Full pipeline: session -> evaluation -> assignment."""
    s = _make_session(14.0)
    ev = _make_evaluation()
    a = plan_assignment(session=s, evaluation=ev)

    assert a.program.name == "salsa_minor_Dm"
    assert a.constraints.tempo_target == 110
    assert a.constraints.bars_per_loop == 2
    assert a.constraints.repetitions >= 1
    assert a.success_criteria.max_mean_error_ms > 0


def test_plan_assignment_short_session_reduces_reps():
    """Short sessions (<=180s) get fewer repetitions."""
    s = _make_session(14.0, duration_s=120)
    ev = _make_evaluation()
    a = plan_assignment(session=s, evaluation=ev)

    # Short session config: 6 reps (vs default 8)
    assert a.constraints.repetitions == 6


def test_plan_assignment_makes_strict_window_when_strict():
    """Strict mode produces a valid strict_window_ms."""
    s = _make_session(19.5)
    ev = _make_evaluation()
    a = plan_assignment(session=s, evaluation=ev)

    assert a.constraints.strict is True
    assert a.constraints.strict_window_ms is not None
    assert 15 <= a.constraints.strict_window_ms <= 60
