"""
Pedagogical Evidence Ledger Store — Append-only persistence.

Sprint 29: Pedagogical Evidence Ledger.

Provides:
- PedagogicalLedgerStore: Append-only JSONL persistence for evidence entries

Core rules:
- All entries are append-only
- Entries are never mutated or deleted
- Ledger is rebuilt from entries on read
- Corrections occur through additional entries
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceLedger,
    PedagogicalEvidenceSummary,
)

from .pedagogical_ledger import build_pedagogical_evidence_summary


PEDAGOGICAL_LEDGER_STORE_VERSION = "0.1.0"


class PedagogicalLedgerStore:
    """
    Append-only store for pedagogical evidence entries.

    Entries are persisted as JSONL (one JSON object per line).
    The ledger is rebuilt from entries when loaded.
    """

    def __init__(self, path: Path | str) -> None:
        """
        Initialize store with file path.

        Parameters
        ----------
        path:
            Path to JSONL file. Created if it doesn't exist.
        """
        self.path = Path(path)

    def _ensure_file_exists(self) -> None:
        """Ensure the store file exists."""
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()

    def append_entry(self, entry: PedagogicalEvidenceEntry) -> PedagogicalEvidenceEntry:
        """
        Append an evidence entry to the store.

        Parameters
        ----------
        entry:
            The entry to append.

        Returns
        -------
        The appended entry (unchanged).
        """
        self._ensure_file_exists()

        data = entry.model_dump(mode="json")
        line = json.dumps(data, default=str)

        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        return entry

    def append_entries(
        self,
        entries: list[PedagogicalEvidenceEntry],
    ) -> list[PedagogicalEvidenceEntry]:
        """
        Append multiple entries to the store.

        Parameters
        ----------
        entries:
            The entries to append.

        Returns
        -------
        The appended entries (unchanged).
        """
        self._ensure_file_exists()

        with self.path.open("a", encoding="utf-8") as f:
            for entry in entries:
                data = entry.model_dump(mode="json")
                line = json.dumps(data, default=str)
                f.write(line + "\n")

        return entries

    def list_entries(
        self,
        *,
        student_id: Optional[str] = None,
    ) -> list[PedagogicalEvidenceEntry]:
        """
        List all entries, optionally filtered by student.

        Parameters
        ----------
        student_id:
            Optional student ID to filter by.

        Returns
        -------
        List of entries sorted by timestamp ascending.
        """
        if not self.path.exists():
            return []

        entries: list[PedagogicalEvidenceEntry] = []

        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                data = json.loads(line)
                entry = PedagogicalEvidenceEntry.model_validate(data)

                if student_id is None or entry.student_id == student_id:
                    entries.append(entry)

        entries.sort(key=lambda e: e.timestamp)

        return entries

    def load_ledger(
        self,
        *,
        student_id: Optional[str] = None,
    ) -> PedagogicalEvidenceLedger:
        """
        Load and rebuild the ledger from stored entries.

        Parameters
        ----------
        student_id:
            Optional student ID to filter by.

        Returns
        -------
        Rebuilt ledger with entries sorted by timestamp.
        """
        entries = self.list_entries(student_id=student_id)

        return PedagogicalEvidenceLedger(
            student_id=student_id,
            entries=entries,
            generated_at=datetime.now(timezone.utc),
        )

    def build_summary(
        self,
        *,
        student_id: Optional[str] = None,
    ) -> PedagogicalEvidenceSummary:
        """
        Build evidence summary from stored entries.

        Parameters
        ----------
        student_id:
            Optional student ID to filter by.

        Returns
        -------
        Summary statistics for the ledger.
        """
        ledger = self.load_ledger(student_id=student_id)
        return build_pedagogical_evidence_summary(ledger)

    def entry_count(
        self,
        *,
        student_id: Optional[str] = None,
    ) -> int:
        """
        Get count of entries, optionally filtered by student.

        Parameters
        ----------
        student_id:
            Optional student ID to filter by.

        Returns
        -------
        Number of entries.
        """
        return len(self.list_entries(student_id=student_id))


__all__ = [
    "PEDAGOGICAL_LEDGER_STORE_VERSION",
    "PedagogicalLedgerStore",
]
