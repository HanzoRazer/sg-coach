"""
Practice History Store — Persistent append-only storage for session history.

Sprint 11: Runtime integration.

This module provides:
- PracticeHistoryStore: Append-only JSONL storage for session history
- PracticeHistoryEntry: Single entry combining session, evaluation, assignments

Core rule: Append-only events. Never mutate past entries.

Ownership: sg-coach
Storage: JSONL (one entry per line)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import secrets

from pydantic import BaseModel, ConfigDict, Field

from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    SessionRecord,
)
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignmentSet


def _generate_entry_id() -> str:
    """Generate a unique entry ID."""
    return f"ph_{secrets.token_hex(6)}"


class PracticeHistoryEntry(BaseModel):
    """
    A single practice history entry.

    Combines session, evaluation, and assignments into one record.
    This is the append-only unit of storage.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=_generate_entry_id)
    session_id: str = Field(description="Session UUID as string")
    user_id: Optional[str] = Field(default=None)
    instrument_id: str

    session: Dict[str, Any] = Field(description="SessionRecord as dict")
    evaluation: Dict[str, Any] = Field(description="CoachEvaluation as dict")
    assignments: Dict[str, Any] = Field(description="AssembledPracticeAssignmentSet as dict")

    findings_count: int = Field(ge=0)
    assignments_count: int = Field(ge=0)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "0.1"


class PracticeHistoryQuery(BaseModel):
    """Query parameters for practice history."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    instrument_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1)


class PracticeHistoryStats(BaseModel):
    """Statistics about the practice history store."""
    model_config = ConfigDict(extra="forbid")

    total_entries: int = Field(ge=0)
    total_findings: int = Field(ge=0)
    total_assignments: int = Field(ge=0)


def _entry_to_json(entry: PracticeHistoryEntry) -> str:
    """Serialize entry to JSON string."""
    return entry.model_dump_json()


def _entry_from_json(line: str) -> PracticeHistoryEntry:
    """Deserialize entry from JSON string."""
    return PracticeHistoryEntry.model_validate_json(line)


def create_history_entry(
    session: SessionRecord,
    evaluation: CoachEvaluation,
    assignments: AssembledPracticeAssignmentSet,
    *,
    user_id: Optional[str] = None,
    entry_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> PracticeHistoryEntry:
    """
    Create a practice history entry from session, evaluation, and assignments.

    Parameters
    ----------
    session:
        The session record.
    evaluation:
        The coaching evaluation.
    assignments:
        The assembled practice assignments.
    user_id:
        Optional user ID.
    entry_id:
        Optional explicit entry ID (for idempotency).
    timestamp:
        Optional explicit timestamp.

    Returns
    -------
    PracticeHistoryEntry ready for storage.
    """
    return PracticeHistoryEntry(
        id=entry_id or _generate_entry_id(),
        session_id=str(session.session_id),
        user_id=user_id,
        instrument_id=session.instrument_id,
        session=session.model_dump(mode="json"),
        evaluation=evaluation.model_dump(mode="json"),
        assignments=assignments.model_dump(mode="json"),
        findings_count=len(evaluation.findings),
        assignments_count=len(assignments.assignments),
        timestamp=timestamp or datetime.now(timezone.utc),
    )


class PracticeHistoryStore:
    """
    Append-only JSONL storage for practice history.

    Each entry is stored as one JSON line in the file.
    Concurrent writes are out of scope for v1.

    Parameters
    ----------
    path:
        Path to the JSONL file. Parent directories will be created.

    Notes
    -----
    - Append-only: existing rows are never modified
    - One PracticeHistoryEntry per line
    - Blank lines are ignored when reading
    - Invalid JSON raises immediately (no silent skipping)
    """

    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Path to the JSONL file."""
        return self._path

    def _ensure_parent_dirs(self) -> None:
        """Create parent directories if they don't exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: PracticeHistoryEntry) -> PracticeHistoryEntry:
        """
        Append a single entry to the store.

        Parameters
        ----------
        entry:
            The entry to store.

        Returns
        -------
        The same entry (for chaining).
        """
        self._ensure_parent_dirs()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(_entry_to_json(entry) + "\n")
        return entry

    def append_session(
        self,
        session: SessionRecord,
        evaluation: CoachEvaluation,
        assignments: AssembledPracticeAssignmentSet,
        *,
        user_id: Optional[str] = None,
    ) -> PracticeHistoryEntry:
        """
        Create and append a practice history entry.

        Convenience method that creates the entry and appends in one call.

        Parameters
        ----------
        session:
            The session record.
        evaluation:
            The coaching evaluation.
        assignments:
            The assembled practice assignments.
        user_id:
            Optional user ID.

        Returns
        -------
        The created and stored entry.
        """
        entry = create_history_entry(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id=user_id,
        )
        return self.append(entry)

    def all(self) -> List[PracticeHistoryEntry]:
        """
        Read all entries from the store.

        Returns
        -------
        List of all stored entries.

        Raises
        ------
        ValueError:
            If any line contains invalid JSON.
        """
        if not self._path.exists():
            return []

        entries: List[PracticeHistoryEntry] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(_entry_from_json(line))
                except Exception as e:
                    raise ValueError(
                        f"Invalid JSON at line {line_num} in {self._path}: {e}"
                    ) from e
        return entries

    def query(
        self,
        query: Optional[PracticeHistoryQuery] = None,
    ) -> List[PracticeHistoryEntry]:
        """
        Query entries with optional filtering.

        Parameters
        ----------
        query:
            Filter parameters. If None, returns all entries.

        Returns
        -------
        List of matching entries.
        """
        entries = self.all()

        if query is None:
            return entries

        filtered: List[PracticeHistoryEntry] = []
        for entry in entries:
            if not self._matches_query(entry, query):
                continue
            filtered.append(entry)

        if query.limit is not None:
            filtered = filtered[:query.limit]

        return filtered

    def _matches_query(
        self,
        entry: PracticeHistoryEntry,
        query: PracticeHistoryQuery,
    ) -> bool:
        """Check if an entry matches the query filters."""
        if query.user_id is not None:
            if entry.user_id != query.user_id:
                return False

        if query.instrument_id is not None:
            if entry.instrument_id != query.instrument_id:
                return False

        if query.session_id is not None:
            if entry.session_id != query.session_id:
                return False

        return True

    def stats(self) -> PracticeHistoryStats:
        """
        Get statistics about the store.

        Returns
        -------
        PracticeHistoryStats with counts.
        """
        entries = self.all()

        total = len(entries)
        total_findings = sum(e.findings_count for e in entries)
        total_assignments = sum(e.assignments_count for e in entries)

        return PracticeHistoryStats(
            total_entries=total,
            total_findings=total_findings,
            total_assignments=total_assignments,
        )

    def get_by_session_id(self, session_id: str) -> Optional[PracticeHistoryEntry]:
        """
        Get entry by session ID.

        Parameters
        ----------
        session_id:
            The session ID to look up.

        Returns
        -------
        The entry if found, None otherwise.
        """
        query = PracticeHistoryQuery(session_id=session_id, limit=1)
        results = self.query(query)
        return results[0] if results else None


__all__ = [
    "PracticeHistoryEntry",
    "PracticeHistoryQuery",
    "PracticeHistoryStats",
    "PracticeHistoryStore",
    "create_history_entry",
]
