"""
Tests for TeacherSchedulingMediationStore.

Sprint 32: Teacher-Governed Adaptive Scheduling.
"""
from datetime import datetime, timezone, timedelta

import pytest

from sg_spec.schemas.teacher_scheduling_mediation import (
    MediationAction,
    TeacherSchedulingMediation,
    TeacherSchedulingOverride,
)
from sg_spec.schemas.practice_queue import PracticeQueuePriority

from sg_coach.teacher_scheduling_mediation_store import (
    TEACHER_SCHEDULING_MEDIATION_STORE_VERSION,
    TeacherSchedulingMediationStore,
)


def make_mediation(
    mediation_id: str = "tsm_test123",
    recommendation_id: str = "asr_xyz789",
    teacher_id: str = "teacher_001",
    student_id: str | None = None,
    action: MediationAction = MediationAction.approve,
    rationale: str | None = None,
    created_at: datetime | None = None,
) -> TeacherSchedulingMediation:
    """Create a test mediation."""
    if action in {MediationAction.reject, MediationAction.defer, MediationAction.approve_modified}:
        rationale = rationale or "Required rationale"

    override = None
    if action == MediationAction.approve_modified:
        override = TeacherSchedulingOverride(
            recommended_priority=PracticeQueuePriority.high,
        )

    return TeacherSchedulingMediation(
        id=mediation_id,
        recommendation_id=recommendation_id,
        teacher_id=teacher_id,
        student_id=student_id,
        action=action,
        rationale=rationale,
        override=override,
        created_at=created_at or datetime.now(timezone.utc),
    )


class TestStoreVersion:
    """Tests for store version constant."""

    def test_version_defined(self) -> None:
        assert TEACHER_SCHEDULING_MEDIATION_STORE_VERSION == "0.1.0"


class TestAppendMediation:
    """Tests for append_mediation."""

    def test_appends_mediation(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        mediation = make_mediation()
        result = store.append_mediation(mediation)

        assert result.id == mediation.id
        assert store.count() == 1

    def test_persists_to_file(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        mediation = make_mediation()
        store.append_mediation(mediation)

        assert store_path.exists()
        content = store_path.read_text()
        assert "tsm_test123" in content

    def test_appends_multiple(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        mediation1 = make_mediation(mediation_id="tsm_001")
        mediation2 = make_mediation(mediation_id="tsm_002")
        store.append_mediation(mediation1)
        store.append_mediation(mediation2)

        assert store.count() == 2

    def test_reloads_from_file(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"

        store1 = TeacherSchedulingMediationStore(store_path)
        store1.append_mediation(make_mediation(mediation_id="tsm_001"))
        store1.append_mediation(make_mediation(mediation_id="tsm_002"))

        store2 = TeacherSchedulingMediationStore(store_path)
        assert store2.count() == 2

    def test_creates_parent_directories(self, tmp_path) -> None:
        store_path = tmp_path / "nested" / "dir" / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        mediation = make_mediation()
        store.append_mediation(mediation)

        assert store_path.exists()


class TestListMediations:
    """Tests for list_mediations."""

    def test_returns_all_without_filters(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001"))
        store.append_mediation(make_mediation(mediation_id="tsm_002"))

        results = store.list_mediations()
        assert len(results) == 2

    def test_filters_by_teacher_id(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001", teacher_id="teacher_A"))
        store.append_mediation(make_mediation(mediation_id="tsm_002", teacher_id="teacher_B"))
        store.append_mediation(make_mediation(mediation_id="tsm_003", teacher_id="teacher_A"))

        results = store.list_mediations(teacher_id="teacher_A")
        assert len(results) == 2
        assert all(m.teacher_id == "teacher_A" for m in results)

    def test_filters_by_student_id(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001", student_id="student_A"))
        store.append_mediation(make_mediation(mediation_id="tsm_002", student_id="student_B"))

        results = store.list_mediations(student_id="student_A")
        assert len(results) == 1
        assert results[0].student_id == "student_A"

    def test_filters_by_recommendation_id(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001", recommendation_id="asr_001"))
        store.append_mediation(make_mediation(mediation_id="tsm_002", recommendation_id="asr_002"))

        results = store.list_mediations(recommendation_id="asr_001")
        assert len(results) == 1
        assert results[0].recommendation_id == "asr_001"

    def test_combines_filters(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(
            mediation_id="tsm_001",
            teacher_id="teacher_A",
            student_id="student_X",
        ))
        store.append_mediation(make_mediation(
            mediation_id="tsm_002",
            teacher_id="teacher_A",
            student_id="student_Y",
        ))
        store.append_mediation(make_mediation(
            mediation_id="tsm_003",
            teacher_id="teacher_B",
            student_id="student_X",
        ))

        results = store.list_mediations(teacher_id="teacher_A", student_id="student_X")
        assert len(results) == 1
        assert results[0].id == "tsm_001"

    def test_returns_empty_for_no_matches(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(teacher_id="teacher_A"))

        results = store.list_mediations(teacher_id="teacher_B")
        assert len(results) == 0


class TestLatestMediationForRecommendation:
    """Tests for latest_mediation_for_recommendation."""

    def test_returns_latest_by_created_at(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=2)
        new_time = now - timedelta(hours=1)

        store.append_mediation(make_mediation(
            mediation_id="tsm_001",
            recommendation_id="asr_target",
            created_at=old_time,
        ))
        store.append_mediation(make_mediation(
            mediation_id="tsm_002",
            recommendation_id="asr_target",
            created_at=new_time,
        ))

        latest = store.latest_mediation_for_recommendation("asr_target")

        assert latest is not None
        assert latest.id == "tsm_002"

    def test_returns_none_when_not_found(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(recommendation_id="asr_other"))

        latest = store.latest_mediation_for_recommendation("asr_nonexistent")

        assert latest is None

    def test_ignores_other_recommendations(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        now = datetime.now(timezone.utc)

        store.append_mediation(make_mediation(
            mediation_id="tsm_001",
            recommendation_id="asr_target",
            created_at=now - timedelta(hours=2),
        ))
        store.append_mediation(make_mediation(
            mediation_id="tsm_002",
            recommendation_id="asr_other",
            created_at=now,
        ))

        latest = store.latest_mediation_for_recommendation("asr_target")

        assert latest is not None
        assert latest.id == "tsm_001"


class TestAllMediations:
    """Tests for all_mediations."""

    def test_returns_all(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001"))
        store.append_mediation(make_mediation(mediation_id="tsm_002"))

        all_mediations = store.all_mediations()

        assert len(all_mediations) == 2

    def test_returns_copy(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation())

        all1 = store.all_mediations()
        all2 = store.all_mediations()

        assert all1 is not all2


class TestCount:
    """Tests for count."""

    def test_returns_zero_for_empty(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        assert store.count() == 0

    def test_returns_correct_count(self, tmp_path) -> None:
        store_path = tmp_path / "mediations.jsonl"
        store = TeacherSchedulingMediationStore(store_path)

        store.append_mediation(make_mediation(mediation_id="tsm_001"))
        store.append_mediation(make_mediation(mediation_id="tsm_002"))
        store.append_mediation(make_mediation(mediation_id="tsm_003"))

        assert store.count() == 3
