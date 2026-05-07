"""
Tests for Practice Review builders.

Sprint 12: Tests for timeline, session review, and progress summary builders.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from sg_coach.practice_history import (
    PracticeHistoryEntry,
    PracticeHistoryStore,
    create_history_entry,
)
from sg_coach.practice_review import (
    build_practice_timeline,
    build_progress_summary,
    build_session_review,
    _count_findings_by_domain,
    _count_assignments_by_status,
    _top_diagnosis_codes,
    _generate_summary,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    CoachFinding,
    FindingEvidence,
    FocusRecommendation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    Severity,
)
from sg_spec.schemas.feedback_vocabulary import FeedbackDomain
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)


def make_session(session_id=None, instrument_id="guitar_1") -> SessionRecord:
    """Helper to create test session."""
    return SessionRecord(
        session_id=session_id or uuid4(),
        instrument_id=instrument_id,
        engine_version="test@1.0.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test_prog"),
        timing=SessionTiming(bpm=120.0, grid=8),
        duration_s=60,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=16,
            notes_played=14,
            notes_dropped=2,
        ),
    )


def make_evaluation(
    session_id=None,
    findings: list[CoachFinding] | None = None,
) -> CoachEvaluation:
    """Helper to create test evaluation."""
    return CoachEvaluation(
        session_id=session_id or uuid4(),
        coach_version="test@1.0.0",
        findings=findings or [],
        focus_recommendation=FocusRecommendation(
            concept="timing",
            reason="Practice timing accuracy",
        ),
        confidence=0.8,
    )


def make_finding(
    finding_type: str = "timing",
    code: DiagnosisCode | None = None,
) -> CoachFinding:
    """Helper to create test finding."""
    return CoachFinding(
        type=finding_type,
        severity=Severity.primary,
        interpretation="Test finding",
        code=code,
    )


def make_assignments(count: int = 1) -> AssembledPracticeAssignmentSet:
    """Helper to create test assignment set."""
    assignments = [
        AssembledPracticeAssignment(
            id=f"pa_test{i:06d}",
            assignment_type=PracticeAssignmentType.drill,
            status=PracticeAssignmentStatus.ready if i % 2 == 0 else PracticeAssignmentStatus.unresolved,
            title=f"Test Drill {i}",
            instructions="Practice this drill",
        )
        for i in range(count)
    ]
    return AssembledPracticeAssignmentSet(assignments=assignments)


def populate_store(
    store: PracticeHistoryStore,
    count: int = 1,
    user_id: str | None = None,
    with_findings: bool = False,
) -> list[PracticeHistoryEntry]:
    """Populate store with test entries."""
    entries = []
    for i in range(count):
        session = make_session()
        findings = []
        if with_findings:
            findings = [
                make_finding("timing", DiagnosisCode.TIMING_GRID_DEVIATION),
                make_finding("harmony", DiagnosisCode.DIM_ORBIT_VIOLATION),
            ]
        evaluation = make_evaluation(session.session_id, findings=findings)
        assignments = make_assignments(2)

        entry = store.append_session(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id=user_id,
        )
        entries.append(entry)

    return entries


class TestCountFindingsByDomain:
    """Test _count_findings_by_domain helper."""

    def test_none_evaluation(self):
        result = _count_findings_by_domain(None)
        assert result == {}

    def test_empty_findings(self):
        evaluation = make_evaluation(findings=[])
        result = _count_findings_by_domain(evaluation)
        assert result == {}

    def test_counts_by_domain(self):
        findings = [
            make_finding("timing"),
            make_finding("timing"),
            make_finding("harmony"),
        ]
        evaluation = make_evaluation(findings=findings)
        result = _count_findings_by_domain(evaluation)
        assert result["timing"] == 2
        assert result["harmony"] == 1


class TestCountAssignmentsByStatus:
    """Test _count_assignments_by_status helper."""

    def test_none_assignments(self):
        result = _count_assignments_by_status(None)
        assert result == {}

    def test_empty_assignments(self):
        assignments = AssembledPracticeAssignmentSet(assignments=[])
        result = _count_assignments_by_status(assignments)
        assert result == {}

    def test_counts_by_status(self):
        assignments = make_assignments(4)
        result = _count_assignments_by_status(assignments)
        assert result["ready"] == 2
        assert result["unresolved"] == 2


class TestTopDiagnosisCodes:
    """Test _top_diagnosis_codes helper."""

    def test_none_evaluation(self):
        result = _top_diagnosis_codes(None)
        assert result == []

    def test_empty_findings(self):
        evaluation = make_evaluation(findings=[])
        result = _top_diagnosis_codes(evaluation)
        assert result == []

    def test_findings_without_codes(self):
        findings = [make_finding("timing", code=None)]
        evaluation = make_evaluation(findings=findings)
        result = _top_diagnosis_codes(evaluation)
        assert result == []

    def test_returns_top_codes_by_frequency(self):
        findings = [
            make_finding("timing", DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding("timing", DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding("timing", DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding("harmony", DiagnosisCode.DIM_ORBIT_VIOLATION),
            make_finding("harmony", DiagnosisCode.DIM_ORBIT_VIOLATION),
            make_finding("other", DiagnosisCode.WRONG_NOTE),
        ]
        evaluation = make_evaluation(findings=findings)
        result = _top_diagnosis_codes(evaluation, limit=3)
        assert len(result) == 3
        assert result[0] == DiagnosisCode.TIMING_GRID_DEVIATION
        assert result[1] == DiagnosisCode.DIM_ORBIT_VIOLATION
        assert result[2] == DiagnosisCode.WRONG_NOTE

    def test_respects_limit(self):
        findings = [
            make_finding("timing", DiagnosisCode.TIMING_GRID_DEVIATION),
            make_finding("harmony", DiagnosisCode.DIM_ORBIT_VIOLATION),
            make_finding("other", DiagnosisCode.WRONG_NOTE),
        ]
        evaluation = make_evaluation(findings=findings)
        result = _top_diagnosis_codes(evaluation, limit=2)
        assert len(result) == 2


class TestGenerateSummary:
    """Test _generate_summary helper."""

    def test_none_both(self):
        result = _generate_summary(None, None)
        assert result is None

    def test_empty_both(self):
        evaluation = make_evaluation(findings=[])
        assignments = AssembledPracticeAssignmentSet(assignments=[])
        result = _generate_summary(evaluation, assignments)
        assert result is None

    def test_findings_only(self):
        findings = [
            make_finding("timing"),
            make_finding("timing"),
            make_finding("harmony"),
        ]
        evaluation = make_evaluation(findings=findings)
        result = _generate_summary(evaluation, None)
        assert result is not None
        assert "timing" in result
        assert "harmony" in result

    def test_assignments_only(self):
        assignments = make_assignments(2)
        result = _generate_summary(None, assignments)
        assert result is not None
        assert "2 assignments" in result

    def test_full_summary(self):
        findings = [make_finding("timing"), make_finding("timing")]
        evaluation = make_evaluation(findings=findings)
        assignments = make_assignments(1)
        result = _generate_summary(evaluation, assignments)
        assert result is not None
        assert "timing" in result
        assert "assignment" in result


class TestBuildSessionReview:
    """Test build_session_review function."""

    def test_returns_none_if_not_found(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        result = build_session_review(session_id="nonexistent", history_store=store)
        assert result is None

    def test_returns_session(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1)
        session_id = entries[0].session_id

        result = build_session_review(session_id=session_id, history_store=store)
        assert result is not None
        assert result.session_id == session_id
        assert result.session is not None

    def test_includes_evaluation(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1, with_findings=True)
        session_id = entries[0].session_id

        result = build_session_review(session_id=session_id, history_store=store)
        assert result.evaluation is not None

    def test_includes_assignments(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1)
        session_id = entries[0].session_id

        result = build_session_review(session_id=session_id, history_store=store)
        assert result.assignments is not None
        assert len(result.assignments.assignments) == 2

    def test_findings_by_domain_counts(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1, with_findings=True)
        session_id = entries[0].session_id

        result = build_session_review(session_id=session_id, history_store=store)
        assert "timing" in result.findings_by_domain
        assert "harmony" in result.findings_by_domain

    def test_assignment_status_counts(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1)
        session_id = entries[0].session_id

        result = build_session_review(session_id=session_id, history_store=store)
        assert "ready" in result.assignment_status_counts
        assert "unresolved" in result.assignment_status_counts

    def test_does_not_mutate_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        entries = populate_store(store, count=1)
        session_id = entries[0].session_id

        entries_before = store.all()
        build_session_review(session_id=session_id, history_store=store)
        entries_after = store.all()

        assert len(entries_before) == len(entries_after)


class TestBuildPracticeTimeline:
    """Test build_practice_timeline function."""

    def test_empty_store(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        result = build_practice_timeline(history_store=store)
        assert result.entries == []
        assert result.total_sessions == 0

    def test_includes_persisted_sessions(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=3)

        result = build_practice_timeline(history_store=store)
        assert len(result.entries) == 3
        assert result.total_sessions == 3

    def test_filters_by_user_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=2, user_id="user_a")
        populate_store(store, count=3, user_id="user_b")

        result = build_practice_timeline(history_store=store, user_id="user_a")
        assert len(result.entries) == 2
        assert result.total_sessions == 2
        assert all(e.user_id == "user_a" for e in result.entries)

    def test_respects_limit(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=5)

        result = build_practice_timeline(history_store=store, limit=2)
        assert len(result.entries) == 2
        assert result.total_sessions == 5

    def test_entries_sorted_by_timestamp_descending(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=3)

        result = build_practice_timeline(history_store=store)
        timestamps = [e.timestamp for e in result.entries]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_entries_include_finding_count(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=1, with_findings=True)

        result = build_practice_timeline(history_store=store)
        assert result.entries[0].finding_count == 2

    def test_entries_include_assignment_count(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=1)

        result = build_practice_timeline(history_store=store)
        assert result.entries[0].assignment_count == 2

    def test_entries_include_top_diagnosis_codes(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=1, with_findings=True)

        result = build_practice_timeline(history_store=store)
        assert len(result.entries[0].top_diagnosis_codes) > 0


class TestBuildProgressSummary:
    """Test build_progress_summary function."""

    def test_empty_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        result = build_progress_summary(history_store=store)
        assert result.session_count == 0
        assert result.total_findings == 0
        assert result.total_assignments == 0

    def test_counts_sessions(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=5)

        result = build_progress_summary(history_store=store)
        assert result.session_count == 5

    def test_counts_findings(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=3, with_findings=True)

        result = build_progress_summary(history_store=store)
        assert result.total_findings == 6

    def test_counts_assignments(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=3)

        result = build_progress_summary(history_store=store)
        assert result.total_assignments == 6

    def test_counts_diagnosis_codes(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=2, with_findings=True)

        result = build_progress_summary(history_store=store)
        assert DiagnosisCode.TIMING_GRID_DEVIATION.value in result.diagnosis_counts
        assert DiagnosisCode.DIM_ORBIT_VIOLATION.value in result.diagnosis_counts

    def test_recent_diagnosis_codes_from_most_recent(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=3, with_findings=True)

        result = build_progress_summary(history_store=store)
        assert len(result.recent_diagnosis_codes) > 0

    def test_filters_by_user_id(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=2, user_id="user_a")
        populate_store(store, count=3, user_id="user_b")

        result = build_progress_summary(history_store=store, user_id="user_a")
        assert result.session_count == 2
        assert result.user_id == "user_a"

    def test_does_not_mutate_history(self, tmp_path: Path):
        store = PracticeHistoryStore(tmp_path / "history.jsonl")
        populate_store(store, count=2)

        entries_before = store.all()
        build_progress_summary(history_store=store)
        entries_after = store.all()

        assert len(entries_before) == len(entries_after)


class TestSchemaExports:
    """Test that review functions are exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            build_practice_timeline,
            build_progress_summary,
            build_session_review,
        )
        assert build_session_review is not None
        assert build_practice_timeline is not None
        assert build_progress_summary is not None
