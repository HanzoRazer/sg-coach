"""
Pedagogical Visualization Projection Engine.

Sprint 33: Pedagogical Timeline Visualization Layer.

Provides:
- timeline_events_from_ledger(): Convert ledger to timeline events
- build_diagnosis_timeline_groups(): Group events by diagnosis
- build_pedagogical_timeline_view(): Build complete timeline view

Core rules:
- Projection-only (no mutation)
- Evidence ledger is canonical source
- Deterministic ordering
- No AI summarization
"""
from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Sequence

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


PEDAGOGICAL_VISUALIZATION_VERSION = "0.1.0"


def _generate_event_id() -> str:
    """Generate unique event ID."""
    return f"ptv_{secrets.token_hex(6)}"


def _map_source_to_event_type(
    source: PedagogicalEvidenceSource,
) -> Optional[PedagogicalVisualizationEventType]:
    """Map ledger source to visualization event type."""
    mapping = {
        PedagogicalEvidenceSource.runtime_review: PedagogicalVisualizationEventType.runtime_review,
        PedagogicalEvidenceSource.longitudinal_review: PedagogicalVisualizationEventType.longitudinal_review,
        PedagogicalEvidenceSource.assignment_outcome: PedagogicalVisualizationEventType.assignment_outcome,
        PedagogicalEvidenceSource.curriculum_progression: PedagogicalVisualizationEventType.curriculum_progression,
        PedagogicalEvidenceSource.queue_event: PedagogicalVisualizationEventType.adaptive_scheduling,
        PedagogicalEvidenceSource.practice_assignment: PedagogicalVisualizationEventType.adaptive_scheduling,
        PedagogicalEvidenceSource.teacher_scheduling_mediation: PedagogicalVisualizationEventType.teacher_mediation,
        PedagogicalEvidenceSource.teacher_review: PedagogicalVisualizationEventType.teacher_mediation,
    }
    return mapping.get(source)


def _map_severity(
    severity: PedagogicalEvidenceSeverity,
) -> TimelineVisualizationSeverity:
    """Map ledger severity to visualization severity."""
    mapping = {
        PedagogicalEvidenceSeverity.informational: TimelineVisualizationSeverity.informational,
        PedagogicalEvidenceSeverity.warning: TimelineVisualizationSeverity.warning,
        PedagogicalEvidenceSeverity.critical: TimelineVisualizationSeverity.critical,
    }
    return mapping.get(severity, TimelineVisualizationSeverity.informational)


def timeline_event_from_entry(
    entry: PedagogicalEvidenceEntry,
) -> Optional[PedagogicalTimelineEvent]:
    """
    Convert a ledger entry to a timeline event.

    Returns None if the source is unknown/unsupported.
    """
    event_type = _map_source_to_event_type(entry.source)
    if event_type is None:
        return None

    return PedagogicalTimelineEvent(
        event_id=_generate_event_id(),
        timestamp=entry.timestamp,
        event_type=event_type,
        title=entry.title,
        summary=entry.summary,
        severity=_map_severity(entry.severity),
        diagnosis_code=entry.diagnosis_code,
        evidence_id=entry.evidence_id,
        related_ids=list(entry.provenance),
        metadata=dict(entry.metadata),
    )


def timeline_events_from_ledger(
    ledger: PedagogicalEvidenceLedger,
) -> list[PedagogicalTimelineEvent]:
    """
    Convert all ledger entries to timeline events.

    Unknown sources are skipped (not failed).

    Parameters
    ----------
    ledger:
        The pedagogical evidence ledger.

    Returns
    -------
    List of timeline events, sorted by timestamp ascending,
    severity descending, event_id ascending.
    """
    events: list[PedagogicalTimelineEvent] = []

    for entry in ledger.entries:
        event = timeline_event_from_entry(entry)
        if event is not None:
            events.append(event)

    severity_order = {
        TimelineVisualizationSeverity.critical: 0,
        TimelineVisualizationSeverity.warning: 1,
        TimelineVisualizationSeverity.informational: 2,
    }

    events.sort(
        key=lambda e: (
            e.timestamp,
            severity_order.get(e.severity, 2),
            e.event_id,
        )
    )

    return events


def build_diagnosis_timeline_groups(
    events: Sequence[PedagogicalTimelineEvent],
) -> list[DiagnosisTimelineGroup]:
    """
    Group timeline events by diagnosis code.

    Parameters
    ----------
    events:
        Timeline events to group.

    Returns
    -------
    List of diagnosis groups, sorted by total_events descending.
    """
    groups_dict: dict[DiagnosisCode, list[PedagogicalTimelineEvent]] = defaultdict(list)

    for event in events:
        if event.diagnosis_code is not None:
            groups_dict[event.diagnosis_code].append(event)

    groups: list[DiagnosisTimelineGroup] = []

    for diagnosis_code, group_events in groups_dict.items():
        sorted_events = sorted(group_events, key=lambda e: e.timestamp)
        latest_event_at = sorted_events[-1].timestamp if sorted_events else None

        groups.append(
            DiagnosisTimelineGroup(
                diagnosis_code=diagnosis_code,
                total_events=len(sorted_events),
                latest_event_at=latest_event_at,
                events=sorted_events,
            )
        )

    groups.sort(key=lambda g: (-g.total_events, g.diagnosis_code.value))

    return groups


def _generate_deterministic_notes(
    events: Sequence[PedagogicalTimelineEvent],
    diagnosis_groups: Sequence[DiagnosisTimelineGroup],
) -> list[str]:
    """
    Generate deterministic summary notes.

    Maximum 5 notes, no AI generation.
    """
    notes: list[str] = []

    if not events:
        return ["No pedagogical evidence recorded yet."]

    if diagnosis_groups:
        most_common = diagnosis_groups[0]
        notes.append(
            f"{most_common.diagnosis_code.value} is the most frequent evidence category."
        )

    critical_count = sum(
        1 for e in events
        if e.severity == TimelineVisualizationSeverity.critical
    )
    if critical_count > 0:
        notes.append(f"{critical_count} critical evidence events require review.")

    teacher_mediation_count = sum(
        1 for e in events
        if e.event_type == PedagogicalVisualizationEventType.teacher_mediation
    )
    if teacher_mediation_count >= 2:
        notes.append("Teacher mediation appears in multiple evidence events.")

    assignment_outcome_count = sum(
        1 for e in events
        if e.event_type == PedagogicalVisualizationEventType.assignment_outcome
    )
    if assignment_outcome_count >= 2:
        notes.append("Assignment outcomes provide repeated evidence for practice response.")

    curriculum_progression_count = sum(
        1 for e in events
        if e.event_type == PedagogicalVisualizationEventType.curriculum_progression
    )
    if curriculum_progression_count >= 1:
        notes.append("Curriculum progression evidence is available.")

    return notes[:5]


def build_pedagogical_timeline_view(
    *,
    ledger: PedagogicalEvidenceLedger,
    student_id: Optional[str] = None,
) -> PedagogicalTimelineView:
    """
    Build a complete pedagogical timeline view from a ledger.

    Parameters
    ----------
    ledger:
        The pedagogical evidence ledger.
    student_id:
        Optional student ID (uses ledger's if not provided).

    Returns
    -------
    PedagogicalTimelineView ready for visualization.
    """
    resolved_student_id = student_id or ledger.student_id

    events = timeline_events_from_ledger(ledger)
    diagnosis_groups = build_diagnosis_timeline_groups(events)
    notes = _generate_deterministic_notes(events, diagnosis_groups)

    return PedagogicalTimelineView(
        student_id=resolved_student_id,
        total_events=len(events),
        timeline_events=events,
        diagnosis_groups=diagnosis_groups,
        notes=notes,
    )


__all__ = [
    "PEDAGOGICAL_VISUALIZATION_VERSION",
    "timeline_event_from_entry",
    "timeline_events_from_ledger",
    "build_diagnosis_timeline_groups",
    "build_pedagogical_timeline_view",
]
