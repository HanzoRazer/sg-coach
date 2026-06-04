"""
Tests for Pedagogical Visualization Projection Engine.

Sprint 33: Pedagogical Timeline Visualization Layer.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from sg_spec.schemas.coach_schemas import DiagnosisCode
from sg_spec.schemas.pedagogical_ledger import (
    PedagogicalEvidenceEntry,
    PedagogicalEvidenceLedger,
    PedagogicalEvidenceSource,
    PedagogicalEvidenceSeverity,
)
from sg_spec.schemas.pedagogical_visualization import (
    DiagnosisTimelineGroup,
    PedagogicalTimelineEvent,
    PedagogicalTimelineView,
    PedagogicalVisualizationEventType,
    TimelineVisualizationSeverity,
)

from sg_coach.pedagogical_visualization import (
    PEDAGOGICAL_VISUALIZATION_VERSION,
    timeline_event_from_entry,
    timeline_events_from_ledger,
    build_diagnosis_timeline_groups,
    build_pedagogical_timeline_view,
)


def make_test_entry(
    *,
    source: PedagogicalEvidenceSource = PedagogicalEvidenceSource.runtime_review,
    severity: PedagogicalEvidenceSeverity = PedagogicalEvidenceSeverity.informational,
    diagnosis_code: DiagnosisCode | None = None,
    timestamp: datetime | None = None,
    evidence_id: str | None = None,
    provenance: list[str] | None = None,
) -> PedagogicalEvidenceEntry:
    """Create a test ledger entry."""
    return PedagogicalEvidenceEntry(
        evidence_id=evidence_id or f"ped_{uuid4().hex[:12]}",
        timestamp=timestamp or datetime.now(timezone.utc),
        source=source,
        title="Test Entry",
        summary="Test summary",
        severity=severity,
        diagnosis_code=diagnosis_code,
        provenance=provenance or [],
    )


def make_test_ledger(
    entries: list[PedagogicalEvidenceEntry] | None = None,
    student_id: str = "student_001",
) -> PedagogicalEvidenceLedger:
    """Create a test ledger."""
    return PedagogicalEvidenceLedger(
        student_id=student_id,
        entries=entries or [],
    )


class TestVersion:
    """Test version constant."""

    def test_version_format(self) -> None:
        parts = PEDAGOGICAL_VISUALIZATION_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestTimelineEventFromEntry:
    """Tests for timeline_event_from_entry()."""

    def test_runtime_review_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.runtime_review)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.runtime_review

    def test_longitudinal_review_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.longitudinal_review)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.longitudinal_review

    def test_assignment_outcome_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.assignment_outcome)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.assignment_outcome

    def test_queue_event_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.queue_event)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.adaptive_scheduling

    def test_practice_assignment_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.practice_assignment)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.adaptive_scheduling

    def test_teacher_scheduling_mediation_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.teacher_scheduling_mediation)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.teacher_mediation

    def test_teacher_review_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.teacher_review)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.teacher_mediation

    def test_curriculum_progression_source(self) -> None:
        entry = make_test_entry(source=PedagogicalEvidenceSource.curriculum_progression)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_type == PedagogicalVisualizationEventType.curriculum_progression

    def test_severity_informational_mapping(self) -> None:
        entry = make_test_entry(severity=PedagogicalEvidenceSeverity.informational)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.severity == TimelineVisualizationSeverity.informational

    def test_severity_warning_mapping(self) -> None:
        entry = make_test_entry(severity=PedagogicalEvidenceSeverity.warning)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.severity == TimelineVisualizationSeverity.warning

    def test_severity_critical_mapping(self) -> None:
        entry = make_test_entry(severity=PedagogicalEvidenceSeverity.critical)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.severity == TimelineVisualizationSeverity.critical

    def test_event_id_generated(self) -> None:
        entry = make_test_entry()
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.event_id.startswith("ptv_")
        assert len(event.event_id) == 16  # ptv_ + 12 hex chars

    def test_timestamp_preserved(self) -> None:
        ts = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        entry = make_test_entry(timestamp=ts)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.timestamp == ts

    def test_title_preserved(self) -> None:
        entry = make_test_entry()
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.title == "Test Entry"

    def test_summary_preserved(self) -> None:
        entry = make_test_entry()
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.summary == "Test summary"

    def test_diagnosis_code_preserved(self) -> None:
        entry = make_test_entry(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION)
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION

    def test_evidence_id_preserved(self) -> None:
        entry = make_test_entry(evidence_id="ped_abc123def456")
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.evidence_id == "ped_abc123def456"

    def test_provenance_becomes_related_ids(self) -> None:
        entry = make_test_entry(provenance=["rr:001", "sess:002"])
        event = timeline_event_from_entry(entry)
        assert event is not None
        assert event.related_ids == ["rr:001", "sess:002"]


class TestTimelineEventsFromLedger:
    """Tests for timeline_events_from_ledger()."""

    def test_empty_ledger(self) -> None:
        ledger = make_test_ledger(entries=[])
        events = timeline_events_from_ledger(ledger)
        assert events == []

    def test_single_entry(self) -> None:
        entry = make_test_entry()
        ledger = make_test_ledger(entries=[entry])
        events = timeline_events_from_ledger(ledger)
        assert len(events) == 1

    def test_multiple_entries(self) -> None:
        entries = [make_test_entry() for _ in range(3)]
        ledger = make_test_ledger(entries=entries)
        events = timeline_events_from_ledger(ledger)
        assert len(events) == 3

    def test_sorts_by_timestamp_ascending(self) -> None:
        t1 = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 15, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        entries = [
            make_test_entry(timestamp=t3),
            make_test_entry(timestamp=t1),
            make_test_entry(timestamp=t2),
        ]
        ledger = make_test_ledger(entries=entries)
        events = timeline_events_from_ledger(ledger)
        assert events[0].timestamp == t1
        assert events[1].timestamp == t2
        assert events[2].timestamp == t3

    def test_sorts_by_severity_descending_when_same_timestamp(self) -> None:
        ts = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        entries = [
            make_test_entry(timestamp=ts, severity=PedagogicalEvidenceSeverity.informational),
            make_test_entry(timestamp=ts, severity=PedagogicalEvidenceSeverity.critical),
            make_test_entry(timestamp=ts, severity=PedagogicalEvidenceSeverity.warning),
        ]
        ledger = make_test_ledger(entries=entries)
        events = timeline_events_from_ledger(ledger)
        assert events[0].severity == TimelineVisualizationSeverity.critical
        assert events[1].severity == TimelineVisualizationSeverity.warning
        assert events[2].severity == TimelineVisualizationSeverity.informational


class TestBuildDiagnosisTimelineGroups:
    """Tests for build_diagnosis_timeline_groups()."""

    def test_empty_events(self) -> None:
        groups = build_diagnosis_timeline_groups([])
        assert groups == []

    def test_events_without_diagnosis_code_excluded(self) -> None:
        event = PedagogicalTimelineEvent(
            event_id="ptv_abc123def456",
            timestamp=datetime.now(timezone.utc),
            event_type=PedagogicalVisualizationEventType.runtime_review,
            title="Test",
            summary="Summary",
            severity=TimelineVisualizationSeverity.informational,
            diagnosis_code=None,
        )
        groups = build_diagnosis_timeline_groups([event])
        assert groups == []

    def test_groups_by_diagnosis_code(self) -> None:
        ts = datetime.now(timezone.utc)
        events = [
            PedagogicalTimelineEvent(
                event_id="ptv_001",
                timestamp=ts,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test 1",
                summary="Summary 1",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
            PedagogicalTimelineEvent(
                event_id="ptv_002",
                timestamp=ts,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test 2",
                summary="Summary 2",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
            PedagogicalTimelineEvent(
                event_id="ptv_003",
                timestamp=ts,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test 3",
                summary="Summary 3",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            ),
        ]
        groups = build_diagnosis_timeline_groups(events)
        assert len(groups) == 2

    def test_sorts_by_total_events_descending(self) -> None:
        ts = datetime.now(timezone.utc)
        events = [
            PedagogicalTimelineEvent(
                event_id=f"ptv_00{i}",
                timestamp=ts,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test",
                summary="Summary",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            )
            for i in range(3)
        ] + [
            PedagogicalTimelineEvent(
                event_id="ptv_single",
                timestamp=ts,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test",
                summary="Summary",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
            )
        ]
        groups = build_diagnosis_timeline_groups(events)
        assert groups[0].diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert groups[0].total_events == 3
        assert groups[1].diagnosis_code == DiagnosisCode.PITCH_DEVIATION
        assert groups[1].total_events == 1

    def test_latest_event_at_populated(self) -> None:
        t1 = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            PedagogicalTimelineEvent(
                event_id="ptv_001",
                timestamp=t1,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test 1",
                summary="Summary 1",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
            PedagogicalTimelineEvent(
                event_id="ptv_002",
                timestamp=t2,
                event_type=PedagogicalVisualizationEventType.runtime_review,
                title="Test 2",
                summary="Summary 2",
                severity=TimelineVisualizationSeverity.informational,
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            ),
        ]
        groups = build_diagnosis_timeline_groups(events)
        assert groups[0].latest_event_at == t2


class TestBuildPedagogicalTimelineView:
    """Tests for build_pedagogical_timeline_view()."""

    def test_empty_ledger(self) -> None:
        ledger = make_test_ledger(entries=[])
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert view.total_events == 0
        assert view.timeline_events == []
        assert view.diagnosis_groups == []
        assert "No pedagogical evidence recorded yet." in view.notes

    def test_student_id_from_ledger(self) -> None:
        ledger = make_test_ledger(entries=[], student_id="student_abc")
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert view.student_id == "student_abc"

    def test_student_id_override(self) -> None:
        ledger = make_test_ledger(entries=[], student_id="student_abc")
        view = build_pedagogical_timeline_view(ledger=ledger, student_id="student_xyz")
        assert view.student_id == "student_xyz"

    def test_total_events_counted(self) -> None:
        entries = [make_test_entry() for _ in range(5)]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert view.total_events == 5

    def test_timeline_events_populated(self) -> None:
        entries = [make_test_entry() for _ in range(3)]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert len(view.timeline_events) == 3

    def test_diagnosis_groups_populated(self) -> None:
        entries = [
            make_test_entry(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION),
            make_test_entry(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION),
            make_test_entry(diagnosis_code=DiagnosisCode.PITCH_DEVIATION),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert len(view.diagnosis_groups) == 2

    def test_notes_generated_for_most_common_diagnosis(self) -> None:
        entries = [
            make_test_entry(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION),
            make_test_entry(diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION),
            make_test_entry(diagnosis_code=DiagnosisCode.PITCH_DEVIATION),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert any("timing_grid_deviation" in note for note in view.notes)

    def test_notes_generated_for_critical_events(self) -> None:
        entries = [
            make_test_entry(severity=PedagogicalEvidenceSeverity.critical),
            make_test_entry(severity=PedagogicalEvidenceSeverity.critical),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert any("critical" in note.lower() for note in view.notes)

    def test_notes_generated_for_teacher_mediation(self) -> None:
        entries = [
            make_test_entry(source=PedagogicalEvidenceSource.teacher_scheduling_mediation),
            make_test_entry(source=PedagogicalEvidenceSource.teacher_review),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert any("teacher mediation" in note.lower() for note in view.notes)

    def test_notes_generated_for_assignment_outcomes(self) -> None:
        entries = [
            make_test_entry(source=PedagogicalEvidenceSource.assignment_outcome),
            make_test_entry(source=PedagogicalEvidenceSource.assignment_outcome),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert any("assignment outcome" in note.lower() for note in view.notes)

    def test_notes_generated_for_curriculum_progression(self) -> None:
        entries = [
            make_test_entry(source=PedagogicalEvidenceSource.curriculum_progression),
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert any("curriculum progression" in note.lower() for note in view.notes)

    def test_notes_limited_to_five(self) -> None:
        entries = [
            make_test_entry(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                severity=PedagogicalEvidenceSeverity.critical,
                source=PedagogicalEvidenceSource.teacher_scheduling_mediation,
            )
            for _ in range(3)
        ] + [
            make_test_entry(source=PedagogicalEvidenceSource.assignment_outcome)
            for _ in range(3)
        ] + [
            make_test_entry(source=PedagogicalEvidenceSource.curriculum_progression)
        ]
        ledger = make_test_ledger(entries=entries)
        view = build_pedagogical_timeline_view(ledger=ledger)
        assert len(view.notes) <= 5


class TestExportsFromInit:
    """Test that functions are exported from sg_coach."""

    def test_version_exported(self) -> None:
        from sg_coach import PEDAGOGICAL_VISUALIZATION_VERSION
        assert PEDAGOGICAL_VISUALIZATION_VERSION is not None

    def test_timeline_event_from_entry_exported(self) -> None:
        from sg_coach import timeline_event_from_entry
        assert timeline_event_from_entry is not None

    def test_timeline_events_from_ledger_exported(self) -> None:
        from sg_coach import timeline_events_from_ledger
        assert timeline_events_from_ledger is not None

    def test_build_diagnosis_timeline_groups_exported(self) -> None:
        from sg_coach import build_diagnosis_timeline_groups
        assert build_diagnosis_timeline_groups is not None

    def test_build_pedagogical_timeline_view_exported(self) -> None:
        from sg_coach import build_pedagogical_timeline_view
        assert build_pedagogical_timeline_view is not None
