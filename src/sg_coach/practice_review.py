"""
Practice Review — Build timeline, session reviews, and progress summaries.

Sprint 12: Read-only review layer over practice history.

This module provides:
- build_session_review(): Single session review with findings/assignments
- build_practice_timeline(): Multi-session timeline query
- build_progress_summary(): Aggregated progress summary

Core rule: Review is read-only. Never mutate history.

Ownership: sg-coach (review builders)
Schemas: sg-spec (PracticeTimeline, SessionReview, PracticeProgressSummary)
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachEvaluation, SessionRecord
from sg_spec.schemas.feedback_vocabulary import FeedbackDomain
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
)
from sg_spec.schemas.practice_review import (
    PracticeProgressSummary,
    PracticeTimeline,
    PracticeTimelineEntry,
    SessionReview,
)

from .practice_history import PracticeHistoryEntry, PracticeHistoryStore


def _reconstruct_session(entry: PracticeHistoryEntry) -> SessionRecord:
    """Reconstruct SessionRecord from history entry."""
    return SessionRecord.model_validate(entry.session)


def _reconstruct_evaluation(entry: PracticeHistoryEntry) -> Optional[CoachEvaluation]:
    """Reconstruct CoachEvaluation from history entry."""
    if not entry.evaluation:
        return None
    return CoachEvaluation.model_validate(entry.evaluation)


def _reconstruct_assignments(entry: PracticeHistoryEntry) -> Optional[AssembledPracticeAssignmentSet]:
    """Reconstruct AssembledPracticeAssignmentSet from history entry."""
    if not entry.assignments:
        return None
    return AssembledPracticeAssignmentSet.model_validate(entry.assignments)


def _count_findings_by_domain(evaluation: Optional[CoachEvaluation]) -> Dict[str, int]:
    """Count findings by FeedbackDomain.value."""
    if evaluation is None:
        return {}

    counts: Dict[str, int] = {}
    for finding in evaluation.findings:
        domain = finding.normalized_domain
        key = domain.value
        counts[key] = counts.get(key, 0) + 1

    return counts


def _count_assignments_by_status(
    assignments: Optional[AssembledPracticeAssignmentSet],
) -> Dict[str, int]:
    """Count assignments by PracticeAssignmentStatus.value."""
    if assignments is None:
        return {}

    counts: Dict[str, int] = {}
    for assignment in assignments.assignments:
        key = assignment.status.value
        counts[key] = counts.get(key, 0) + 1

    return counts


def _top_diagnosis_codes(
    evaluation: Optional[CoachEvaluation],
    limit: int = 3,
) -> List[DiagnosisCode]:
    """
    Get most frequent diagnosis codes from evaluation.

    Returns codes sorted by frequency descending, with stable order for ties.
    """
    if evaluation is None:
        return []

    code_counts: Counter[DiagnosisCode] = Counter()
    for finding in evaluation.findings:
        if finding.code is not None:
            code_counts[finding.code] += 1

    sorted_codes = sorted(
        code_counts.keys(),
        key=lambda c: (-code_counts[c], c.value),
    )

    return sorted_codes[:limit]


def _generate_summary(
    evaluation: Optional[CoachEvaluation],
    assignments: Optional[AssembledPracticeAssignmentSet],
) -> Optional[str]:
    """
    Generate a deterministic summary string.

    Returns None if insufficient data exists.
    """
    finding_count = len(evaluation.findings) if evaluation else 0
    assignment_count = len(assignments.assignments) if assignments else 0

    if finding_count == 0 and assignment_count == 0:
        return None

    parts = []

    if finding_count > 0 and evaluation:
        domain_counts = _count_findings_by_domain(evaluation)
        domain_parts = [
            f"{count} {domain}" for domain, count in sorted(domain_counts.items())
        ]
        if domain_parts:
            findings_str = ", ".join(domain_parts)
            parts.append(f"{findings_str} finding{'s' if finding_count != 1 else ''}")

    if assignment_count > 0:
        parts.append(f"{assignment_count} assignment{'s' if assignment_count != 1 else ''} generated")

    if not parts:
        return None

    return ". ".join(parts) + "."


def build_session_review(
    *,
    session_id: str,
    history_store: PracticeHistoryStore,
) -> Optional[SessionReview]:
    """
    Build a session review from practice history.

    Parameters
    ----------
    session_id:
        The session ID to review.
    history_store:
        The practice history store.

    Returns
    -------
    SessionReview if found, None otherwise.

    Notes
    -----
    - Read-only: does not mutate history
    - Reconstructs models from stored dicts
    - Computes findings_by_domain and assignment_status_counts
    - Generates summary if sufficient data exists
    """
    entry = history_store.get_by_session_id(session_id)
    if entry is None:
        return None

    session = _reconstruct_session(entry)
    evaluation = _reconstruct_evaluation(entry)
    assignments = _reconstruct_assignments(entry)

    findings_by_domain = _count_findings_by_domain(evaluation)
    assignment_status_counts = _count_assignments_by_status(assignments)
    summary = _generate_summary(evaluation, assignments)

    return SessionReview(
        session_id=session_id,
        session=session,
        evaluation=evaluation,
        assignments=assignments,
        findings_by_domain=findings_by_domain,
        assignment_status_counts=assignment_status_counts,
        summary=summary,
    )


def build_practice_timeline(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> PracticeTimeline:
    """
    Build a practice timeline from history.

    Parameters
    ----------
    history_store:
        The practice history store.
    user_id:
        Optional user ID filter.
    limit:
        Optional limit on number of entries.

    Returns
    -------
    PracticeTimeline with entries sorted by timestamp descending.

    Notes
    -----
    - Read-only: does not mutate history
    - Entries are sorted most recent first
    - total_sessions reflects full count before limit
    """
    from .practice_history import PracticeHistoryQuery

    query = PracticeHistoryQuery(user_id=user_id)
    all_entries = history_store.query(query)

    sorted_entries = sorted(
        all_entries,
        key=lambda e: e.timestamp,
        reverse=True,
    )

    total_sessions = len(sorted_entries)

    if limit is not None:
        sorted_entries = sorted_entries[:limit]

    timeline_entries: List[PracticeTimelineEntry] = []

    for entry in sorted_entries:
        evaluation = _reconstruct_evaluation(entry)
        top_codes = _top_diagnosis_codes(evaluation, limit=3)

        program_ref = None
        if entry.session and "program_ref" in entry.session:
            program_ref = entry.session["program_ref"]

        timeline_entry = PracticeTimelineEntry(
            session_id=entry.session_id,
            user_id=entry.user_id,
            instrument_id=entry.instrument_id,
            timestamp=entry.timestamp,
            program_ref=program_ref,
            finding_count=entry.findings_count,
            assignment_count=entry.assignments_count,
            top_diagnosis_codes=top_codes,
            status="reviewable",
        )
        timeline_entries.append(timeline_entry)

    return PracticeTimeline(
        entries=timeline_entries,
        total_sessions=total_sessions,
    )


def build_progress_summary(
    *,
    history_store: PracticeHistoryStore,
    user_id: Optional[str] = None,
) -> PracticeProgressSummary:
    """
    Build a progress summary from practice history.

    Parameters
    ----------
    history_store:
        The practice history store.
    user_id:
        Optional user ID filter.

    Returns
    -------
    PracticeProgressSummary aggregating all history for the user.

    Notes
    -----
    - Read-only: does not mutate history
    - Covers all history (no date range in v1)
    - recent_diagnosis_codes from most recent session with findings
    """
    from .practice_history import PracticeHistoryQuery

    query = PracticeHistoryQuery(user_id=user_id)
    all_entries = history_store.query(query)

    if not all_entries:
        return PracticeProgressSummary(
            user_id=user_id,
            session_count=0,
            total_findings=0,
            total_assignments=0,
        )

    sorted_entries = sorted(
        all_entries,
        key=lambda e: e.timestamp,
        reverse=True,
    )

    session_count = len(sorted_entries)
    total_findings = sum(e.findings_count for e in sorted_entries)
    total_assignments = sum(e.assignments_count for e in sorted_entries)

    diagnosis_counts: Counter[str] = Counter()
    for entry in sorted_entries:
        evaluation = _reconstruct_evaluation(entry)
        if evaluation:
            for finding in evaluation.findings:
                if finding.code is not None:
                    diagnosis_counts[finding.code.value] += 1

    recent_diagnosis_codes: List[DiagnosisCode] = []
    for entry in sorted_entries:
        evaluation = _reconstruct_evaluation(entry)
        if evaluation and evaluation.findings:
            seen: set[str] = set()
            for finding in evaluation.findings:
                if finding.code is not None and finding.code.value not in seen:
                    recent_diagnosis_codes.append(finding.code)
                    seen.add(finding.code.value)
            break

    return PracticeProgressSummary(
        user_id=user_id,
        session_count=session_count,
        total_findings=total_findings,
        total_assignments=total_assignments,
        diagnosis_counts=dict(diagnosis_counts),
        recent_diagnosis_codes=recent_diagnosis_codes,
    )


__all__ = [
    "build_session_review",
    "build_practice_timeline",
    "build_progress_summary",
]
