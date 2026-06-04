"""
Tests for Studio Roster Store.

Sprint 20: Multi-student studio support with append-only event log.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_coach.studio_roster_store import (
    STUDIO_ROSTER_VERSION,
    StudioRosterStore,
)
from sg_spec.schemas.studio_roster import (
    StudioRosterEventType,
    Student,
    Teacher,
    Studio,
    StudioOverview,
)


class TestStudioRosterStoreInit:
    """Tests for store initialization."""

    def test_init_creates_empty_store(self, tmp_path):
        path = tmp_path / "roster.jsonl"
        store = StudioRosterStore(path)
        assert store.path == path
        assert not path.exists()

    def test_init_loads_existing_events(self, tmp_path):
        path = tmp_path / "roster.jsonl"
        event = {
            "id": "sre_001",
            "event_type": "studio_created",
            "studio_id": "studio_001",
            "payload": {"name": "Test Studio"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "studio_roster",
            "version": "0.1",
        }
        path.write_text(json.dumps(event) + "\n")

        store = StudioRosterStore(path)
        assert len(store._events) == 1

    def test_init_skips_invalid_lines(self, tmp_path):
        path = tmp_path / "roster.jsonl"
        path.write_text("invalid json\n{}\n")

        store = StudioRosterStore(path)
        assert len(store._events) == 0


class TestCreateStudio:
    """Tests for studio creation."""

    def test_create_studio_minimal(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Test Studio")

        assert studio.name == "Test Studio"
        assert studio.studio_id.startswith("studio_")
        assert len(studio.studio_id) == 19  # studio_ + 12 hex
        assert studio.teacher_ids == []
        assert studio.student_ids == []
        assert studio.metadata == {}

    def test_create_studio_with_id(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(
            name="Custom Studio",
            studio_id="studio_custom123",
        )
        assert studio.studio_id == "studio_custom123"

    def test_create_studio_with_teachers(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(
            name="Studio",
            teacher_ids=["teacher_001", "teacher_002"],
        )
        assert studio.teacher_ids == ["teacher_001", "teacher_002"]

    def test_create_studio_with_metadata(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(
            name="Studio",
            metadata={"location": "downtown"},
        )
        assert studio.metadata == {"location": "downtown"}

    def test_create_studio_persists_event(self, tmp_path):
        path = tmp_path / "roster.jsonl"
        store = StudioRosterStore(path)
        store.create_studio(name="Test Studio")

        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event["event_type"] == "studio_created"


class TestAddStudent:
    """Tests for adding students."""

    def test_add_student_minimal(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Alice",
        )

        assert student.display_name == "Alice"
        assert student.student_id.startswith("student_")
        assert len(student.student_id) == 20  # student_ + 12 hex
        assert student.active is True
        assert student.notes is None
        assert student.metadata == {}

    def test_add_student_with_id(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Bob",
            student_id="student_custom123",
        )
        assert student.student_id == "student_custom123"

    def test_add_student_with_enrollment_date(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        enroll = datetime(2024, 1, 15, tzinfo=timezone.utc)
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Carol",
            enrollment_date=enroll,
        )
        assert student.enrollment_date == enroll

    def test_add_student_with_notes(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Dave",
            notes="Beginner guitarist",
        )
        assert student.notes == "Beginner guitarist"

    def test_add_student_with_metadata(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Eve",
            metadata={"skill_level": "intermediate"},
        )
        assert student.metadata == {"skill_level": "intermediate"}


class TestAddTeacher:
    """Tests for adding teachers."""

    def test_add_teacher_minimal(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        teacher = store.add_teacher(
            studio_id=studio.studio_id,
            display_name="Mr. Smith",
        )

        assert teacher.display_name == "Mr. Smith"
        assert teacher.teacher_id.startswith("teacher_")
        assert len(teacher.teacher_id) == 20  # teacher_ + 12 hex
        assert teacher.active is True
        assert teacher.metadata == {}

    def test_add_teacher_with_id(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        teacher = store.add_teacher(
            studio_id=studio.studio_id,
            display_name="Ms. Jones",
            teacher_id="teacher_custom123",
        )
        assert teacher.teacher_id == "teacher_custom123"

    def test_add_teacher_with_metadata(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        teacher = store.add_teacher(
            studio_id=studio.studio_id,
            display_name="Dr. Brown",
            metadata={"specialty": "classical"},
        )
        assert teacher.metadata == {"specialty": "classical"}


class TestDeactivateStudent:
    """Tests for student deactivation."""

    def test_deactivate_student(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Alice",
        )

        deactivated = store.deactivate_student(
            studio_id=studio.studio_id,
            student_id=student.student_id,
        )
        assert deactivated.active is False
        assert deactivated.display_name == "Alice"

    def test_deactivate_student_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        with pytest.raises(ValueError) as exc:
            store.deactivate_student(
                studio_id=studio.studio_id,
                student_id="student_nonexistent",
            )
        assert "not found" in str(exc.value)


class TestDeactivateTeacher:
    """Tests for teacher deactivation."""

    def test_deactivate_teacher(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        teacher = store.add_teacher(
            studio_id=studio.studio_id,
            display_name="Mr. Smith",
        )

        deactivated = store.deactivate_teacher(
            studio_id=studio.studio_id,
            teacher_id=teacher.teacher_id,
        )
        assert deactivated.active is False
        assert deactivated.display_name == "Mr. Smith"

    def test_deactivate_teacher_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        with pytest.raises(ValueError) as exc:
            store.deactivate_teacher(
                studio_id=studio.studio_id,
                teacher_id="teacher_nonexistent",
            )
        assert "not found" in str(exc.value)


class TestReactivateStudent:
    """Tests for student reactivation."""

    def test_reactivate_student(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        student = store.add_student(
            studio_id=studio.studio_id,
            display_name="Alice",
        )
        store.deactivate_student(studio.studio_id, student.student_id)

        reactivated = store.reactivate_student(
            studio_id=studio.studio_id,
            student_id=student.student_id,
        )
        assert reactivated.active is True

    def test_reactivate_student_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        with pytest.raises(ValueError) as exc:
            store.reactivate_student(
                studio_id=studio.studio_id,
                student_id="student_nonexistent",
            )
        assert "not found" in str(exc.value)


class TestReactivateTeacher:
    """Tests for teacher reactivation."""

    def test_reactivate_teacher(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        teacher = store.add_teacher(
            studio_id=studio.studio_id,
            display_name="Mr. Smith",
        )
        store.deactivate_teacher(studio.studio_id, teacher.teacher_id)

        reactivated = store.reactivate_teacher(
            studio_id=studio.studio_id,
            teacher_id=teacher.teacher_id,
        )
        assert reactivated.active is True

    def test_reactivate_teacher_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        with pytest.raises(ValueError) as exc:
            store.reactivate_teacher(
                studio_id=studio.studio_id,
                teacher_id="teacher_nonexistent",
            )
        assert "not found" in str(exc.value)


class TestGetStudio:
    """Tests for getting studio state."""

    def test_get_studio(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        created = store.create_studio(name="Test Studio")

        studio = store.get_studio(created.studio_id)
        assert studio is not None
        assert studio.name == "Test Studio"
        assert studio.studio_id == created.studio_id

    def test_get_studio_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        store.create_studio(name="Studio")

        studio = store.get_studio("studio_nonexistent")
        assert studio is None

    def test_get_studio_auto_resolve_single(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        created = store.create_studio(name="Only Studio")

        studio = store.get_studio()  # No ID provided
        assert studio is not None
        assert studio.studio_id == created.studio_id

    def test_get_studio_error_multiple_no_id(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        store.create_studio(name="Studio 1")
        store.create_studio(name="Studio 2")

        with pytest.raises(ValueError) as exc:
            store.get_studio()
        assert "Multiple studios" in str(exc.value)

    def test_get_studio_with_members(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        store.add_student(studio.studio_id, "Alice")
        store.add_teacher(studio.studio_id, "Mr. Smith")

        rebuilt = store.get_studio(studio.studio_id)
        assert len(rebuilt.student_ids) == 1
        assert len(rebuilt.teacher_ids) == 1


class TestListStudents:
    """Tests for listing students."""

    def test_list_students_empty(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        students = store.list_students(studio.studio_id)
        assert students == []

    def test_list_students_active_only(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        alice = store.add_student(studio.studio_id, "Alice")
        bob = store.add_student(studio.studio_id, "Bob")
        store.deactivate_student(studio.studio_id, bob.student_id)

        students = store.list_students(studio.studio_id, active_only=True)
        assert len(students) == 1
        assert students[0].display_name == "Alice"

    def test_list_students_all(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        alice = store.add_student(studio.studio_id, "Alice")
        bob = store.add_student(studio.studio_id, "Bob")
        store.deactivate_student(studio.studio_id, bob.student_id)

        students = store.list_students(studio.studio_id, active_only=False)
        assert len(students) == 2

    def test_list_students_auto_resolve(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        store.add_student(studio.studio_id, "Alice")

        students = store.list_students()  # No ID
        assert len(students) == 1


class TestListTeachers:
    """Tests for listing teachers."""

    def test_list_teachers_empty(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")

        teachers = store.list_teachers(studio.studio_id)
        assert teachers == []

    def test_list_teachers_active_only(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        smith = store.add_teacher(studio.studio_id, "Mr. Smith")
        jones = store.add_teacher(studio.studio_id, "Ms. Jones")
        store.deactivate_teacher(studio.studio_id, jones.teacher_id)

        teachers = store.list_teachers(studio.studio_id, active_only=True)
        assert len(teachers) == 1
        assert teachers[0].display_name == "Mr. Smith"

    def test_list_teachers_all(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Studio")
        store.add_teacher(studio.studio_id, "Mr. Smith")
        jones = store.add_teacher(studio.studio_id, "Ms. Jones")
        store.deactivate_teacher(studio.studio_id, jones.teacher_id)

        teachers = store.list_teachers(studio.studio_id, active_only=False)
        assert len(teachers) == 2


class TestBuildOverview:
    """Tests for building studio overview."""

    def test_build_overview_empty_studio(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Empty Studio")

        overview = store.build_overview(studio.studio_id)
        assert overview.studio_id == studio.studio_id
        assert overview.name == "Empty Studio"
        assert overview.active_student_count == 0
        assert overview.active_teacher_count == 0
        assert overview.total_student_count == 0
        assert overview.total_teacher_count == 0
        assert overview.students == []
        assert overview.teachers == []

    def test_build_overview_with_members(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Full Studio")
        store.add_student(studio.studio_id, "Alice")
        store.add_student(studio.studio_id, "Bob")
        store.add_teacher(studio.studio_id, "Mr. Smith")

        overview = store.build_overview(studio.studio_id)
        assert overview.active_student_count == 2
        assert overview.active_teacher_count == 1
        assert overview.total_student_count == 2
        assert overview.total_teacher_count == 1
        assert len(overview.students) == 2
        assert len(overview.teachers) == 1

    def test_build_overview_with_deactivated(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Mixed Studio")
        alice = store.add_student(studio.studio_id, "Alice")
        bob = store.add_student(studio.studio_id, "Bob")
        smith = store.add_teacher(studio.studio_id, "Mr. Smith")
        jones = store.add_teacher(studio.studio_id, "Ms. Jones")

        store.deactivate_student(studio.studio_id, bob.student_id)
        store.deactivate_teacher(studio.studio_id, jones.teacher_id)

        overview = store.build_overview(studio.studio_id)
        assert overview.active_student_count == 1
        assert overview.active_teacher_count == 1
        assert overview.total_student_count == 2
        assert overview.total_teacher_count == 2

    def test_build_overview_not_found(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        store.create_studio(name="Studio")

        with pytest.raises(ValueError) as exc:
            store.build_overview("studio_nonexistent")
        assert "not found" in str(exc.value)

    def test_build_overview_auto_resolve(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio = store.create_studio(name="Only Studio")

        overview = store.build_overview()  # No ID
        assert overview.studio_id == studio.studio_id


class TestEventPersistence:
    """Tests for event persistence and reload."""

    def test_events_persist_across_sessions(self, tmp_path):
        path = tmp_path / "roster.jsonl"

        # Session 1: Create studio and add members
        store1 = StudioRosterStore(path)
        studio = store1.create_studio(name="Persistent Studio")
        store1.add_student(studio.studio_id, "Alice")
        store1.add_teacher(studio.studio_id, "Mr. Smith")

        # Session 2: Reload and verify
        store2 = StudioRosterStore(path)
        rebuilt = store2.get_studio(studio.studio_id)
        assert rebuilt is not None
        assert rebuilt.name == "Persistent Studio"
        assert len(rebuilt.student_ids) == 1
        assert len(rebuilt.teacher_ids) == 1

    def test_deactivation_persists(self, tmp_path):
        path = tmp_path / "roster.jsonl"

        # Session 1
        store1 = StudioRosterStore(path)
        studio = store1.create_studio(name="Studio")
        alice = store1.add_student(studio.studio_id, "Alice")
        store1.deactivate_student(studio.studio_id, alice.student_id)

        # Session 2
        store2 = StudioRosterStore(path)
        students = store2.list_students(studio.studio_id, active_only=True)
        assert len(students) == 0

        all_students = store2.list_students(studio.studio_id, active_only=False)
        assert len(all_students) == 1
        assert all_students[0].active is False

    def test_reactivation_persists(self, tmp_path):
        path = tmp_path / "roster.jsonl"

        # Session 1
        store1 = StudioRosterStore(path)
        studio = store1.create_studio(name="Studio")
        alice = store1.add_student(studio.studio_id, "Alice")
        store1.deactivate_student(studio.studio_id, alice.student_id)
        store1.reactivate_student(studio.studio_id, alice.student_id)

        # Session 2
        store2 = StudioRosterStore(path)
        students = store2.list_students(studio.studio_id, active_only=True)
        assert len(students) == 1
        assert students[0].active is True


class TestMultipleStudios:
    """Tests for multiple studios in one file."""

    def test_multiple_studios(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        studio1 = store.create_studio(name="Studio 1")
        studio2 = store.create_studio(name="Studio 2")

        store.add_student(studio1.studio_id, "Alice")
        store.add_student(studio2.studio_id, "Bob")

        students1 = store.list_students(studio1.studio_id)
        students2 = store.list_students(studio2.studio_id)

        assert len(students1) == 1
        assert students1[0].display_name == "Alice"
        assert len(students2) == 1
        assert students2[0].display_name == "Bob"

    def test_get_studio_ids(self, tmp_path):
        store = StudioRosterStore(tmp_path / "roster.jsonl")
        s1 = store.create_studio(name="Studio 1")
        s2 = store.create_studio(name="Studio 2")
        s3 = store.create_studio(name="Studio 3")

        ids = store._get_studio_ids()
        assert len(ids) == 3
        assert s1.studio_id in ids
        assert s2.studio_id in ids
        assert s3.studio_id in ids


class TestModuleExports:
    """Tests for module exports."""

    def test_version_constant(self):
        assert STUDIO_ROSTER_VERSION == "0.1"

    def test_import_from_package(self):
        from sg_coach import STUDIO_ROSTER_VERSION, StudioRosterStore
        assert STUDIO_ROSTER_VERSION is not None
        assert StudioRosterStore is not None
