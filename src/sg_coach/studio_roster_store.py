"""
Studio Roster Store.

Sprint 20: Multi-student studio support with append-only event log.

Local-first roster management. No auth, no permissions, no cloud sync.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from sg_spec.schemas.studio_roster import (
    StudioRosterEventType,
    Student,
    Teacher,
    Studio,
    StudioRosterEvent,
    StudioOverview,
)


STUDIO_ROSTER_VERSION = "0.1"


def _generate_studio_id() -> str:
    """Generate a unique studio ID with studio_ prefix."""
    return f"studio_{secrets.token_hex(6)}"


def _generate_student_id() -> str:
    """Generate a unique student ID with student_ prefix."""
    return f"student_{secrets.token_hex(6)}"


def _generate_teacher_id() -> str:
    """Generate a unique teacher ID with teacher_ prefix."""
    return f"teacher_{secrets.token_hex(6)}"


def _generate_event_id() -> str:
    """Generate a unique event ID with sre_ prefix."""
    return f"sre_{secrets.token_hex(6)}"


class StudioRosterStore:
    """
    Append-only event store for studio roster management.

    Events are persisted to JSONL. Current state is rebuilt from events.
    One file may contain multiple studios.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        """
        Initialize store with file path.

        Parameters
        ----------
        path:
            Path to JSONL file for roster events.
        """
        self.path = Path(path)
        self._events: list[StudioRosterEvent] = []
        self._load()

    def _load(self) -> None:
        """Load events from file if it exists."""
        self._events = []
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            event = StudioRosterEvent.model_validate(data)
                            self._events.append(event)
                        except Exception:
                            pass

    def _append_event(self, event: StudioRosterEvent) -> StudioRosterEvent:
        """Append event to file and memory."""
        if event.id is None:
            event = event.model_copy(update={"id": _generate_event_id()})

        self._events.append(event)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

        return event

    def _get_studio_ids(self) -> list[str]:
        """Get all studio IDs from events."""
        ids = set()
        for event in self._events:
            if event.event_type == StudioRosterEventType.studio_created:
                ids.add(event.studio_id)
        return list(ids)

    def _resolve_studio_id(self, studio_id: Optional[str]) -> str:
        """
        Resolve studio ID, defaulting if only one studio exists.

        Raises ValueError if multiple studios exist and no ID provided.
        """
        if studio_id is not None:
            return studio_id

        ids = self._get_studio_ids()
        if len(ids) == 0:
            raise ValueError("No studios exist in store")
        if len(ids) == 1:
            return ids[0]
        raise ValueError(
            f"Multiple studios exist ({len(ids)}). Specify studio_id explicitly."
        )

    def _rebuild_studio(self, studio_id: str) -> Optional[Studio]:
        """Rebuild studio state from events."""
        studio_data: Optional[dict] = None
        teacher_ids: list[str] = []
        student_ids: list[str] = []
        created_at: Optional[datetime] = None
        updated_at: Optional[datetime] = None

        for event in self._events:
            if event.studio_id != studio_id:
                continue

            updated_at = event.timestamp

            if event.event_type == StudioRosterEventType.studio_created:
                studio_data = {
                    "studio_id": event.studio_id,
                    "name": event.payload.get("name", ""),
                    "metadata": event.payload.get("metadata", {}),
                }
                teacher_ids = list(event.payload.get("teacher_ids", []))
                created_at = event.timestamp

            elif event.event_type == StudioRosterEventType.teacher_added:
                if event.target_id and event.target_id not in teacher_ids:
                    teacher_ids.append(event.target_id)

            elif event.event_type == StudioRosterEventType.teacher_deactivated:
                pass  # Don't remove from list, just mark inactive

            elif event.event_type == StudioRosterEventType.teacher_reactivated:
                if event.target_id and event.target_id not in teacher_ids:
                    teacher_ids.append(event.target_id)

            elif event.event_type == StudioRosterEventType.student_added:
                if event.target_id and event.target_id not in student_ids:
                    student_ids.append(event.target_id)

            elif event.event_type == StudioRosterEventType.student_deactivated:
                pass  # Don't remove from list, just mark inactive

            elif event.event_type == StudioRosterEventType.student_reactivated:
                if event.target_id and event.target_id not in student_ids:
                    student_ids.append(event.target_id)

            elif event.event_type == StudioRosterEventType.metadata_updated:
                if studio_data and event.payload.get("entity_type") == "studio":
                    studio_data["metadata"] = event.payload.get("metadata", {})

        if studio_data is None:
            return None

        return Studio(
            studio_id=studio_data["studio_id"],
            name=studio_data["name"],
            teacher_ids=teacher_ids,
            student_ids=student_ids,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
            metadata=studio_data.get("metadata", {}),
        )

    def _rebuild_student(self, studio_id: str, student_id: str) -> Optional[Student]:
        """Rebuild student state from events."""
        student_data: Optional[dict] = None
        active = True

        for event in self._events:
            if event.studio_id != studio_id:
                continue
            if event.target_id != student_id:
                continue

            if event.event_type == StudioRosterEventType.student_added:
                student_data = {
                    "student_id": student_id,
                    "display_name": event.payload.get("display_name", ""),
                    "enrollment_date": event.payload.get("enrollment_date")
                    or event.timestamp,
                    "notes": event.payload.get("notes"),
                    "metadata": event.payload.get("metadata", {}),
                }
                active = True

            elif event.event_type == StudioRosterEventType.student_deactivated:
                active = False

            elif event.event_type == StudioRosterEventType.student_reactivated:
                active = True

            elif event.event_type == StudioRosterEventType.metadata_updated:
                if student_data and event.payload.get("entity_type") == "student":
                    student_data["metadata"] = event.payload.get("metadata", {})

        if student_data is None:
            return None

        enrollment_date = student_data["enrollment_date"]
        if isinstance(enrollment_date, str):
            enrollment_date = datetime.fromisoformat(enrollment_date)

        return Student(
            student_id=student_data["student_id"],
            display_name=student_data["display_name"],
            active=active,
            enrollment_date=enrollment_date,
            notes=student_data.get("notes"),
            metadata=student_data.get("metadata", {}),
        )

    def _rebuild_teacher(self, studio_id: str, teacher_id: str) -> Optional[Teacher]:
        """Rebuild teacher state from events."""
        teacher_data: Optional[dict] = None
        active = True

        for event in self._events:
            if event.studio_id != studio_id:
                continue
            if event.target_id != teacher_id:
                continue

            if event.event_type == StudioRosterEventType.teacher_added:
                teacher_data = {
                    "teacher_id": teacher_id,
                    "display_name": event.payload.get("display_name", ""),
                    "metadata": event.payload.get("metadata", {}),
                }
                active = True

            elif event.event_type == StudioRosterEventType.teacher_deactivated:
                active = False

            elif event.event_type == StudioRosterEventType.teacher_reactivated:
                active = True

            elif event.event_type == StudioRosterEventType.metadata_updated:
                if teacher_data and event.payload.get("entity_type") == "teacher":
                    teacher_data["metadata"] = event.payload.get("metadata", {})

        if teacher_data is None:
            return None

        return Teacher(
            teacher_id=teacher_data["teacher_id"],
            display_name=teacher_data["display_name"],
            active=active,
            metadata=teacher_data.get("metadata", {}),
        )

    def create_studio(
        self,
        name: str,
        studio_id: Optional[str] = None,
        teacher_ids: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Studio:
        """
        Create a new studio.

        Parameters
        ----------
        name:
            Studio name (1-200 characters).
        studio_id:
            Optional studio ID. Auto-generated if not provided.
        teacher_ids:
            Optional initial teacher IDs.
        metadata:
            Optional metadata dict.

        Returns
        -------
        Created Studio.
        """
        sid = studio_id or _generate_studio_id()
        now = datetime.now(timezone.utc)

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.studio_created,
            studio_id=sid,
            payload={
                "name": name,
                "teacher_ids": teacher_ids or [],
                "metadata": metadata or {},
            },
            timestamp=now,
        )
        self._append_event(event)

        return Studio(
            studio_id=sid,
            name=name,
            teacher_ids=teacher_ids or [],
            student_ids=[],
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def add_student(
        self,
        studio_id: str,
        display_name: str,
        student_id: Optional[str] = None,
        enrollment_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Student:
        """
        Add a student to a studio.

        Parameters
        ----------
        studio_id:
            Studio to add student to.
        display_name:
            Student display name (1-200 characters).
        student_id:
            Optional student ID. Auto-generated if not provided.
        enrollment_date:
            Optional enrollment date. Defaults to now.
        notes:
            Optional notes (max 1000 characters).
        metadata:
            Optional metadata dict.

        Returns
        -------
        Created Student.
        """
        sid = student_id or _generate_student_id()
        now = datetime.now(timezone.utc)
        enroll = enrollment_date or now

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.student_added,
            studio_id=studio_id,
            target_id=sid,
            payload={
                "display_name": display_name,
                "enrollment_date": enroll.isoformat(),
                "notes": notes,
                "metadata": metadata or {},
            },
            timestamp=now,
        )
        self._append_event(event)

        return Student(
            student_id=sid,
            display_name=display_name,
            active=True,
            enrollment_date=enroll,
            notes=notes,
            metadata=metadata or {},
        )

    def add_teacher(
        self,
        studio_id: str,
        display_name: str,
        teacher_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Teacher:
        """
        Add a teacher to a studio.

        Parameters
        ----------
        studio_id:
            Studio to add teacher to.
        display_name:
            Teacher display name (1-200 characters).
        teacher_id:
            Optional teacher ID. Auto-generated if not provided.
        metadata:
            Optional metadata dict.

        Returns
        -------
        Created Teacher.
        """
        tid = teacher_id or _generate_teacher_id()
        now = datetime.now(timezone.utc)

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.teacher_added,
            studio_id=studio_id,
            target_id=tid,
            payload={
                "display_name": display_name,
                "metadata": metadata or {},
            },
            timestamp=now,
        )
        self._append_event(event)

        return Teacher(
            teacher_id=tid,
            display_name=display_name,
            active=True,
            metadata=metadata or {},
        )

    def deactivate_student(self, studio_id: str, student_id: str) -> Student:
        """
        Deactivate a student (soft delete).

        Parameters
        ----------
        studio_id:
            Studio containing the student.
        student_id:
            Student to deactivate.

        Returns
        -------
        Updated Student with active=False.

        Raises
        ------
        ValueError:
            If student not found.
        """
        student = self._rebuild_student(studio_id, student_id)
        if student is None:
            raise ValueError(f"Student {student_id} not found in studio {studio_id}")

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.student_deactivated,
            studio_id=studio_id,
            target_id=student_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._append_event(event)

        return student.model_copy(update={"active": False})

    def deactivate_teacher(self, studio_id: str, teacher_id: str) -> Teacher:
        """
        Deactivate a teacher (soft delete).

        Parameters
        ----------
        studio_id:
            Studio containing the teacher.
        teacher_id:
            Teacher to deactivate.

        Returns
        -------
        Updated Teacher with active=False.

        Raises
        ------
        ValueError:
            If teacher not found.
        """
        teacher = self._rebuild_teacher(studio_id, teacher_id)
        if teacher is None:
            raise ValueError(f"Teacher {teacher_id} not found in studio {studio_id}")

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.teacher_deactivated,
            studio_id=studio_id,
            target_id=teacher_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._append_event(event)

        return teacher.model_copy(update={"active": False})

    def reactivate_student(self, studio_id: str, student_id: str) -> Student:
        """
        Reactivate a deactivated student.

        Parameters
        ----------
        studio_id:
            Studio containing the student.
        student_id:
            Student to reactivate.

        Returns
        -------
        Updated Student with active=True.

        Raises
        ------
        ValueError:
            If student not found.
        """
        student = self._rebuild_student(studio_id, student_id)
        if student is None:
            raise ValueError(f"Student {student_id} not found in studio {studio_id}")

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.student_reactivated,
            studio_id=studio_id,
            target_id=student_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._append_event(event)

        return student.model_copy(update={"active": True})

    def reactivate_teacher(self, studio_id: str, teacher_id: str) -> Teacher:
        """
        Reactivate a deactivated teacher.

        Parameters
        ----------
        studio_id:
            Studio containing the teacher.
        teacher_id:
            Teacher to reactivate.

        Returns
        -------
        Updated Teacher with active=True.

        Raises
        ------
        ValueError:
            If teacher not found.
        """
        teacher = self._rebuild_teacher(studio_id, teacher_id)
        if teacher is None:
            raise ValueError(f"Teacher {teacher_id} not found in studio {studio_id}")

        event = StudioRosterEvent(
            event_type=StudioRosterEventType.teacher_reactivated,
            studio_id=studio_id,
            target_id=teacher_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._append_event(event)

        return teacher.model_copy(update={"active": True})

    def get_studio(self, studio_id: Optional[str] = None) -> Optional[Studio]:
        """
        Get studio by ID.

        Parameters
        ----------
        studio_id:
            Studio ID. If omitted and only one studio exists, uses that.

        Returns
        -------
        Studio if found, None otherwise.

        Raises
        ------
        ValueError:
            If multiple studios exist and studio_id not provided.
        """
        resolved_id = self._resolve_studio_id(studio_id)
        return self._rebuild_studio(resolved_id)

    def list_students(
        self,
        studio_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Student]:
        """
        List students in a studio.

        Parameters
        ----------
        studio_id:
            Studio ID. If omitted and only one studio exists, uses that.
        active_only:
            If True, only return active students (default True).

        Returns
        -------
        List of Student objects.
        """
        resolved_id = self._resolve_studio_id(studio_id)
        studio = self._rebuild_studio(resolved_id)
        if studio is None:
            return []

        students = []
        for student_id in studio.student_ids:
            student = self._rebuild_student(resolved_id, student_id)
            if student is not None:
                if active_only and not student.active:
                    continue
                students.append(student)

        return students

    def list_teachers(
        self,
        studio_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Teacher]:
        """
        List teachers in a studio.

        Parameters
        ----------
        studio_id:
            Studio ID. If omitted and only one studio exists, uses that.
        active_only:
            If True, only return active teachers (default True).

        Returns
        -------
        List of Teacher objects.
        """
        resolved_id = self._resolve_studio_id(studio_id)
        studio = self._rebuild_studio(resolved_id)
        if studio is None:
            return []

        teachers = []
        for teacher_id in studio.teacher_ids:
            teacher = self._rebuild_teacher(resolved_id, teacher_id)
            if teacher is not None:
                if active_only and not teacher.active:
                    continue
                teachers.append(teacher)

        return teachers

    def build_overview(self, studio_id: Optional[str] = None) -> StudioOverview:
        """
        Build studio overview with counts and member lists.

        Parameters
        ----------
        studio_id:
            Studio ID. If omitted and only one studio exists, uses that.

        Returns
        -------
        StudioOverview with current state.

        Raises
        ------
        ValueError:
            If studio not found or multiple studios exist without ID.
        """
        resolved_id = self._resolve_studio_id(studio_id)
        studio = self._rebuild_studio(resolved_id)
        if studio is None:
            raise ValueError(f"Studio {resolved_id} not found")

        all_students = self.list_students(resolved_id, active_only=False)
        all_teachers = self.list_teachers(resolved_id, active_only=False)

        active_students = [s for s in all_students if s.active]
        active_teachers = [t for t in all_teachers if t.active]

        return StudioOverview(
            studio_id=studio.studio_id,
            name=studio.name,
            active_student_count=len(active_students),
            active_teacher_count=len(active_teachers),
            total_student_count=len(all_students),
            total_teacher_count=len(all_teachers),
            students=all_students,
            teachers=all_teachers,
            generated_at=datetime.now(timezone.utc),
        )


__all__ = [
    "STUDIO_ROSTER_VERSION",
    "StudioRosterStore",
]
