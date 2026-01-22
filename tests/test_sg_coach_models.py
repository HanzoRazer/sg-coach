from __future__ import annotations

from uuid import uuid4

import pytest

from sg_coach.schemas import (
    CoachEvaluation,
    CoachFinding,
    FocusRecommendation,
    FindingEvidence,
    PracticeAssignment,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    PerformanceSummary,
    SuccessCriteria,
    AssignmentConstraints,
    AssignmentFocus,
)


def test_session_record_accepts_minimal_valid():
    sid = uuid4()
    rec = SessionRecord(
        session_id=sid,
        instrument_id="sg-000142",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="salsa_minor_Dm", hash="sha256:abc123"),
        timing=SessionTiming(bpm=110, grid=16, strict=True, late_drop_ms=35, ghost_vel_max=22, panic_enabled=True),
        duration_s=120,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=10,
            notes_played=10,
            notes_dropped=0,
            error_by_step={"0": 4.2, "7": 18.1},
        ),
    )
    assert rec.session_id == sid


def test_session_record_rejects_bad_error_by_step_key():
    with pytest.raises(ValueError):
        SessionRecord(
            session_id=uuid4(),
            instrument_id="sg-1",
            engine_version="zt-band@0.2.0",
            program_ref=ProgramRef(type=ProgramType.ztprog, name="x"),
            timing=SessionTiming(bpm=120, grid=8),
            duration_s=1,
            performance=PerformanceSummary(
                bars_played=1,
                notes_expected=1,
                notes_played=1,
                notes_dropped=0,
                error_by_step={"9": 1.0},  # grid=8 => max step 7
            ),
        )


def test_coach_evaluation_requires_focus_and_confidence():
    ev = CoachEvaluation(
        session_id=uuid4(),
        coach_version="coach-rules@0.1.0",
        findings=[
            CoachFinding(
                type="timing",
                severity="primary",
                evidence=FindingEvidence(step=7, mean_error_ms=31.8),
                interpretation="Late on &2 relative to clave",
            )
        ],
        strengths=["Stable tempo after bar 16"],
        weaknesses=["Drag on off-beat &2"],
        focus_recommendation=FocusRecommendation(concept="clave_alignment", reason="Error concentrated on clave off-beats"),
        confidence=0.87,
    )
    assert ev.confidence == pytest.approx(0.87)


def test_practice_assignment_accepts_valid_and_enforces_program_type():
    a = PracticeAssignment(
        assignment_id=uuid4(),
        session_id=uuid4(),
        program=ProgramRef(type=ProgramType.ztprog, name="salsa_minor_Dm"),
        constraints=AssignmentConstraints(
            tempo_start=90,
            tempo_target=110,
            tempo_step=5,
            strict=True,
            strict_window_ms=25,
            bars_per_loop=2,
            repetitions=8,
        ),
        focus=AssignmentFocus(primary="clave_offbeat", secondary="left_hand_relaxation"),
        success_criteria=SuccessCriteria(max_mean_error_ms=15.0, max_late_drops=1),
        coach_prompt={"mode": "optional", "message": "Lock your &2 to the clave."},
        expires_after_sessions=3,
    )
    assert a.constraints.tempo_target == 110

    with pytest.raises(ValueError):
        PracticeAssignment(
            assignment_id=uuid4(),
            session_id=uuid4(),
            program=ProgramRef(type=ProgramType.ztplay, name="playlist_1"),
            constraints=AssignmentConstraints(
                tempo_start=90, tempo_target=95, tempo_step=5, bars_per_loop=2, repetitions=2
            ),
            focus=AssignmentFocus(primary="x"),
            success_criteria=SuccessCriteria(max_mean_error_ms=20.0, max_late_drops=3),
        )
