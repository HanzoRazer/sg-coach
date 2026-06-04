"""
Session Playback Builder.

Sprint 18: Transform session review into inspectable interactive playback.

Builds SessionPlaybackData from session, evaluation, and assignments.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sg_spec.schemas.coach_finding import DiagnosisCode
from sg_spec.schemas.coach_schemas import (
    CoachEvaluation,
    CoachFinding,
    Severity,
)
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignmentSet
from sg_spec.schemas.session_playback import (
    PlaybackAssignmentReference,
    PlaybackEventType,
    PlaybackFindingOverlay,
    PlaybackTimelineEvent,
    SessionPlaybackData,
)

from .schemas import SessionRecord


PLAYBACK_VERSION = "0.1"
DEFAULT_FINDING_WINDOW_MS = 2000
EVENT_TYPE_SORT_ORDER = {
    PlaybackEventType.note: 0,
    PlaybackEventType.finding: 1,
    PlaybackEventType.assignment: 2,
    PlaybackEventType.marker: 3,
}


def _extract_finding_timestamp_ms(finding: CoachFinding) -> int:
    """
    Extract timestamp from finding using priority:
    1. target_span.start_time_sec (convert to ms)
    2. Default to 0
    """
    if finding.target_span:
        if finding.target_span.start_time_sec is not None:
            return int(finding.target_span.start_time_sec * 1000)
    return 0


def _generate_finding_id(index: int, diagnosis_code: DiagnosisCode) -> str:
    """Generate a unique finding ID for playback."""
    return f"playback_finding_{index}_{diagnosis_code.value}"


def _build_note_events_from_midi(
    midi_events: list,
) -> list[PlaybackTimelineEvent]:
    """
    Build timeline events from MIDI note events.

    Parameters
    ----------
    midi_events:
        List of MidiNoteEvent from MidiSessionInput.

    Returns note-on events only (not note-off).
    """
    events: list[PlaybackTimelineEvent] = []

    for event in midi_events:
        if hasattr(event, 'type') and event.type.value == "note_on":
            timestamp_ms = int(event.time_sec * 1000)
            pitch = event.note
            label = f"Note {pitch}"

            events.append(
                PlaybackTimelineEvent(
                    event_type=PlaybackEventType.note,
                    timestamp_ms=timestamp_ms,
                    label=label,
                    note=str(pitch),
                    version=PLAYBACK_VERSION,
                )
            )

    return events


def _get_finding_label(finding: CoachFinding) -> str:
    """Get label from finding, preferring message over interpretation."""
    if finding.message:
        return finding.message[:200] if len(finding.message) > 200 else finding.message
    return finding.interpretation[:200] if len(finding.interpretation) > 200 else finding.interpretation


def _build_finding_events(
    findings: list[CoachFinding],
) -> tuple[list[PlaybackTimelineEvent], dict[str, int]]:
    """
    Build timeline events and timestamp map for findings.

    Returns:
        Tuple of (events, finding_id_to_timestamp_map)
    """
    events: list[PlaybackTimelineEvent] = []
    timestamp_map: dict[str, int] = {}

    for i, finding in enumerate(findings):
        diagnosis_code = finding.code
        if diagnosis_code is None:
            continue

        timestamp_ms = _extract_finding_timestamp_ms(finding)
        finding_id = _generate_finding_id(i, diagnosis_code)
        timestamp_map[finding_id] = timestamp_ms

        label = _get_finding_label(finding)

        events.append(
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.finding,
                timestamp_ms=timestamp_ms,
                label=label,
                finding_id=finding_id,
                diagnosis_code=diagnosis_code,
                severity=finding.severity,
                version=PLAYBACK_VERSION,
            )
        )

    return events, timestamp_map


def _build_assignment_events(
    assignments: AssembledPracticeAssignmentSet,
    finding_timestamp_map: dict[str, int],
) -> list[PlaybackTimelineEvent]:
    """
    Build timeline events for assignments.

    Links to finding timestamps where applicable.
    """
    events: list[PlaybackTimelineEvent] = []

    for assignment in assignments.assignments:
        timestamp_ms = 0
        if finding_timestamp_map:
            timestamps = list(finding_timestamp_map.values())
            timestamp_ms = min(timestamps) if timestamps else 0

        description = None
        if hasattr(assignment, 'rationale') and assignment.rationale:
            description = assignment.rationale[:500] if len(assignment.rationale) > 500 else assignment.rationale

        events.append(
            PlaybackTimelineEvent(
                event_type=PlaybackEventType.assignment,
                timestamp_ms=timestamp_ms,
                label=assignment.title[:200] if len(assignment.title) > 200 else assignment.title,
                description=description,
                assignment_id=assignment.id,
                diagnosis_code=assignment.diagnosis_code,
                version=PLAYBACK_VERSION,
            )
        )

    return events


def _build_finding_overlays(
    findings: list[CoachFinding],
    session_duration_ms: int,
) -> list[PlaybackFindingOverlay]:
    """
    Build finding overlays for timeline visualization.

    Each overlay spans [timestamp, timestamp + DEFAULT_FINDING_WINDOW_MS]
    clamped to session duration.
    """
    overlays: list[PlaybackFindingOverlay] = []

    for i, finding in enumerate(findings):
        diagnosis_code = finding.code
        if diagnosis_code is None:
            continue

        start_ms = _extract_finding_timestamp_ms(finding)
        end_ms = min(start_ms + DEFAULT_FINDING_WINDOW_MS, session_duration_ms)

        if end_ms < start_ms:
            end_ms = start_ms

        finding_id = _generate_finding_id(i, diagnosis_code)
        label = _get_finding_label(finding)

        overlays.append(
            PlaybackFindingOverlay(
                finding_id=finding_id,
                diagnosis_code=diagnosis_code,
                severity=finding.severity,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms,
                label=label,
                recommendation_ids=[],
                version=PLAYBACK_VERSION,
            )
        )

    return overlays


def _build_assignment_references(
    assignments: AssembledPracticeAssignmentSet,
    findings: list[CoachFinding],
    finding_timestamp_map: dict[str, int],
) -> list[PlaybackAssignmentReference]:
    """
    Build assignment references with finding linkage.

    Links assignments to findings by matching diagnosis_code.
    """
    refs: list[PlaybackAssignmentReference] = []

    diagnosis_to_findings: dict[DiagnosisCode, list[tuple[str, int]]] = {}
    for i, finding in enumerate(findings):
        if finding.code is None:
            continue
        finding_id = _generate_finding_id(i, finding.code)
        timestamp_ms = finding_timestamp_map.get(finding_id, 0)
        if finding.code not in diagnosis_to_findings:
            diagnosis_to_findings[finding.code] = []
        diagnosis_to_findings[finding.code].append((finding_id, timestamp_ms))

    for assignment in assignments.assignments:
        diagnosis_code = assignment.diagnosis_code

        linked_finding_ids: list[str] = []
        linked_timestamps_ms: list[int] = []

        if diagnosis_code and diagnosis_code in diagnosis_to_findings:
            for finding_id, timestamp_ms in diagnosis_to_findings[diagnosis_code]:
                linked_finding_ids.append(finding_id)
                linked_timestamps_ms.append(timestamp_ms)

        refs.append(
            PlaybackAssignmentReference(
                assignment_id=assignment.id,
                title=assignment.title[:200] if len(assignment.title) > 200 else assignment.title,
                diagnosis_code=diagnosis_code,
                linked_finding_ids=linked_finding_ids,
                linked_timestamps_ms=linked_timestamps_ms,
                version=PLAYBACK_VERSION,
            )
        )

    return refs


def _sort_timeline_events(
    events: list[PlaybackTimelineEvent],
) -> list[PlaybackTimelineEvent]:
    """
    Sort timeline events by timestamp_ms ascending, then event_type order.

    Order: note < finding < assignment < marker
    """
    return sorted(
        events,
        key=lambda e: (e.timestamp_ms, EVENT_TYPE_SORT_ORDER.get(e.event_type, 99)),
    )


def build_session_playback(
    *,
    session: SessionRecord,
    evaluation: CoachEvaluation,
    assignments: Optional[AssembledPracticeAssignmentSet] = None,
    user_id: Optional[str] = None,
    midi_events: Optional[list] = None,
) -> SessionPlaybackData:
    """
    Build complete playback data from session, evaluation, and assignments.

    Parameters
    ----------
    session:
        The practice session record.
    evaluation:
        The coaching evaluation with findings.
    assignments:
        Optional assembled practice assignments.
    user_id:
        Optional user identifier.
    midi_events:
        Optional list of MidiNoteEvent for building note events.

    Returns
    -------
    SessionPlaybackData with timeline events, finding overlays,
    and assignment references.
    """
    duration_ms = int(session.duration_s * 1000) if session.duration_s else 0

    note_events: list[PlaybackTimelineEvent] = []
    if midi_events:
        note_events = _build_note_events_from_midi(midi_events)

    finding_events, finding_timestamp_map = _build_finding_events(
        evaluation.findings
    )

    assignment_events: list[PlaybackTimelineEvent] = []
    assignment_refs: list[PlaybackAssignmentReference] = []

    if assignments:
        assignment_events = _build_assignment_events(
            assignments, finding_timestamp_map
        )
        assignment_refs = _build_assignment_references(
            assignments, evaluation.findings, finding_timestamp_map
        )

    all_events = note_events + finding_events + assignment_events
    sorted_events = _sort_timeline_events(all_events)

    finding_overlays = _build_finding_overlays(
        evaluation.findings, duration_ms
    )

    return SessionPlaybackData(
        session_id=str(session.session_id),
        user_id=user_id,
        generated_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        timeline_events=sorted_events,
        finding_overlays=finding_overlays,
        assignments=assignment_refs,
        version=PLAYBACK_VERSION,
    )


__all__ = [
    "PLAYBACK_VERSION",
    "DEFAULT_FINDING_WINDOW_MS",
    "build_session_playback",
]
