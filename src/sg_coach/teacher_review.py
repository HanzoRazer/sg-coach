"""
Teacher Review Builder.

Sprint 19: Teacher-facing review layer for student practice inspection.

Teacher review is additive metadata — it does not mutate system findings,
evaluations, or assignments.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sg_spec.schemas.coach_schemas import CoachEvaluation, SessionRecord, TargetSpan
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignmentSet
from sg_spec.schemas.practice_dashboard import PracticeDashboardData
from sg_spec.schemas.practice_review import SessionReview
from sg_spec.schemas.session_playback import SessionPlaybackData
from sg_spec.schemas.teacher_review import (
    TeacherAnnotation,
    TeacherAnnotationType,
    TeacherRecommendation,
    TeacherRecommendationType,
    TeacherReview,
)

from .practice_dashboard import build_practice_dashboard
from .practice_history import PracticeHistoryQuery, PracticeHistoryStore
from .practice_review import build_session_review
from .session_playback import build_session_playback


TEACHER_REVIEW_VERSION = "0.1"


def _generate_annotation_id() -> str:
    """Generate a unique annotation ID with ta_ prefix."""
    return f"ta_{secrets.token_hex(6)}"


def _generate_recommendation_id() -> str:
    """Generate a unique recommendation ID with tr_ prefix."""
    return f"tr_{secrets.token_hex(6)}"


def _reconstruct_session(entry_data: dict) -> Optional[SessionRecord]:
    """Reconstruct SessionRecord from history entry dict."""
    try:
        session_data = entry_data.get("session")
        if session_data:
            return SessionRecord.model_validate(session_data)
    except Exception:
        pass
    return None


def _reconstruct_evaluation(entry_data: dict) -> Optional[CoachEvaluation]:
    """Reconstruct CoachEvaluation from history entry dict."""
    try:
        evaluation_data = entry_data.get("evaluation")
        if evaluation_data:
            return CoachEvaluation.model_validate(evaluation_data)
    except Exception:
        pass
    return None


def _reconstruct_assignments(entry_data: dict) -> Optional[AssembledPracticeAssignmentSet]:
    """Reconstruct AssembledPracticeAssignmentSet from history entry dict."""
    try:
        assignments_data = entry_data.get("assignments")
        if assignments_data:
            return AssembledPracticeAssignmentSet.model_validate(assignments_data)
    except Exception:
        pass
    return None


def build_teacher_review(
    *,
    history_store: PracticeHistoryStore,
    session_id: Optional[str] = None,
    student_id: Optional[str] = None,
    teacher_id: Optional[str] = None,
    include_dashboard: bool = True,
    include_playback: bool = True,
) -> TeacherReview:
    """
    Build a teacher review from practice history.

    Parameters
    ----------
    history_store:
        The practice history store to read from.
    session_id:
        Optional session ID to include session review and playback.
    student_id:
        Student identifier for filtering and metadata.
    teacher_id:
        Teacher identifier for metadata.
    include_dashboard:
        Whether to include dashboard data (default True).
    include_playback:
        Whether to include playback data when session_id provided (default True).

    Returns
    -------
    TeacherReview with populated sections based on inputs.

    Notes
    -----
    If session_id is provided but reconstruction fails,
    the review degrades gracefully without that section.

    Teacher annotations/recommendations are not auto-generated.
    Use create_teacher_annotation/recommendation helpers.
    """
    dashboard: Optional[PracticeDashboardData] = None
    session_review: Optional[SessionReview] = None
    playback: Optional[SessionPlaybackData] = None

    if include_dashboard:
        try:
            dashboard = build_practice_dashboard(
                history_store=history_store,
                user_id=student_id,
            )
        except Exception:
            pass

    if session_id:
        try:
            session_review = build_session_review(
                session_id=session_id,
                history_store=history_store,
            )
        except Exception:
            pass

        entry = history_store.get_by_session_id(session_id)
        if entry and include_playback:
            entry_dict = entry.model_dump()

            session = _reconstruct_session(entry_dict)
            evaluation = _reconstruct_evaluation(entry_dict)
            assignments = _reconstruct_assignments(entry_dict)

            if session and evaluation:
                try:
                    playback = build_session_playback(
                        session=session,
                        evaluation=evaluation,
                        assignments=assignments,
                        user_id=student_id,
                    )
                except Exception:
                    pass

    return TeacherReview(
        teacher_id=teacher_id,
        student_id=student_id,
        session_review=session_review,
        dashboard=dashboard,
        playback=playback,
        annotations=[],
        recommendations=[],
        generated_at=datetime.now(timezone.utc),
        version=TEACHER_REVIEW_VERSION,
    )


def create_teacher_annotation(
    *,
    annotation_type: TeacherAnnotationType,
    text: str,
    teacher_id: Optional[str] = None,
    student_id: Optional[str] = None,
    session_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    assignment_id: Optional[str] = None,
    target_span: Optional[TargetSpan] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> TeacherAnnotation:
    """
    Create a teacher annotation with auto-generated ID.

    Parameters
    ----------
    annotation_type:
        Type of annotation (note, correction, encouragement, warning, assignment_adjustment).
    text:
        Annotation text (1-1000 characters).
    teacher_id:
        Optional teacher identifier.
    student_id:
        Optional student identifier.
    session_id:
        Optional session identifier.
    finding_id:
        Optional linked finding ID.
    assignment_id:
        Optional linked assignment ID.
    target_span:
        Optional time/position span.
    metadata:
        Optional additional metadata.

    Returns
    -------
    TeacherAnnotation with generated ta_<12hex> ID.
    """
    return TeacherAnnotation(
        id=_generate_annotation_id(),
        teacher_id=teacher_id,
        student_id=student_id,
        session_id=session_id,
        finding_id=finding_id,
        assignment_id=assignment_id,
        annotation_type=annotation_type,
        text=text,
        target_span=target_span,
        metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
        version=TEACHER_REVIEW_VERSION,
    )


def create_teacher_recommendation(
    *,
    recommendation_type: TeacherRecommendationType,
    text: str,
    teacher_id: Optional[str] = None,
    student_id: Optional[str] = None,
    session_id: Optional[str] = None,
    related_goal_id: Optional[str] = None,
    related_assignment_id: Optional[str] = None,
    related_finding_ids: Optional[Sequence[str]] = None,
    priority: int = 0,
    metadata: Optional[dict[str, Any]] = None,
) -> TeacherRecommendation:
    """
    Create a teacher recommendation with auto-generated ID.

    Parameters
    ----------
    recommendation_type:
        Type of recommendation.
    text:
        Recommendation text (1-1000 characters).
    teacher_id:
        Optional teacher identifier.
    student_id:
        Optional student identifier.
    session_id:
        Optional session identifier.
    related_goal_id:
        Optional related goal ID.
    related_assignment_id:
        Optional related assignment ID.
    related_finding_ids:
        Optional list of related finding IDs.
    priority:
        Priority level (0-10, default 0).
    metadata:
        Optional additional metadata.

    Returns
    -------
    TeacherRecommendation with generated tr_<12hex> ID.
    """
    return TeacherRecommendation(
        id=_generate_recommendation_id(),
        teacher_id=teacher_id,
        student_id=student_id,
        session_id=session_id,
        recommendation_type=recommendation_type,
        text=text,
        related_goal_id=related_goal_id,
        related_assignment_id=related_assignment_id,
        related_finding_ids=list(related_finding_ids) if related_finding_ids else [],
        priority=priority,
        metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
        version=TEACHER_REVIEW_VERSION,
    )


__all__ = [
    "TEACHER_REVIEW_VERSION",
    "build_teacher_review",
    "create_teacher_annotation",
    "create_teacher_recommendation",
]
