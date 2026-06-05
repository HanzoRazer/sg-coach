"""
Teacher Scheduling Mediation Store — Append-only mediation persistence.

Sprint 32: Teacher-Governed Adaptive Scheduling.

Provides:
- TeacherSchedulingMediationStore: Append-only JSONL store for mediations

Core rules:
- Append-only (no mutation or deletion)
- Latest mediation by created_at
- Immutable mediation history
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from sg_spec.schemas.teacher_scheduling_mediation import TeacherSchedulingMediation


TEACHER_SCHEDULING_MEDIATION_STORE_VERSION = "0.1.0"


class TeacherSchedulingMediationStore:
    """
    Append-only JSONL store for teacher scheduling mediations.

    All mediations are persisted immutably. No updates or deletes are allowed.
    """

    def __init__(self, path: Path | str) -> None:
        """
        Initialize the store.

        Parameters
        ----------
        path:
            Path to the JSONL file for persistence.
        """
        self._path = Path(path)
        self._mediations: list[TeacherSchedulingMediation] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load mediations from disk if not already loaded."""
        if self._loaded:
            return

        self._mediations = []

        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    mediation = TeacherSchedulingMediation.model_validate(data)
                    self._mediations.append(mediation)

        self._loaded = True

    def append_mediation(
        self,
        mediation: TeacherSchedulingMediation,
    ) -> TeacherSchedulingMediation:
        """
        Append a mediation to the store.

        Parameters
        ----------
        mediation:
            The mediation to append.

        Returns
        -------
        The appended mediation.
        """
        self._ensure_loaded()

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            data = mediation.model_dump(mode="json")
            f.write(json.dumps(data, default=str) + "\n")

        self._mediations.append(mediation)
        return mediation

    def list_mediations(
        self,
        *,
        teacher_id: Optional[str] = None,
        student_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
    ) -> list[TeacherSchedulingMediation]:
        """
        List mediations with optional filtering.

        Parameters
        ----------
        teacher_id:
            Filter by teacher ID.
        student_id:
            Filter by student ID.
        recommendation_id:
            Filter by recommendation ID.

        Returns
        -------
        List of matching mediations.
        """
        self._ensure_loaded()

        results: list[TeacherSchedulingMediation] = []

        for mediation in self._mediations:
            if teacher_id is not None and mediation.teacher_id != teacher_id:
                continue
            if student_id is not None and mediation.student_id != student_id:
                continue
            if recommendation_id is not None and mediation.recommendation_id != recommendation_id:
                continue
            results.append(mediation)

        return results

    def latest_mediation_for_recommendation(
        self,
        recommendation_id: str,
    ) -> Optional[TeacherSchedulingMediation]:
        """
        Get the latest mediation for a recommendation.

        Parameters
        ----------
        recommendation_id:
            The recommendation ID to look up.

        Returns
        -------
        The latest mediation by created_at, or None if not found.
        """
        self._ensure_loaded()

        matching = [
            m for m in self._mediations
            if m.recommendation_id == recommendation_id
        ]

        if not matching:
            return None

        return max(matching, key=lambda m: m.created_at)

    def all_mediations(self) -> list[TeacherSchedulingMediation]:
        """
        Get all mediations.

        Returns
        -------
        List of all mediations.
        """
        self._ensure_loaded()
        return list(self._mediations)

    def count(self) -> int:
        """
        Get the total number of mediations.

        Returns
        -------
        Number of mediations in the store.
        """
        self._ensure_loaded()
        return len(self._mediations)


__all__ = [
    "TEACHER_SCHEDULING_MEDIATION_STORE_VERSION",
    "TeacherSchedulingMediationStore",
]
