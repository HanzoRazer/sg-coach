"""
Tests for coach_schema: Session -> Coach -> Assignment spine.

Validates the three-layer separation:
- SessionRecord: immutable facts
- CoachEvaluation: grounded interpretation
- PracticeAssignment: constrained intent

Updated to test unified schema from shared.coach_schemas.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from zt_band.coach_schema import (
    AssignmentConstraints,
    AssignmentFocus,
    ClaveKind,
    CoachEvaluation,
    CoachFinding,
    CoachPrompt,
    FindingEvidence,
    FocusRecommendation,
    PerformanceSummary,
    PracticeAssignment,
    ProgramRef,
    ProgramType,
    SessionEvents,
    SessionRecord,
    SessionTiming,
    Severity,
    SuccessCriteria,
    TimingErrorStats,
    validate_assignment_program_exists,
    validate_coach_references_session,
    # Legacy aliases should still work
    Finding,
    TimingConfig,
    PerformanceMetrics,
    AssignmentProgram,
    PracticeConstraints,
    PracticeFocus,
)


# ============================================================================
# SessionRecord Tests
# ============================================================================

TEST_UUID = UUID("12345678-1234-1234-1234-123456789abc")


def make_valid_session() -> SessionRecord:
    """Factory for valid SessionRecord."""
    return SessionRecord(
        session_id=TEST_UUID,
        instrument_id="sg-000142",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="salsa_minor_dm",
            hash="sha256:" + "a" * 64,
        ),
        timing=SessionTiming(bpm=110, grid=16, clave=ClaveKind.son_2_3, strict=True, late_drop_ms=35),
        duration_s=312,
        performance=PerformanceSummary(
            bars_played=64,
            notes_expected=512,
            notes_played=489,
            notes_dropped=23,
            timing_error_ms=TimingErrorStats(mean=18.4, std=9.2, max=41.7),
            error_by_step={"0": 4.1, "3": 22.5, "7": 31.8, "11": 19.4},
        ),
        events=SessionEvents(late_drops=7, panic_triggered=False),
        created_at=datetime.now(timezone.utc),
    )


def test_session_record_valid():
    """Valid session record passes validation."""
    session = make_valid_session()
    assert session.session_id == TEST_UUID
    assert session.performance.notes_dropped == 23


def test_session_record_rejects_free_text():
    """Session record has no free text fields - schema enforces this."""
    session = make_valid_session()
    # Attempt to add extra field should fail
    with pytest.raises(ValidationError):
        SessionRecord(
            **session.model_dump(),
            user_notes="This is free text",  # NOT ALLOWED
        )


def test_session_record_rejects_empty_instrument_id():
    """Instrument ID must have at least 1 character."""
    data = make_valid_session().model_dump()
    data["instrument_id"] = ""
    with pytest.raises(ValidationError):
        SessionRecord(**data)


def test_session_record_rejects_invalid_hash():
    """Program hash must start with sha256:."""
    with pytest.raises(ValidationError):
        ProgramRef(
            type=ProgramType.ztprog,
            name="test_prog",
            hash="md5:abc123",  # Wrong format
        )


def test_timing_error_stats_non_negative():
    """Timing error std/max must be non-negative."""
    with pytest.raises(ValidationError):
        TimingErrorStats(mean=50.0, std=-10.0, max=60.0)  # negative std


def test_timing_grid_must_be_8_or_16():
    """Grid must be exactly 8 or 16."""
    with pytest.raises(ValidationError):
        SessionTiming(bpm=120, grid=4)  # Not allowed


# ============================================================================
# CoachEvaluation Tests
# ============================================================================

def make_valid_evaluation() -> CoachEvaluation:
    """Factory for valid CoachEvaluation."""
    return CoachEvaluation(
        session_id=TEST_UUID,
        coach_version="coach-rules@0.1.0",
        findings=[
            CoachFinding(
                type="timing",
                severity=Severity.primary,
                evidence=FindingEvidence(step=7, mean_error_ms=31.8),
                interpretation="Late on &2 relative to clave",
            )
        ],
        strengths=["Stable tempo after bar 16", "Low variance on downbeats"],
        weaknesses=["Consistent drag on off-beat &2"],
        focus_recommendation=FocusRecommendation(
            concept="clave_alignment",
            reason="Timing error concentrated on clave off-beats",
        ),
        confidence=0.87,
        created_at=datetime.now(timezone.utc),
    )


def test_coach_evaluation_valid():
    """Valid evaluation passes."""
    evaluation = make_valid_evaluation()
    assert evaluation.confidence == 0.87
    assert len(evaluation.findings) == 1


def test_coach_evaluation_requires_confidence():
    """Confidence is required - forces honesty."""
    with pytest.raises(ValidationError):
        CoachEvaluation(
            session_id=TEST_UUID,
            coach_version="coach-rules@0.1.0",
            findings=[],
            focus_recommendation=FocusRecommendation(concept="test", reason="test"),
            # confidence missing
            created_at=datetime.now(timezone.utc),
        )


def test_coach_evaluation_requires_focus_recommendation():
    """Focus recommendation is required."""
    with pytest.raises(ValidationError):
        CoachEvaluation(
            session_id=TEST_UUID,
            coach_version="coach-rules@0.1.0",
            findings=[],
            confidence=0.5,
            # focus_recommendation missing
            created_at=datetime.now(timezone.utc),
        )


def test_coach_evaluation_bounded_text():
    """Strengths/weaknesses have length limits (160 chars)."""
    with pytest.raises(ValidationError):
        CoachEvaluation(
            session_id=TEST_UUID,
            coach_version="coach-rules@0.1.0",
            findings=[],
            strengths=["x" * 200],  # Too long (> 160)
            focus_recommendation=FocusRecommendation(concept="test", reason="test"),
            confidence=0.5,
            created_at=datetime.now(timezone.utc),
        )


def test_finding_interpretation_bounded():
    """Finding interpretation has max length of 240 chars."""
    with pytest.raises(ValidationError):
        CoachFinding(
            type="timing",
            severity=Severity.primary,
            evidence=FindingEvidence(step=7, mean_error_ms=31.8),
            interpretation="x" * 300,  # Too long
        )


# ============================================================================
# PracticeAssignment Tests
# ============================================================================

def make_valid_assignment() -> PracticeAssignment:
    """Factory for valid PracticeAssignment."""
    return PracticeAssignment(
        assignment_id=uuid4(),
        session_id=TEST_UUID,
        program=ProgramRef(type=ProgramType.ztprog, name="salsa_minor_dm"),
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
        success_criteria=SuccessCriteria(max_mean_error_ms=15, max_late_drops=1),
        coach_prompt=CoachPrompt(
            mode="optional",
            message="Lock your &2 to the clave - don't rush home.",
        ),
        expires_after_sessions=3,
    )


def test_practice_assignment_valid():
    """Valid assignment passes."""
    assignment = make_valid_assignment()
    assert assignment.constraints.tempo_start == 90
    assert assignment.focus.primary == "clave_offbeat"


def test_practice_assignment_rejects_extra_fields():
    """Assignment cannot invent new fields."""
    with pytest.raises(ValidationError):
        PracticeAssignment(
            **make_valid_assignment().model_dump(),
            new_theory_concept="invented_by_ai",  # NOT ALLOWED
        )


def test_practice_assignment_rejects_ztplay():
    """Assignment program.type must be ztprog or ztex, not ztplay."""
    with pytest.raises(ValidationError):
        PracticeAssignment(
            assignment_id=uuid4(),
            session_id=TEST_UUID,
            program=ProgramRef(type=ProgramType.ztplay, name="test"),  # ztplay not allowed
            constraints=AssignmentConstraints(
                tempo_start=90, tempo_target=110, tempo_step=5,
                bars_per_loop=2, repetitions=4,
            ),
            focus=AssignmentFocus(primary="timing"),
            success_criteria=SuccessCriteria(max_mean_error_ms=20, max_late_drops=2),
        )


def test_constraints_numeric():
    """Constraints are numeric and bounded."""
    # BPM too high
    with pytest.raises(ValidationError):
        AssignmentConstraints(
            tempo_start=500, tempo_target=110, tempo_step=5,
            bars_per_loop=4, repetitions=4,
        )

    # Repetitions out of range
    with pytest.raises(ValidationError):
        AssignmentConstraints(
            tempo_start=90, tempo_target=110, tempo_step=5,
            bars_per_loop=4, repetitions=1000,  # max is 999
        )


def test_constraints_tempo_ramp():
    """Target tempo must be >= start tempo."""
    with pytest.raises(ValidationError):
        AssignmentConstraints(
            tempo_start=120, tempo_target=90, tempo_step=5,  # target < start
            bars_per_loop=4, repetitions=4,
        )


# ============================================================================
# Cross-Layer Validation Tests
# ============================================================================

def test_coach_references_session():
    """Coach findings must reference actual session data."""
    session = make_valid_session()
    evaluation = make_valid_evaluation()

    # Update evaluation to have matching session_id
    evaluation = evaluation.model_copy(update={"session_id": session.session_id})

    # Should pass - step 7 exists in session
    validate_coach_references_session(evaluation, session)


def test_coach_rejects_nonexistent_step():
    """Coach cannot reference steps not in session."""
    session = make_valid_session()
    # Session has steps: 0, 3, 7, 11 - so step 5 doesn't exist in session
    evaluation = CoachEvaluation(
        session_id=session.session_id,
        coach_version="coach-rules@0.1.0",
        findings=[
            CoachFinding(
                type="timing",
                severity=Severity.primary,
                evidence=FindingEvidence(step=5, mean_error_ms=50.0),  # Step 5 not in session data
                interpretation="Error on step 5",
            )
        ],
        focus_recommendation=FocusRecommendation(concept="test", reason="test"),
        confidence=0.5,
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError) as exc_info:
        validate_coach_references_session(evaluation, session)
    assert "step 5" in str(exc_info.value)


def test_coach_session_id_mismatch():
    """Coach must reference correct session."""
    session = make_valid_session()
    evaluation = make_valid_evaluation()
    different_uuid = UUID("00000000-0000-0000-0000-000000000000")
    evaluation = evaluation.model_copy(update={"session_id": different_uuid})

    with pytest.raises(ValueError) as exc_info:
        validate_coach_references_session(evaluation, session)
    assert "must match" in str(exc_info.value)


def test_assignment_program_exists():
    """Assignment must reference existing program."""
    assignment = make_valid_assignment()
    available = {"salsa_minor_dm", "swing_basic", "bossa_basic"}

    # Should pass
    validate_assignment_program_exists(assignment, available)


def test_assignment_rejects_unknown_program():
    """Assignment cannot reference nonexistent program."""
    assignment = make_valid_assignment()
    assignment = assignment.model_copy(
        update={"program": ProgramRef(type=ProgramType.ztprog, name="invented_program")}
    )
    available = {"salsa_minor_dm", "swing_basic"}

    with pytest.raises(ValueError) as exc_info:
        validate_assignment_program_exists(assignment, available)
    assert "unknown program" in str(exc_info.value)


# ============================================================================
# Layer Boundary Tests (The Key Mental Model)
# ============================================================================

def test_session_is_truth():
    """Session layer is pure fact - no interpretation fields."""
    session = make_valid_session()
    # These fields should NOT exist on SessionRecord
    assert not hasattr(session, "interpretation")
    assert not hasattr(session, "recommendation")
    assert not hasattr(session, "coach_message")


def test_coach_is_interpretation():
    """Coach layer interprets but cannot mutate music."""
    evaluation = make_valid_evaluation()
    # These fields should NOT exist on CoachEvaluation
    assert not hasattr(evaluation, "chords")
    assert not hasattr(evaluation, "style")
    assert not hasattr(evaluation, "notes")


def test_assignment_is_intent():
    """Assignment layer constrains but cannot invent theory."""
    assignment = make_valid_assignment()
    # Program reference only - no chord/note invention
    assert hasattr(assignment, "program")
    assert not hasattr(assignment, "new_chords")
    assert not hasattr(assignment, "custom_theory")


# ============================================================================
# Legacy Alias Tests
# ============================================================================

def test_legacy_aliases_work():
    """Legacy class names should still work for backward compatibility."""
    # TimingConfig is alias for SessionTiming
    config = TimingConfig(bpm=120, grid=16)
    assert isinstance(config, SessionTiming)

    # PerformanceMetrics is alias for PerformanceSummary
    perf = PerformanceMetrics(
        bars_played=10, notes_expected=100, notes_played=95, notes_dropped=5,
    )
    assert isinstance(perf, PerformanceSummary)

    # Finding is alias for CoachFinding
    finding = Finding(
        type="timing", severity=Severity.info,
        interpretation="Test finding",
    )
    assert isinstance(finding, CoachFinding)

    # AssignmentProgram is alias for ProgramRef
    prog = AssignmentProgram(type=ProgramType.ztprog, name="test")
    assert isinstance(prog, ProgramRef)

    # PracticeConstraints is alias for AssignmentConstraints
    constraints = PracticeConstraints(
        tempo_start=90, tempo_target=120, tempo_step=5,
        bars_per_loop=4, repetitions=8,
    )
    assert isinstance(constraints, AssignmentConstraints)

    # PracticeFocus is alias for AssignmentFocus
    focus = PracticeFocus(primary="timing")
    assert isinstance(focus, AssignmentFocus)
