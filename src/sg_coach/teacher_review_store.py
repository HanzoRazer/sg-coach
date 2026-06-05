"""
Teacher Review Store.

Sprint 19: Append-only JSONL persistence for teacher annotations
and recommendations.

Teacher data is additive metadata only — it never mutates
PracticeHistoryStore, CoachEvaluation, or PracticeAssignment.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sg_spec.schemas.teacher_review import (
    TeacherAnnotation,
    TeacherRecommendation,
)


class TeacherReviewStore:
    """
    Append-only JSONL store for teacher annotations and recommendations.

    Stores annotations and recommendations as separate line types
    in a single JSONL file. Each line has a 'type' field to
    distinguish annotation vs recommendation.
    """

    def __init__(self, path: Path | str) -> None:
        """
        Initialize the store.

        Parameters
        ----------
        path:
            Path to the JSONL file. Created if it doesn't exist.
        """
        self.path = Path(path)

    def _ensure_file(self) -> None:
        """Ensure the file exists."""
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()

    def append_annotation(self, annotation: TeacherAnnotation) -> None:
        """
        Append an annotation to the store.

        Parameters
        ----------
        annotation:
            The TeacherAnnotation to append.
        """
        self._ensure_file()
        record = {
            "type": "annotation",
            "data": annotation.model_dump(mode="json"),
            "appended_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def append_recommendation(self, recommendation: TeacherRecommendation) -> None:
        """
        Append a recommendation to the store.

        Parameters
        ----------
        recommendation:
            The TeacherRecommendation to append.
        """
        self._ensure_file()
        record = {
            "type": "recommendation",
            "data": recommendation.model_dump(mode="json"),
            "appended_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _read_all(self) -> list[dict]:
        """Read all records from the store."""
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def list_annotations(
        self,
        *,
        student_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[TeacherAnnotation]:
        """
        List annotations with optional filtering.

        Parameters
        ----------
        student_id:
            Filter by student ID.
        session_id:
            Filter by session ID.

        Returns
        -------
        List of TeacherAnnotation matching filters.
        """
        records = self._read_all()
        annotations = []

        for record in records:
            if record.get("type") != "annotation":
                continue

            data = record.get("data", {})

            if student_id and data.get("student_id") != student_id:
                continue
            if session_id and data.get("session_id") != session_id:
                continue

            try:
                annotation = TeacherAnnotation.model_validate(data)
                annotations.append(annotation)
            except Exception:
                continue

        return annotations

    def list_recommendations(
        self,
        *,
        student_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[TeacherRecommendation]:
        """
        List recommendations with optional filtering.

        Parameters
        ----------
        student_id:
            Filter by student ID.
        session_id:
            Filter by session ID.

        Returns
        -------
        List of TeacherRecommendation matching filters.
        """
        records = self._read_all()
        recommendations = []

        for record in records:
            if record.get("type") != "recommendation":
                continue

            data = record.get("data", {})

            if student_id and data.get("student_id") != student_id:
                continue
            if session_id and data.get("session_id") != session_id:
                continue

            try:
                recommendation = TeacherRecommendation.model_validate(data)
                recommendations.append(recommendation)
            except Exception:
                continue

        return recommendations


__all__ = [
    "TeacherReviewStore",
]
