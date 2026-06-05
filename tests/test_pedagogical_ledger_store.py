"""
Tests for Pedagogical Evidence Ledger Store.

Sprint 29: Pedagogical Evidence Ledger.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceSource,
    PedagogicalEvidenceSeverity,
)

from sg_coach.pedagogical_ledger_store import (
    PEDAGOGICAL_LEDGER_STORE_VERSION,
    PedagogicalLedgerStore,
)


def make_test_entry(
    evidence_id: str = "ped_test123",
    student_id: str | None = "student_123",
    diagnosis_code: DiagnosisCode | None = None,
    timestamp: datetime | None = None,
) -> PedagogicalEvidenceEntry:
    """Create a test entry."""
    return PedagogicalEvidenceEntry(
        evidence_id=evidence_id,
        student_id=student_id,
        source=PedagogicalEvidenceSource.runtime_review,
        timestamp=timestamp or datetime.now(timezone.utc),
        diagnosis_code=diagnosis_code,
        title="Test entry",
        summary="Test summary",
    )


class TestPedagogicalLedgerStore:
    """Tests for PedagogicalLedgerStore."""

    def test_creates_file_on_append(self, tmp_path: Path) -> None:
        store_path = tmp_path / "ledger.jsonl"
        store = PedagogicalLedgerStore(store_path)

        entry = make_test_entry()
        store.append_entry(entry)

        assert store_path.exists()

    def test_append_entry_returns_entry(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")
        entry = make_test_entry()

        result = store.append_entry(entry)

        assert result.evidence_id == entry.evidence_id

    def test_list_entries_empty_file(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entries = store.list_entries()

        assert entries == []

    def test_list_entries_returns_appended(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry1 = make_test_entry(evidence_id="ped_001")
        entry2 = make_test_entry(evidence_id="ped_002")
        store.append_entry(entry1)
        store.append_entry(entry2)

        entries = store.list_entries()

        assert len(entries) == 2
        ids = {e.evidence_id for e in entries}
        assert "ped_001" in ids
        assert "ped_002" in ids

    def test_list_entries_sorted_by_timestamp(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=1)

        entry_new = make_test_entry(evidence_id="ped_new", timestamp=now)
        entry_old = make_test_entry(evidence_id="ped_old", timestamp=old)

        store.append_entry(entry_new)
        store.append_entry(entry_old)

        entries = store.list_entries()

        assert entries[0].evidence_id == "ped_old"
        assert entries[1].evidence_id == "ped_new"

    def test_list_entries_filter_by_student(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry1 = make_test_entry(evidence_id="ped_001", student_id="student_A")
        entry2 = make_test_entry(evidence_id="ped_002", student_id="student_B")
        store.append_entry(entry1)
        store.append_entry(entry2)

        entries = store.list_entries(student_id="student_A")

        assert len(entries) == 1
        assert entries[0].evidence_id == "ped_001"

    def test_append_entries_multiple(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entries = [
            make_test_entry(evidence_id="ped_001"),
            make_test_entry(evidence_id="ped_002"),
            make_test_entry(evidence_id="ped_003"),
        ]
        store.append_entries(entries)

        result = store.list_entries()

        assert len(result) == 3

    def test_load_ledger_returns_ledger(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry = make_test_entry()
        store.append_entry(entry)

        ledger = store.load_ledger()

        assert len(ledger.entries) == 1
        assert ledger.entries[0].evidence_id == entry.evidence_id

    def test_load_ledger_with_student_filter(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry1 = make_test_entry(evidence_id="ped_001", student_id="student_A")
        entry2 = make_test_entry(evidence_id="ped_002", student_id="student_B")
        store.append_entry(entry1)
        store.append_entry(entry2)

        ledger = store.load_ledger(student_id="student_A")

        assert ledger.student_id == "student_A"
        assert len(ledger.entries) == 1

    def test_load_ledger_sets_generated_at(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        before = datetime.now(timezone.utc)
        ledger = store.load_ledger()
        after = datetime.now(timezone.utc)

        assert before <= ledger.generated_at <= after

    def test_build_summary_counts_entries(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry1 = make_test_entry(
            evidence_id="ped_001",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )
        entry2 = make_test_entry(
            evidence_id="ped_002",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )
        store.append_entry(entry1)
        store.append_entry(entry2)

        summary = store.build_summary()

        assert summary.total_entries == 2
        assert summary.runtime_review_entries == 2
        assert summary.diagnosis_counts["timing_grid_deviation"] == 2

    def test_build_summary_with_student_filter(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        entry1 = make_test_entry(evidence_id="ped_001", student_id="student_A")
        entry2 = make_test_entry(evidence_id="ped_002", student_id="student_B")
        store.append_entry(entry1)
        store.append_entry(entry2)

        summary = store.build_summary(student_id="student_A")

        assert summary.total_entries == 1

    def test_entry_count(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        store.append_entry(make_test_entry(evidence_id="ped_001"))
        store.append_entry(make_test_entry(evidence_id="ped_002"))

        assert store.entry_count() == 2

    def test_entry_count_with_student_filter(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "ledger.jsonl")

        store.append_entry(make_test_entry(evidence_id="ped_001", student_id="student_A"))
        store.append_entry(make_test_entry(evidence_id="ped_002", student_id="student_B"))

        assert store.entry_count(student_id="student_A") == 1

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        store = PedagogicalLedgerStore(tmp_path / "nonexistent.jsonl")

        entries = store.list_entries()

        assert entries == []

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        store_path = tmp_path / "nested" / "dir" / "ledger.jsonl"
        store = PedagogicalLedgerStore(store_path)

        entry = make_test_entry()
        store.append_entry(entry)

        assert store_path.exists()

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        store_path = tmp_path / "ledger.jsonl"

        store1 = PedagogicalLedgerStore(store_path)
        store1.append_entry(make_test_entry(evidence_id="ped_001"))

        store2 = PedagogicalLedgerStore(store_path)
        entries = store2.list_entries()

        assert len(entries) == 1
        assert entries[0].evidence_id == "ped_001"


class TestStoreVersion:
    """Test store version constant."""

    def test_version_defined(self) -> None:
        assert PEDAGOGICAL_LEDGER_STORE_VERSION == "0.1.0"
