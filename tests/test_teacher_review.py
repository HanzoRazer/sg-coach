"""
Tests for Teacher Review Builder and Store.

Sprint 19: Teacher-facing review layer.
"""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from sg_spec.schemas.coach_finding import DiagnosisCode
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
    TargetSpan,
)
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)
from sg_spec.schemas.teacher_review import (
    TeacherAnnotation,
    TeacherAnnotationType,
    TeacherRecommendation,
    TeacherRecommendationType,
    TeacherReview,
)

from sg_coach import COACH_VERSION
from sg_coach.practice_history import PracticeHistoryStore
from sg_coach.teacher_review import (
    TEACHER_REVIEW_VERSION,
    build_teacher_review,
    create_teacher_annotation,
    create_teacher_recommendation,
)
from sg_coach.teacher_review_store import TeacherReviewStore


def _make_session(session_id=None, duration_s: int = 60) -> SessionRecord:
    """Create a minimal session record for testing."""
    return SessionRecord(
        session_id=session_id or uuid4(),
        instrument_id="sg-test",
        engine_version="test@1.0.0",
        program_ref=ProgramRef(type=ProgramType.ztprog, name="test"),
        timing=SessionTiming(bpm=120, grid=16),
        duration_s=duration_s,
        performance=PerformanceSummary(
            bars_played=4,
            notes_expected=10,
            notes_played=10,
            notes_dropped=0,
        ),
    )


def _make_evaluation(session_id: str) -> CoachEvaluation:
    """Create a minimal evaluation for testing."""
    return CoachEvaluation(
        session_id=session_id,
        coach_version=COACH_VERSION,
        findings=[
            CoachFinding(
                type="timing",
                code=DiagnosisCode.TIMING_GRID_DEVIATION,
                severity=Severity.primary,
                interpretation="Timing issue",
                evidence=FindingEvidence(),
            ),
        ],
        focus_recommendation=FocusRecommendation(
            concept="Timing",
            reason="Work on timing",
        ),
        strengths=[],
        weaknesses=[],
        confidence=0.9,
    )


def _make_assignments() -> AssembledPracticeAssignmentSet:
    """Create a minimal assignment set for testing."""
    return AssembledPracticeAssignmentSet(
        assignments=[
            AssembledPracticeAssignment(
                id="assign_001",
                assignment_type=PracticeAssignmentType.drill,
                status=PracticeAssignmentStatus.ready,
                title="Metronome Drill",
                instructions="Practice with metronome",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
        ],
    )


@pytest.fixture
def temp_history_file():
    """Create a temporary history file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def populated_history(temp_history_file) -> tuple[PracticeHistoryStore, str]:
    """Create a history store with one session."""
    store = PracticeHistoryStore(temp_history_file)
    session = _make_session()
    session_id = str(session.session_id)
    evaluation = _make_evaluation(session_id)
    assignments = _make_assignments()

    store.append_session(
        session=session,
        evaluation=evaluation,
        assignments=assignments,
        user_id="student_001",
    )

    return store, session_id


class TestBuildTeacherReview:
    """Test build_teacher_review function."""

    def test_returns_teacher_review(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)
        assert isinstance(review, TeacherReview)

    def test_includes_dashboard_by_default(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)
        assert review.dashboard is not None

    def test_excludes_dashboard_when_disabled(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            include_dashboard=False,
        )
        assert review.dashboard is None

    def test_includes_session_review_when_session_id_provided(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            session_id=session_id,
        )
        assert review.session_review is not None
        assert review.session_review.session_id == session_id

    def test_includes_playback_when_session_id_provided(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            session_id=session_id,
        )
        assert review.playback is not None

    def test_excludes_playback_when_disabled(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            session_id=session_id,
            include_playback=False,
        )
        assert review.playback is None

    def test_handles_missing_session_gracefully(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            session_id="nonexistent_session",
        )
        assert review.session_review is None
        assert review.playback is None
        assert review.dashboard is not None

    def test_preserves_teacher_id(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            teacher_id="teacher_001",
        )
        assert review.teacher_id == "teacher_001"

    def test_preserves_student_id(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(
            history_store=store,
            student_id="student_001",
        )
        assert review.student_id == "student_001"

    def test_annotations_default_empty(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)
        assert review.annotations == []

    def test_recommendations_default_empty(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)
        assert review.recommendations == []

    def test_version_is_set(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)
        assert review.version == TEACHER_REVIEW_VERSION


class TestCreateTeacherAnnotation:
    """Test create_teacher_annotation helper."""

    def test_generates_id_with_ta_prefix(self):
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Good work",
        )
        assert annotation.id is not None
        assert annotation.id.startswith("ta_")
        assert len(annotation.id) == 15  # ta_ + 12 hex chars

    def test_preserves_all_ids(self):
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.correction,
            text="Watch the timing",
            teacher_id="teacher_001",
            student_id="student_001",
            session_id="session_001",
            finding_id="finding_001",
            assignment_id="assign_001",
        )
        assert annotation.teacher_id == "teacher_001"
        assert annotation.student_id == "student_001"
        assert annotation.session_id == "session_001"
        assert annotation.finding_id == "finding_001"
        assert annotation.assignment_id == "assign_001"

    def test_metadata_defaults_empty(self):
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Test",
        )
        assert annotation.metadata == {}

    def test_preserves_metadata(self):
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Test",
            metadata={"severity": "minor"},
        )
        assert annotation.metadata["severity"] == "minor"

    def test_preserves_target_span(self):
        span = TargetSpan(start_time_sec=5.0, end_time_sec=7.0)
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.correction,
            text="Check this section",
            target_span=span,
        )
        assert annotation.target_span is not None
        assert annotation.target_span.start_time_sec == 5.0

    def test_timestamp_is_set(self):
        before = datetime.now(timezone.utc)
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Test",
        )
        after = datetime.now(timezone.utc)
        assert before <= annotation.timestamp <= after

    def test_all_annotation_types(self):
        for atype in TeacherAnnotationType:
            annotation = create_teacher_annotation(
                annotation_type=atype,
                text="Test",
            )
            assert annotation.annotation_type == atype


class TestCreateTeacherRecommendation:
    """Test create_teacher_recommendation helper."""

    def test_generates_id_with_tr_prefix(self):
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Add metronome drill",
        )
        assert rec.id is not None
        assert rec.id.startswith("tr_")
        assert len(rec.id) == 15  # tr_ + 12 hex chars

    def test_preserves_related_ids(self):
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.modify_assignment,
            text="Slow down tempo",
            teacher_id="teacher_001",
            student_id="student_001",
            session_id="session_001",
            related_goal_id="goal_001",
            related_assignment_id="assign_001",
            related_finding_ids=["finding_001", "finding_002"],
        )
        assert rec.teacher_id == "teacher_001"
        assert rec.student_id == "student_001"
        assert rec.session_id == "session_001"
        assert rec.related_goal_id == "goal_001"
        assert rec.related_assignment_id == "assign_001"
        assert rec.related_finding_ids == ["finding_001", "finding_002"]

    def test_priority_preserved(self):
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Important drill",
            priority=8,
        )
        assert rec.priority == 8

    def test_priority_defaults_zero(self):
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Test",
        )
        assert rec.priority == 0

    def test_metadata_defaults_empty(self):
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Test",
        )
        assert rec.metadata == {}

    def test_timestamp_is_set(self):
        before = datetime.now(timezone.utc)
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Test",
        )
        after = datetime.now(timezone.utc)
        assert before <= rec.timestamp <= after

    def test_all_recommendation_types(self):
        for rtype in TeacherRecommendationType:
            rec = create_teacher_recommendation(
                recommendation_type=rtype,
                text="Test",
            )
            assert rec.recommendation_type == rtype


class TestTeacherReviewContainsAnnotations:
    """Test that TeacherReview can contain annotations."""

    def test_review_with_manually_added_annotations(self, populated_history):
        store, session_id = populated_history
        review = build_teacher_review(history_store=store)

        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.encouragement,
            text="Great job!",
        )
        review_with_annotations = TeacherReview(
            **{
                **review.model_dump(),
                "annotations": [annotation],
            }
        )
        assert len(review_with_annotations.annotations) == 1


class TestTeacherReviewStore:
    """Test TeacherReviewStore."""

    @pytest.fixture
    def temp_store_file(self):
        """Create a temporary store file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_append_annotation_writes_jsonl(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        annotation = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Test annotation",
            student_id="student_001",
        )
        store.append_annotation(annotation)

        with temp_store_file.open("r") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["type"] == "annotation"
            assert data["data"]["text"] == "Test annotation"

    def test_append_recommendation_writes_jsonl(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        rec = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Test recommendation",
            student_id="student_001",
        )
        store.append_recommendation(rec)

        with temp_store_file.open("r") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["type"] == "recommendation"
            assert data["data"]["text"] == "Test recommendation"

    def test_list_annotations_returns_all(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        a1 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="First",
        )
        a2 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.correction,
            text="Second",
        )
        store.append_annotation(a1)
        store.append_annotation(a2)

        annotations = store.list_annotations()
        assert len(annotations) == 2

    def test_list_annotations_filters_by_student_id(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        a1 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="For student 1",
            student_id="student_001",
        )
        a2 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="For student 2",
            student_id="student_002",
        )
        store.append_annotation(a1)
        store.append_annotation(a2)

        filtered = store.list_annotations(student_id="student_001")
        assert len(filtered) == 1
        assert filtered[0].text == "For student 1"

    def test_list_annotations_filters_by_session_id(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        a1 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Session 1",
            session_id="session_001",
        )
        a2 = create_teacher_annotation(
            annotation_type=TeacherAnnotationType.note,
            text="Session 2",
            session_id="session_002",
        )
        store.append_annotation(a1)
        store.append_annotation(a2)

        filtered = store.list_annotations(session_id="session_001")
        assert len(filtered) == 1
        assert filtered[0].text == "Session 1"

    def test_list_recommendations_returns_all(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        r1 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="First",
        )
        r2 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.defer_goal,
            text="Second",
        )
        store.append_recommendation(r1)
        store.append_recommendation(r2)

        recommendations = store.list_recommendations()
        assert len(recommendations) == 2

    def test_list_recommendations_filters_by_student_id(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        r1 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="For student 1",
            student_id="student_001",
        )
        r2 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="For student 2",
            student_id="student_002",
        )
        store.append_recommendation(r1)
        store.append_recommendation(r2)

        filtered = store.list_recommendations(student_id="student_001")
        assert len(filtered) == 1
        assert filtered[0].text == "For student 1"

    def test_list_recommendations_filters_by_session_id(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        r1 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Session 1",
            session_id="session_001",
        )
        r2 = create_teacher_recommendation(
            recommendation_type=TeacherRecommendationType.add_assignment,
            text="Session 2",
            session_id="session_002",
        )
        store.append_recommendation(r1)
        store.append_recommendation(r2)

        filtered = store.list_recommendations(session_id="session_001")
        assert len(filtered) == 1
        assert filtered[0].text == "Session 1"

    def test_empty_store_returns_empty_lists(self, temp_store_file):
        store = TeacherReviewStore(temp_store_file)
        assert store.list_annotations() == []
        assert store.list_recommendations() == []


class TestModuleExports:
    """Test that teacher review is exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            TEACHER_REVIEW_VERSION,
            TeacherReviewStore,
            build_teacher_review,
            create_teacher_annotation,
            create_teacher_recommendation,
        )
        assert TEACHER_REVIEW_VERSION == "0.1"
        assert callable(build_teacher_review)
        assert callable(create_teacher_annotation)
        assert callable(create_teacher_recommendation)
        assert TeacherReviewStore is not None
