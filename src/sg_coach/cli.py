"""
CLI for sg-coach.

Sprint 11: Minimal CLI for coaching evaluation.
Sprint 15: Extended with review, goals, timeline commands.
Sprint 31: Teacher scheduling mediation commands.
Sprint 33: Pedagogical timeline visualization commands.
Sprint 34: Guided practice session UX projection commands.
Sprint 35: Pedagogical narrative projection commands.
Sprint 36: Session workspace projection commands.
Sprint 37: Workspace export commands.
Sprint 38: Frontend state projection commands.
Sprint 39: Frontend interaction event commands.
Sprint 41: Governance check commands.

Usage:
    sg-coach evaluate <session.json>
    sg-coach evaluate --midi <midi_input.json>
    sg-coach evaluate --midi <midi_input.json> --persist <history.jsonl>
    sg-coach review --history <history.jsonl>
    sg-coach goals --history <history.jsonl>
    sg-coach timeline --history <history.jsonl>
    sg-coach mediation submit --recommendation <rec.json> --teacher-id <id> --action approve
    sg-coach mediation apply --mediation <med.json> --recommendation <rec.json> --queue <queue.json>
    sg-coach timeline-view --ledger <ledger.json> [--student-id <id>] [--pretty]
    sg-coach guided-session-view [--queue <queue.json>] [--assignment <assignment.json>] [--pretty]
    sg-coach narrative guided-session --session-view <view.json> [--audience mixed] [--pretty]
    sg-coach narrative runtime-review --review <review.json> [--audience teacher] [--pretty]
    sg-coach narrative longitudinal-review --review <review.json> [--audience teacher] [--pretty]
    sg-coach workspace session --session-view <view.json> [--narrative <narrative.json>] [--pretty]
    sg-coach workspace export --workspace <workspace.json> [--redaction none] [--output <file>] [--pretty]
    sg-coach workspace frontend-state --workspace <workspace.json> [--output <file>] [--pretty]
    sg-coach frontend-event apply --state <state.json> --event <event.json> [--pretty]
    sg-coach frontend-event replay --state <state.json> --events <events.jsonl> [--pretty]
    sg-coach governance check --repo-root <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from sg_spec.schemas.coach_schemas import CoachEvaluation
from sg_spec.schemas.drill_resolution import DrillResolutionResult
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType

from .coach_policy import evaluate_session, COACH_VERSION
from .session_builder import build_session_from_midi, ENGINE_VERSION
from .recommendation_integration import attach_recommendations
from .practice_assignment_assembler import assemble_practice_assignments
from .drill_resolver import resolve_drill, request_from_recommended_action
from .practice_history import PracticeHistoryStore
from .practice_review import build_practice_timeline, build_progress_summary
from .goal_tracking import build_weakness_progressions, generate_practice_goals
from .practice_dashboard import build_practice_dashboard
from .session_playback import build_session_playback
from .teacher_review import build_teacher_review
from .studio_roster_store import StudioRosterStore
from .practice_queue import (
    build_practice_queue,
    next_queue_assignment,
    QUEUE_VERSION,
)
from .practice_queue_store import PracticeQueueStore
from .schemas import SessionRecord


def _resolve_drills_for_evaluation(evaluation: CoachEvaluation) -> list[DrillResolutionResult]:
    """Resolve drills for all recommendations in an evaluation."""
    results: list[DrillResolutionResult] = []
    if not evaluation.recommendations:
        return results

    for rec_set in evaluation.recommendations:
        diagnosis_code = rec_set.finding_code
        if not diagnosis_code:
            continue

        for action in rec_set.actions:
            if action.action_type != FeedbackActionType.assign_drill:
                continue

            request = request_from_recommended_action(
                diagnosis_code=diagnosis_code,
                action=action,
            )
            result = resolve_drill(request)
            results.append(result)

    return results


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_from_session_file(
    path: Path,
    *,
    verbose: bool = False,
    persist_path: Optional[Path] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Evaluate a session from JSON file."""
    data = load_json(path)
    session = SessionRecord.model_validate(data)
    evaluation = evaluate_session(session)
    evaluation_with_recs = attach_recommendations(evaluation)

    drill_results = _resolve_drills_for_evaluation(evaluation_with_recs)

    assignments = assemble_practice_assignments(
        findings=evaluation_with_recs.findings,
        recommendation_sets=evaluation_with_recs.recommendations or [],
        drill_results=drill_results,
    )

    if persist_path:
        store = PracticeHistoryStore(persist_path)
        entry = store.append_session(
            session=session,
            evaluation=evaluation_with_recs,
            assignments=assignments,
            user_id=user_id,
        )
        entry_id = entry.id
    else:
        entry_id = None

    result = {
        "session_id": str(session.session_id),
        "coach_version": COACH_VERSION,
        "findings_count": len(evaluation.findings),
        "findings": [f.model_dump() for f in evaluation.findings],
        "recommendations_count": len(evaluation_with_recs.recommendations or []),
        "assignments_count": len(assignments.assignments),
        "assignments": [a.model_dump() for a in assignments.assignments],
    }

    if entry_id:
        result["history_entry_id"] = entry_id

    if verbose:
        result["focus_recommendation"] = evaluation.focus_recommendation.model_dump()
        result["strengths"] = evaluation.strengths
        result["weaknesses"] = evaluation.weaknesses

    return result


def evaluate_from_midi_file(
    path: Path,
    *,
    verbose: bool = False,
    persist_path: Optional[Path] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Evaluate from MIDI input JSON file."""
    from sg_spec.schemas.midi_session import MidiSessionInput

    data = load_json(path)
    midi_input = MidiSessionInput.model_validate(data)
    session = build_session_from_midi(midi_input)

    evaluation = evaluate_session(session)
    evaluation_with_recs = attach_recommendations(evaluation)

    drill_results = _resolve_drills_for_evaluation(evaluation_with_recs)

    assignments = assemble_practice_assignments(
        findings=evaluation_with_recs.findings,
        recommendation_sets=evaluation_with_recs.recommendations or [],
        drill_results=drill_results,
    )

    if persist_path:
        store = PracticeHistoryStore(persist_path)
        entry = store.append_session(
            session=session,
            evaluation=evaluation_with_recs,
            assignments=assignments,
            user_id=user_id,
        )
        entry_id = entry.id
    else:
        entry_id = None

    result = {
        "session_id": str(session.session_id),
        "engine_version": ENGINE_VERSION,
        "coach_version": COACH_VERSION,
        "input_type": "midi",
        "findings_count": len(evaluation.findings),
        "findings": [f.model_dump() for f in evaluation.findings],
        "recommendations_count": len(evaluation_with_recs.recommendations or []),
        "assignments_count": len(assignments.assignments),
        "assignments": [a.model_dump() for a in assignments.assignments],
    }

    if entry_id:
        result["history_entry_id"] = entry_id

    if verbose:
        result["focus_recommendation"] = evaluation.focus_recommendation.model_dump()
        result["strengths"] = evaluation.strengths
        result["weaknesses"] = evaluation.weaknesses

    return result


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Handle evaluate command."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    persist_path = Path(args.persist) if args.persist else None
    user_id = args.user_id if hasattr(args, 'user_id') else None

    try:
        if args.midi:
            result = evaluate_from_midi_file(
                input_path,
                verbose=args.verbose,
                persist_path=persist_path,
                user_id=user_id,
            )
        else:
            result = evaluate_from_session_file(
                input_path,
                verbose=args.verbose,
                persist_path=persist_path,
                user_id=user_id,
            )

        print(json.dumps(result, indent=2, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Handle version command."""
    print(f"sg-coach {COACH_VERSION}")
    print(f"engine {ENGINE_VERSION}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Handle review command — show timeline and progress summary."""
    history_path = Path(args.history)
    if not history_path.exists():
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        return 1

    store = PracticeHistoryStore(history_path)
    user_id = getattr(args, 'user_id', None)
    limit = getattr(args, 'limit', None)

    timeline = build_practice_timeline(
        history_store=store,
        user_id=user_id,
        limit=limit,
    )
    progress = build_progress_summary(
        history_store=store,
        user_id=user_id,
    )

    output = {
        "timeline": timeline.model_dump(mode="json"),
        "progress": progress.model_dump(mode="json"),
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_goals(args: argparse.Namespace) -> int:
    """Handle goals command — show practice goals."""
    history_path = Path(args.history)
    if not history_path.exists():
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        return 1

    store = PracticeHistoryStore(history_path)
    user_id = getattr(args, 'user_id', None)

    progressions = build_weakness_progressions(
        history_store=store,
        user_id=user_id,
    )
    goals = generate_practice_goals(progressions=progressions)

    output = {
        "goals": [g.model_dump(mode="json") for g in goals],
        "progressions": [p.model_dump(mode="json") for p in progressions],
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_timeline(args: argparse.Namespace) -> int:
    """Handle timeline command — show practice timeline."""
    history_path = Path(args.history)
    if not history_path.exists():
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        return 1

    store = PracticeHistoryStore(history_path)
    user_id = getattr(args, 'user_id', None)
    limit = getattr(args, 'limit', None)

    timeline = build_practice_timeline(
        history_store=store,
        user_id=user_id,
        limit=limit,
    )

    output = timeline.model_dump(mode="json")

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Handle dashboard command — show practice dashboard data."""
    history_path = Path(args.history)
    if not history_path.exists():
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        return 1

    store = PracticeHistoryStore(history_path)
    user_id = getattr(args, 'user_id', None)

    dashboard = build_practice_dashboard(
        history_store=store,
        user_id=user_id,
    )

    output = dashboard.model_dump(mode="json")

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_playback(args: argparse.Namespace) -> int:
    """Handle playback command — build session playback data."""
    from sg_spec.schemas.coach_schemas import CoachEvaluation
    from sg_spec.schemas.practice_assignment import AssembledPracticeAssignmentSet

    session_path = Path(args.session)
    if not session_path.exists():
        print(f"Error: Session file not found: {session_path}", file=sys.stderr)
        return 1

    evaluation_path = Path(args.evaluation)
    if not evaluation_path.exists():
        print(f"Error: Evaluation file not found: {evaluation_path}", file=sys.stderr)
        return 1

    assignments = None
    if args.assignments:
        assignments_path = Path(args.assignments)
        if not assignments_path.exists():
            print(f"Error: Assignments file not found: {assignments_path}", file=sys.stderr)
            return 1
        assignments_data = load_json(assignments_path)
        assignments = AssembledPracticeAssignmentSet.model_validate(assignments_data)

    try:
        session_data = load_json(session_path)
        session = SessionRecord.model_validate(session_data)

        evaluation_data = load_json(evaluation_path)
        evaluation = CoachEvaluation.model_validate(evaluation_data)

        user_id = getattr(args, 'user_id', None)

        playback = build_session_playback(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id=user_id,
        )

        output = playback.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        return 1


def cmd_teacher_review(args: argparse.Namespace) -> int:
    """Handle teacher-review command — build teacher review data."""
    history_path = Path(args.history)
    if not history_path.exists():
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        return 1

    store = PracticeHistoryStore(history_path)
    session_id = getattr(args, 'session_id', None)
    student_id = getattr(args, 'student_id', None)
    teacher_id = getattr(args, 'teacher_id', None)

    review = build_teacher_review(
        history_store=store,
        session_id=session_id,
        student_id=student_id,
        teacher_id=teacher_id,
        include_dashboard=True,
        include_playback=True,
    )

    output = review.model_dump(mode="json")

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_create(args: argparse.Namespace) -> int:
    """Handle studio create command."""
    roster_path = Path(args.roster)
    store = StudioRosterStore(roster_path)

    studio = store.create_studio(
        name=args.name,
        studio_id=getattr(args, 'studio_id', None),
    )

    output = {
        "studio_id": studio.studio_id,
        "name": studio.name,
        "created_at": studio.created_at.isoformat(),
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_add_student(args: argparse.Namespace) -> int:
    """Handle studio add-student command."""
    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}", file=sys.stderr)
        return 1

    store = StudioRosterStore(roster_path)
    studio_id = getattr(args, 'studio_id', None)

    try:
        student = store.add_student(
            studio_id=store._resolve_studio_id(studio_id),
            display_name=args.name,
            student_id=getattr(args, 'student_id', None),
            notes=getattr(args, 'notes', None),
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = {
        "student_id": student.student_id,
        "display_name": student.display_name,
        "active": student.active,
        "enrollment_date": student.enrollment_date.isoformat(),
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_add_teacher(args: argparse.Namespace) -> int:
    """Handle studio add-teacher command."""
    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}", file=sys.stderr)
        return 1

    store = StudioRosterStore(roster_path)
    studio_id = getattr(args, 'studio_id', None)

    try:
        teacher = store.add_teacher(
            studio_id=store._resolve_studio_id(studio_id),
            display_name=args.name,
            teacher_id=getattr(args, 'teacher_id', None),
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = {
        "teacher_id": teacher.teacher_id,
        "display_name": teacher.display_name,
        "active": teacher.active,
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_list_students(args: argparse.Namespace) -> int:
    """Handle studio list-students command."""
    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}", file=sys.stderr)
        return 1

    store = StudioRosterStore(roster_path)
    studio_id = getattr(args, 'studio_id', None)
    active_only = not getattr(args, 'all', False)

    try:
        students = store.list_students(
            studio_id=studio_id,
            active_only=active_only,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = {
        "count": len(students),
        "students": [
            {
                "student_id": s.student_id,
                "display_name": s.display_name,
                "active": s.active,
                "enrollment_date": s.enrollment_date.isoformat(),
                "notes": s.notes,
            }
            for s in students
        ],
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_list_teachers(args: argparse.Namespace) -> int:
    """Handle studio list-teachers command."""
    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}", file=sys.stderr)
        return 1

    store = StudioRosterStore(roster_path)
    studio_id = getattr(args, 'studio_id', None)
    active_only = not getattr(args, 'all', False)

    try:
        teachers = store.list_teachers(
            studio_id=studio_id,
            active_only=active_only,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = {
        "count": len(teachers),
        "teachers": [
            {
                "teacher_id": t.teacher_id,
                "display_name": t.display_name,
                "active": t.active,
            }
            for t in teachers
        ],
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_studio_overview(args: argparse.Namespace) -> int:
    """Handle studio overview command."""
    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}", file=sys.stderr)
        return 1

    store = StudioRosterStore(roster_path)
    studio_id = getattr(args, 'studio_id', None)

    try:
        overview = store.build_overview(studio_id=studio_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = overview.model_dump(mode="json")

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_queue_build(args: argparse.Namespace) -> int:
    """Handle queue build command."""
    from sg_spec.schemas.practice_assignment import (
        AssembledPracticeAssignment,
        AssembledPracticeAssignmentSet,
    )

    assignments_path = Path(args.assignments)
    if not assignments_path.exists():
        print(f"Error: Assignments file not found: {assignments_path}", file=sys.stderr)
        return 1

    try:
        data = load_json(assignments_path)

        if "assignments" in data:
            assignment_set = AssembledPracticeAssignmentSet.model_validate(data)
            assignments = assignment_set.assignments
        else:
            assignments = [AssembledPracticeAssignment.model_validate(a) for a in data]

        student_id = getattr(args, 'student_id', None)

        queue = build_practice_queue(
            assignments=assignments,
            student_id=student_id,
        )

        output = queue.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_queue_next(args: argparse.Namespace) -> int:
    """Handle queue next command."""
    from sg_spec.schemas.practice_queue import PracticeQueue

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
        return 1

    try:
        data = load_json(queue_path)
        queue = PracticeQueue.model_validate(data)

        next_assignment = next_queue_assignment(queue)

        if next_assignment is None:
            output = {"next_assignment": None, "message": "No eligible assignments"}
        else:
            output = {
                "next_assignment": next_assignment.model_dump(mode="json"),
            }

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_queue_complete(args: argparse.Namespace) -> int:
    """Handle queue complete command."""
    store_path = Path(args.store)
    if not store_path.exists():
        print(f"Error: Store file not found: {store_path}", file=sys.stderr)
        return 1

    store = PracticeQueueStore(store_path)
    queue_id = getattr(args, 'queue_id', None)
    assignment_id = args.assignment_id

    if queue_id is None:
        queue = store.load_queue()
        if queue.id:
            queue_id = queue.id
        else:
            print("Error: No queue_id found in store", file=sys.stderr)
            return 1

    event = store.mark_completed(
        queue_id=queue_id,
        assignment_id=assignment_id,
    )

    output = {
        "event_id": event.id,
        "event_type": event.event_type.value,
        "assignment_id": event.assignment_id,
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_queue_defer(args: argparse.Namespace) -> int:
    """Handle queue defer command."""
    from datetime import datetime, timezone, timedelta

    store_path = Path(args.store)
    if not store_path.exists():
        print(f"Error: Store file not found: {store_path}", file=sys.stderr)
        return 1

    store = PracticeQueueStore(store_path)
    queue_id = getattr(args, 'queue_id', None)
    assignment_id = args.assignment_id
    defer_hours = getattr(args, 'hours', None)

    if queue_id is None:
        queue = store.load_queue()
        if queue.id:
            queue_id = queue.id
        else:
            print("Error: No queue_id found in store", file=sys.stderr)
            return 1

    deferred_until = None
    if defer_hours:
        deferred_until = datetime.now(timezone.utc) + timedelta(hours=defer_hours)

    event = store.mark_deferred(
        queue_id=queue_id,
        assignment_id=assignment_id,
        deferred_until=deferred_until,
    )

    output = {
        "event_id": event.id,
        "event_type": event.event_type.value,
        "assignment_id": event.assignment_id,
        "deferred_until": event.metadata.get("deferred_until"),
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def _load_assignments_lookup(assignments_path: Path) -> dict[str, Any]:
    """Load assignments from file and return lookup dict."""
    from sg_spec.schemas.practice_assignment import (
        AssembledPracticeAssignment,
        AssembledPracticeAssignmentSet,
    )

    data = load_json(assignments_path)

    if isinstance(data, list):
        assignments = [AssembledPracticeAssignment.model_validate(a) for a in data]
        return {a.id: a for a in assignments if a.id}
    elif "assignments" in data:
        assignment_set = AssembledPracticeAssignmentSet.model_validate(data)
        return {a.id: a for a in assignment_set.assignments if a.id}
    else:
        return {k: AssembledPracticeAssignment.model_validate(v) for k, v in data.items()}


def cmd_runtime_start_next(args: argparse.Namespace) -> int:
    """Handle runtime start-next command."""
    from sg_spec.schemas.practice_queue import PracticeQueue

    from .runtime_flow import start_next_queue_assignment

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
        return 1

    assignments_path = Path(args.assignments)
    if not assignments_path.exists():
        print(f"Error: Assignments file not found: {assignments_path}", file=sys.stderr)
        return 1

    try:
        queue_data = load_json(queue_path)
        queue = PracticeQueue.model_validate(queue_data)

        assignments_lookup = _load_assignments_lookup(assignments_path)

        def lookup(aid: str):
            return assignments_lookup.get(aid)

        runtime_session, updated_queue, queue_event, runtime_event = start_next_queue_assignment(
            queue=queue,
            assignment_lookup=lookup,
        )

        if runtime_session is None:
            output = {
                "runtime_session": None,
                "message": "No eligible assignments",
            }
        else:
            output = {
                "runtime_session": runtime_session.model_dump(mode="json"),
                "updated_queue": updated_queue.model_dump(mode="json"),
                "queue_event": queue_event.model_dump(mode="json") if queue_event else None,
                "runtime_event": runtime_event.model_dump(mode="json") if runtime_event else None,
            }

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_runtime_complete(args: argparse.Namespace) -> int:
    """Handle runtime complete command."""
    from sg_spec.schemas.practice_queue import PracticeQueue
    from sg_spec.schemas.curriculum_progression import CurriculumProgressState
    from sg_spec.schemas.runtime_flow import RuntimePracticeSession
    from sg_spec.schemas.user_feedback import PracticeOutcome

    from .runtime_flow import complete_runtime_session

    runtime_session_path = Path(args.runtime_session)
    if not runtime_session_path.exists():
        print(f"Error: Runtime session file not found: {runtime_session_path}", file=sys.stderr)
        return 1

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
        return 1

    progress_path = Path(args.progress)
    if not progress_path.exists():
        print(f"Error: Progress file not found: {progress_path}", file=sys.stderr)
        return 1

    try:
        runtime_session_data = load_json(runtime_session_path)
        runtime_session = RuntimePracticeSession.model_validate(runtime_session_data)

        queue_data = load_json(queue_path)
        queue = PracticeQueue.model_validate(queue_data)

        progress_data = load_json(progress_path)
        progress = CurriculumProgressState.model_validate(progress_data)

        outcome_str = args.outcome.lower()
        outcome = PracticeOutcome(outcome_str)

        result, runtime_event = complete_runtime_session(
            runtime_session=runtime_session,
            outcome=outcome,
            queue=queue,
            progress_state=progress,
        )

        output = {
            "result": result.model_dump(mode="json"),
            "runtime_event": runtime_event.model_dump(mode="json"),
        }

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_runtime_abandon(args: argparse.Namespace) -> int:
    """Handle runtime abandon command."""
    from sg_spec.schemas.practice_queue import PracticeQueue
    from sg_spec.schemas.runtime_flow import RuntimePracticeSession

    from .runtime_flow import abandon_runtime_session

    runtime_session_path = Path(args.runtime_session)
    if not runtime_session_path.exists():
        print(f"Error: Runtime session file not found: {runtime_session_path}", file=sys.stderr)
        return 1

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
        return 1

    try:
        runtime_session_data = load_json(runtime_session_path)
        runtime_session = RuntimePracticeSession.model_validate(runtime_session_data)

        queue_data = load_json(queue_path)
        queue = PracticeQueue.model_validate(queue_data)

        abandoned_session, updated_queue, queue_event, runtime_event = abandon_runtime_session(
            runtime_session=runtime_session,
            queue=queue,
        )

        output = {
            "abandoned_session": abandoned_session.model_dump(mode="json"),
            "updated_queue": updated_queue.model_dump(mode="json"),
            "queue_event": queue_event.model_dump(mode="json"),
            "runtime_event": runtime_event.model_dump(mode="json"),
        }

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_runtime_attach_evidence(args: argparse.Namespace) -> int:
    """Handle runtime attach-evidence command."""
    from sg_spec.schemas.coach_schemas import CoachEvaluation, SessionRecord
    from sg_spec.schemas.runtime_flow import RuntimePracticeSession

    from .runtime_flow import attach_runtime_evidence

    runtime_session_path = Path(args.runtime_session)
    if not runtime_session_path.exists():
        print(f"Error: Runtime session file not found: {runtime_session_path}", file=sys.stderr)
        return 1

    session_path = Path(args.session)
    if not session_path.exists():
        print(f"Error: Session file not found: {session_path}", file=sys.stderr)
        return 1

    evaluation_path = Path(args.evaluation)
    if not evaluation_path.exists():
        print(f"Error: Evaluation file not found: {evaluation_path}", file=sys.stderr)
        return 1

    try:
        runtime_session_data = load_json(runtime_session_path)
        runtime_session = RuntimePracticeSession.model_validate(runtime_session_data)

        session_data = load_json(session_path)
        session_record = SessionRecord.model_validate(session_data)

        evaluation_data = load_json(evaluation_path)
        evaluation = CoachEvaluation.model_validate(evaluation_data)

        result = attach_runtime_evidence(
            runtime_session=runtime_session,
            session_record=session_record,
            evaluation=evaluation,
        )

        output = {
            "result": result.model_dump(mode="json"),
        }

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_runtime_review(args: argparse.Namespace) -> int:
    """Handle runtime review command."""
    from sg_spec.schemas.runtime_flow import RuntimePracticeSession, RuntimeSessionResult

    from .runtime_review import build_runtime_review_report

    runtime_session_path = Path(args.runtime_session)
    if not runtime_session_path.exists():
        print(f"Error: Runtime session file not found: {runtime_session_path}", file=sys.stderr)
        return 1

    runtime_result_path = Path(args.runtime_result) if args.runtime_result else None
    if runtime_result_path and not runtime_result_path.exists():
        print(f"Error: Runtime result file not found: {runtime_result_path}", file=sys.stderr)
        return 1

    try:
        runtime_session_data = load_json(runtime_session_path)
        runtime_session = RuntimePracticeSession.model_validate(runtime_session_data)

        runtime_result = None
        if runtime_result_path:
            runtime_result_data = load_json(runtime_result_path)
            runtime_result = RuntimeSessionResult.model_validate(runtime_result_data)

        report = build_runtime_review_report(
            runtime_session=runtime_session,
            runtime_result=runtime_result,
        )

        output = report.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_runtime_longitudinal_review(args: argparse.Namespace) -> int:
    """Handle runtime longitudinal-review command."""
    from sg_spec.schemas.runtime_review import RuntimeReviewReport

    from .longitudinal_review import build_longitudinal_progress_review

    reports_path = Path(args.reports)
    if not reports_path.exists():
        print(f"Error: Reports file not found: {reports_path}", file=sys.stderr)
        return 1

    try:
        reports = []
        with reports_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                report = RuntimeReviewReport.model_validate(data)
                reports.append(report)

        student_id = getattr(args, 'student_id', None)

        review = build_longitudinal_progress_review(
            reports=reports,
            student_id=student_id,
        )

        output = review.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_ledger_build(args: argparse.Namespace) -> int:
    """Handle ledger build command."""
    from sg_spec.schemas.runtime_review import RuntimeReviewReport
    from sg_spec.schemas.practice_queue import PracticeQueueEvent
    from sg_spec.schemas.teacher_review import TeacherReview

    from .pedagogical_ledger import build_pedagogical_evidence_ledger

    runtime_reviews = []
    queue_events = []
    teacher_reviews = []

    if args.runtime_reviews:
        runtime_reviews_path = Path(args.runtime_reviews)
        if not runtime_reviews_path.exists():
            print(f"Error: Runtime reviews file not found: {runtime_reviews_path}", file=sys.stderr)
            return 1

        with runtime_reviews_path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                data = json.loads(content)
                runtime_reviews = [RuntimeReviewReport.model_validate(r) for r in data]
            else:
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    runtime_reviews.append(RuntimeReviewReport.model_validate(data))

    if args.queue_events:
        queue_events_path = Path(args.queue_events)
        if not queue_events_path.exists():
            print(f"Error: Queue events file not found: {queue_events_path}", file=sys.stderr)
            return 1

        with queue_events_path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                data = json.loads(content)
                queue_events = [PracticeQueueEvent.model_validate(e) for e in data]
            else:
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    queue_events.append(PracticeQueueEvent.model_validate(data))

    if args.teacher_reviews:
        teacher_reviews_path = Path(args.teacher_reviews)
        if not teacher_reviews_path.exists():
            print(f"Error: Teacher reviews file not found: {teacher_reviews_path}", file=sys.stderr)
            return 1

        with teacher_reviews_path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                data = json.loads(content)
                teacher_reviews = [TeacherReview.model_validate(r) for r in data]
            else:
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    teacher_reviews.append(TeacherReview.model_validate(data))

    student_id = getattr(args, 'student_id', None)

    ledger = build_pedagogical_evidence_ledger(
        runtime_reviews=runtime_reviews,
        queue_events=queue_events,
        teacher_reviews=teacher_reviews,
        student_id=student_id,
    )

    output = ledger.model_dump(mode="json")

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_ledger_summary(args: argparse.Namespace) -> int:
    """Handle ledger summary command."""
    from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceLedger

    from .pedagogical_ledger import build_pedagogical_evidence_summary

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"Error: Ledger file not found: {ledger_path}", file=sys.stderr)
        return 1

    try:
        data = load_json(ledger_path)
        ledger = PedagogicalEvidenceLedger.model_validate(data)

        summary = build_pedagogical_evidence_summary(ledger)

        output = summary.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_queue_abandon(args: argparse.Namespace) -> int:
    """Handle queue abandon command."""
    store_path = Path(args.store)
    if not store_path.exists():
        print(f"Error: Store file not found: {store_path}", file=sys.stderr)
        return 1

    store = PracticeQueueStore(store_path)
    queue_id = getattr(args, 'queue_id', None)
    assignment_id = args.assignment_id

    if queue_id is None:
        queue = store.load_queue()
        if queue.id:
            queue_id = queue.id
        else:
            print("Error: No queue_id found in store", file=sys.stderr)
            return 1

    event = store.mark_abandoned(
        queue_id=queue_id,
        assignment_id=assignment_id,
    )

    output = {
        "event_id": event.id,
        "event_type": event.event_type.value,
        "assignment_id": event.assignment_id,
    }

    indent = 2 if getattr(args, 'pretty', False) else None
    print(json.dumps(output, indent=indent, default=str))
    return 0


def cmd_adaptive_scheduling(args: argparse.Namespace) -> int:
    """Handle adaptive-scheduling command."""
    from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceLedger
    from sg_spec.schemas.practice_queue import PracticeQueue

    from .adaptive_scheduling import build_adaptive_scheduling_plan

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"Error: Ledger file not found: {ledger_path}", file=sys.stderr)
        return 1

    queue = None
    if args.queue:
        queue_path = Path(args.queue)
        if not queue_path.exists():
            print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
            return 1
        queue_data = load_json(queue_path)
        queue = PracticeQueue.model_validate(queue_data)

    try:
        ledger_data = load_json(ledger_path)
        ledger = PedagogicalEvidenceLedger.model_validate(ledger_data)

        student_id = getattr(args, 'student_id', None)

        plan = build_adaptive_scheduling_plan(
            ledger=ledger,
            queue=queue,
            student_id=student_id,
        )

        output = plan.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_mediation_submit(args: argparse.Namespace) -> int:
    """Handle mediation submit command."""
    from sg_spec.schemas.adaptive_scheduling import AdaptiveSchedulingRecommendation
    from sg_spec.schemas.teacher_scheduling_mediation import (
        MediationAction,
        TeacherSchedulingOverride,
    )
    from sg_spec.schemas.practice_queue import PracticeQueuePriority

    from .teacher_scheduling_mediation import create_teacher_scheduling_mediation

    recommendation_path = Path(args.recommendation)
    if not recommendation_path.exists():
        print(f"Error: Recommendation file not found: {recommendation_path}", file=sys.stderr)
        return 1

    try:
        recommendation_data = load_json(recommendation_path)
        recommendation = AdaptiveSchedulingRecommendation.model_validate(recommendation_data)

        action = MediationAction(args.action)
        teacher_id = args.teacher_id
        rationale = getattr(args, 'rationale', None)
        student_id = getattr(args, 'student_id', None)

        override = None
        if action == MediationAction.approve_modified:
            override_priority = getattr(args, 'override_priority', None)
            override_repetition = getattr(args, 'override_repetition', None)
            override_delay = getattr(args, 'override_delay', None)

            if override_priority or override_repetition is not None or override_delay is not None:
                override = TeacherSchedulingOverride(
                    recommended_priority=PracticeQueuePriority(override_priority) if override_priority else None,
                    recommended_repetition_count=override_repetition,
                    recommended_delay_days=override_delay,
                )

        mediation = create_teacher_scheduling_mediation(
            recommendation=recommendation,
            teacher_id=teacher_id,
            action=action,
            student_id=student_id,
            override=override,
            rationale=rationale,
        )

        output = mediation.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_mediation_apply(args: argparse.Namespace) -> int:
    """Handle mediation apply command."""
    from sg_spec.schemas.adaptive_scheduling import AdaptiveSchedulingRecommendation
    from sg_spec.schemas.practice_queue import PracticeQueue
    from sg_spec.schemas.teacher_scheduling_mediation import TeacherSchedulingMediation

    from .teacher_scheduling_mediation import apply_mediation_to_queue

    mediation_path = Path(args.mediation)
    if not mediation_path.exists():
        print(f"Error: Mediation file not found: {mediation_path}", file=sys.stderr)
        return 1

    recommendation_path = Path(args.recommendation)
    if not recommendation_path.exists():
        print(f"Error: Recommendation file not found: {recommendation_path}", file=sys.stderr)
        return 1

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
        return 1

    try:
        mediation_data = load_json(mediation_path)
        mediation = TeacherSchedulingMediation.model_validate(mediation_data)

        recommendation_data = load_json(recommendation_path)
        recommendation = AdaptiveSchedulingRecommendation.model_validate(recommendation_data)

        queue_data = load_json(queue_path)
        queue = PracticeQueue.model_validate(queue_data)

        updated_queue = apply_mediation_to_queue(
            queue=queue,
            mediation=mediation,
            original_recommendation=recommendation,
        )

        output = updated_queue.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_timeline_view(args: argparse.Namespace) -> int:
    """Handle timeline-view command."""
    from sg_spec.schemas.pedagogical_ledger import PedagogicalEvidenceLedger

    from .pedagogical_visualization import build_pedagogical_timeline_view

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"Error: Ledger file not found: {ledger_path}", file=sys.stderr)
        return 1

    try:
        ledger_data = load_json(ledger_path)
        ledger = PedagogicalEvidenceLedger.model_validate(ledger_data)

        student_id = getattr(args, 'student_id', None)

        view = build_pedagogical_timeline_view(
            ledger=ledger,
            student_id=student_id,
        )

        output = view.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_guided_session_view(args: argparse.Namespace) -> int:
    """Handle guided-session-view command."""
    from sg_spec.schemas.adaptive_scheduling import AdaptiveSchedulingPlan
    from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
    from sg_spec.schemas.practice_assignment import AssembledPracticeAssignment
    from sg_spec.schemas.practice_queue import PracticeQueue
    from sg_spec.schemas.runtime_flow import RuntimePracticeSession
    from sg_spec.schemas.session_playback import SessionPlaybackData
    from sg_spec.schemas.teacher_scheduling_mediation import TeacherSchedulingMediation

    from .guided_practice_view import build_guided_practice_session_view

    queue = None
    runtime_session = None
    assignment = None
    playback = None
    adaptive_plan = None
    mediations = []
    timeline = None

    try:
        if args.queue:
            queue_path = Path(args.queue)
            if not queue_path.exists():
                print(f"Error: Queue file not found: {queue_path}", file=sys.stderr)
                return 1
            queue_data = load_json(queue_path)
            queue = PracticeQueue.model_validate(queue_data)

        if args.runtime_session:
            rts_path = Path(args.runtime_session)
            if not rts_path.exists():
                print(f"Error: Runtime session file not found: {rts_path}", file=sys.stderr)
                return 1
            rts_data = load_json(rts_path)
            runtime_session = RuntimePracticeSession.model_validate(rts_data)

        if args.assignment:
            assignment_path = Path(args.assignment)
            if not assignment_path.exists():
                print(f"Error: Assignment file not found: {assignment_path}", file=sys.stderr)
                return 1
            assignment_data = load_json(assignment_path)
            assignment = AssembledPracticeAssignment.model_validate(assignment_data)

        if args.playback:
            playback_path = Path(args.playback)
            if not playback_path.exists():
                print(f"Error: Playback file not found: {playback_path}", file=sys.stderr)
                return 1
            playback_data = load_json(playback_path)
            playback = SessionPlaybackData.model_validate(playback_data)

        if args.adaptive_plan:
            adaptive_path = Path(args.adaptive_plan)
            if not adaptive_path.exists():
                print(f"Error: Adaptive plan file not found: {adaptive_path}", file=sys.stderr)
                return 1
            adaptive_data = load_json(adaptive_path)
            adaptive_plan = AdaptiveSchedulingPlan.model_validate(adaptive_data)

        if args.mediations:
            mediations_path = Path(args.mediations)
            if not mediations_path.exists():
                print(f"Error: Mediations file not found: {mediations_path}", file=sys.stderr)
                return 1
            mediations_data = load_json(mediations_path)
            if isinstance(mediations_data, list):
                mediations = [TeacherSchedulingMediation.model_validate(m) for m in mediations_data]
            else:
                mediations = [TeacherSchedulingMediation.model_validate(mediations_data)]

        if args.timeline:
            timeline_path = Path(args.timeline)
            if not timeline_path.exists():
                print(f"Error: Timeline file not found: {timeline_path}", file=sys.stderr)
                return 1
            timeline_data = load_json(timeline_path)
            timeline = PedagogicalTimelineView.model_validate(timeline_data)

        student_id = getattr(args, 'student_id', None)

        view = build_guided_practice_session_view(
            queue=queue,
            runtime_session=runtime_session,
            assignment=assignment,
            playback=playback,
            adaptive_plan=adaptive_plan,
            mediations=mediations,
            timeline=timeline,
            student_id=student_id,
        )

        output = view.model_dump(mode="json")

        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_narrative_guided_session(args: argparse.Namespace) -> int:
    """Handle narrative guided-session command."""
    from sg_spec.schemas.guided_practice_view import GuidedPracticeSessionView
    from sg_spec.schemas.pedagogical_narrative import NarrativeAudience

    from .pedagogical_narrative import build_guided_session_narrative

    try:
        session_view_path = Path(args.session_view)
        if not session_view_path.exists():
            print(f"Error: Session view file not found: {session_view_path}", file=sys.stderr)
            return 1

        session_view_data = load_json(session_view_path)
        session_view = GuidedPracticeSessionView.model_validate(session_view_data)

        audience = NarrativeAudience(args.audience) if args.audience else NarrativeAudience.mixed

        narrative = build_guided_session_narrative(
            session_view=session_view,
            audience=audience,
        )

        output = narrative.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_narrative_runtime_review(args: argparse.Namespace) -> int:
    """Handle narrative runtime-review command."""
    from sg_spec.schemas.pedagogical_narrative import NarrativeAudience
    from sg_spec.schemas.runtime_review import RuntimeReviewReport

    from .pedagogical_narrative import build_runtime_review_narrative

    try:
        review_path = Path(args.review)
        if not review_path.exists():
            print(f"Error: Review file not found: {review_path}", file=sys.stderr)
            return 1

        review_data = load_json(review_path)
        review = RuntimeReviewReport.model_validate(review_data)

        audience = NarrativeAudience(args.audience) if args.audience else NarrativeAudience.mixed

        narrative = build_runtime_review_narrative(
            review=review,
            audience=audience,
        )

        output = narrative.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_narrative_longitudinal_review(args: argparse.Namespace) -> int:
    """Handle narrative longitudinal-review command."""
    from sg_spec.schemas.longitudinal_review import LongitudinalProgressReview
    from sg_spec.schemas.pedagogical_narrative import NarrativeAudience

    from .pedagogical_narrative import build_longitudinal_review_narrative

    try:
        review_path = Path(args.review)
        if not review_path.exists():
            print(f"Error: Review file not found: {review_path}", file=sys.stderr)
            return 1

        review_data = load_json(review_path)
        review = LongitudinalProgressReview.model_validate(review_data)

        audience = NarrativeAudience(args.audience) if args.audience else NarrativeAudience.teacher

        narrative = build_longitudinal_review_narrative(
            review=review,
            audience=audience,
        )

        output = narrative.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_workspace_session(args: argparse.Namespace) -> int:
    """Handle workspace session command."""
    from sg_spec.schemas.guided_practice_view import GuidedPracticeSessionView
    from sg_spec.schemas.pedagogical_narrative import PedagogicalNarrative
    from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
    from sg_spec.schemas.session_workspace import WorkspaceAudience

    from .session_workspace import build_session_workspace_projection

    try:
        session_view_path = Path(args.session_view)
        if not session_view_path.exists():
            print(f"Error: Session view file not found: {session_view_path}", file=sys.stderr)
            return 1

        session_view_data = load_json(session_view_path)
        guided_session = GuidedPracticeSessionView.model_validate(session_view_data)

        narrative = None
        if args.narrative:
            narrative_path = Path(args.narrative)
            if not narrative_path.exists():
                print(f"Error: Narrative file not found: {narrative_path}", file=sys.stderr)
                return 1
            narrative_data = load_json(narrative_path)
            narrative = PedagogicalNarrative.model_validate(narrative_data)

        timeline = None
        if args.timeline:
            timeline_path = Path(args.timeline)
            if not timeline_path.exists():
                print(f"Error: Timeline file not found: {timeline_path}", file=sys.stderr)
                return 1
            timeline_data = load_json(timeline_path)
            timeline = PedagogicalTimelineView.model_validate(timeline_data)

        audience = WorkspaceAudience(args.audience) if args.audience else WorkspaceAudience.mixed

        projection = build_session_workspace_projection(
            guided_session=guided_session,
            narrative=narrative,
            timeline=timeline,
            audience=audience,
        )

        output = projection.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_workspace_export(args: argparse.Namespace) -> int:
    """Handle workspace export command."""
    from sg_spec.schemas.pedagogical_narrative import PedagogicalNarrative
    from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
    from sg_spec.schemas.session_workspace import SessionWorkspaceProjection
    from sg_spec.schemas.workspace_export import WorkspaceExportRedactionLevel

    from .workspace_export import build_workspace_export_package

    try:
        workspace_path = Path(args.workspace)
        if not workspace_path.exists():
            print(f"Error: Workspace file not found: {workspace_path}", file=sys.stderr)
            return 1

        workspace_data = load_json(workspace_path)
        workspace = SessionWorkspaceProjection.model_validate(workspace_data)

        narrative = None
        if args.narrative:
            narrative_path = Path(args.narrative)
            if not narrative_path.exists():
                print(f"Error: Narrative file not found: {narrative_path}", file=sys.stderr)
                return 1
            narrative_data = load_json(narrative_path)
            narrative = PedagogicalNarrative.model_validate(narrative_data)

        timeline = None
        if args.timeline:
            timeline_path = Path(args.timeline)
            if not timeline_path.exists():
                print(f"Error: Timeline file not found: {timeline_path}", file=sys.stderr)
                return 1
            timeline_data = load_json(timeline_path)
            timeline = PedagogicalTimelineView.model_validate(timeline_data)

        redaction_level = WorkspaceExportRedactionLevel(args.redaction) if args.redaction else WorkspaceExportRedactionLevel.none

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
            redaction_level=redaction_level,
        )

        output = package.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        json_output = json.dumps(output, indent=indent, default=str)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output, encoding="utf-8")
        else:
            print(json_output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_workspace_frontend_state(args: argparse.Namespace) -> int:
    """Handle workspace frontend-state command."""
    from sg_spec.schemas.session_workspace import SessionWorkspaceProjection

    from .frontend_state import build_workspace_frontend_state

    try:
        workspace_path = Path(args.workspace)
        if not workspace_path.exists():
            print(f"Error: Workspace file not found: {workspace_path}", file=sys.stderr)
            return 1

        workspace_data = load_json(workspace_path)
        workspace = SessionWorkspaceProjection.model_validate(workspace_data)

        frontend_state = build_workspace_frontend_state(workspace=workspace)

        output = frontend_state.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        json_output = json.dumps(output, indent=indent, default=str)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output, encoding="utf-8")
        else:
            print(json_output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_frontend_event_apply(args: argparse.Namespace) -> int:
    """Handle frontend-event apply command."""
    from sg_spec.schemas.frontend_interaction import FrontendInteractionEvent
    from sg_spec.schemas.frontend_state import WorkspaceFrontendState

    from .frontend_interaction import apply_frontend_interaction

    try:
        state_path = Path(args.state)
        if not state_path.exists():
            print(f"Error: State file not found: {state_path}", file=sys.stderr)
            return 1

        event_path = Path(args.event)
        if not event_path.exists():
            print(f"Error: Event file not found: {event_path}", file=sys.stderr)
            return 1

        state_data = load_json(state_path)
        state = WorkspaceFrontendState.model_validate(state_data)

        event_data = load_json(event_path)
        event = FrontendInteractionEvent.model_validate(event_data)

        result = apply_frontend_interaction(state=state, event=event)

        output = result.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_frontend_event_replay(args: argparse.Namespace) -> int:
    """Handle frontend-event replay command."""
    from sg_spec.schemas.frontend_interaction import FrontendInteractionEvent
    from sg_spec.schemas.frontend_state import WorkspaceFrontendState

    from .frontend_interaction_store import FrontendInteractionStore

    try:
        state_path = Path(args.state)
        if not state_path.exists():
            print(f"Error: State file not found: {state_path}", file=sys.stderr)
            return 1

        events_path = Path(args.events)
        if not events_path.exists():
            print(f"Error: Events file not found: {events_path}", file=sys.stderr)
            return 1

        state_data = load_json(state_path)
        state = WorkspaceFrontendState.model_validate(state_data)

        events: list[FrontendInteractionEvent] = []
        with events_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event_data = json.loads(line)
                events.append(FrontendInteractionEvent.model_validate(event_data))

        store = FrontendInteractionStore(events_path)
        result = store.replay_events(state, events)

        output = result.model_dump(mode="json")
        indent = 2 if getattr(args, 'pretty', False) else None
        print(json.dumps(output, indent=indent, default=str))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_governance_check(args: argparse.Namespace) -> int:
    """Handle governance check command."""
    from .governance_checks import run_all_governance_checks

    try:
        repo_root = Path(args.repo_root).resolve()

        if not repo_root.exists():
            print(f"Error: Repository root not found: {repo_root}", file=sys.stderr)
            return 1

        # Determine which checks to run based on repo
        feedback_route_path = None
        check_ai_docs = False

        if (repo_root / "sg_agentd").exists():
            feedback_route_path = repo_root / "sg_agentd" / "routes" / "feedback.py"

        if (repo_root / "sg_ai").exists() or (repo_root / "packages" / "sg-engine").exists():
            check_ai_docs = True

        results = run_all_governance_checks(
            repo_root=repo_root,
            check_shared_imports=True,
            check_pr_snapshots=True,
            check_feedback_boundary=feedback_route_path is not None,
            check_ai_docs=check_ai_docs,
            feedback_route_path=feedback_route_path,
        )

        # Report results
        total_violations = 0
        for check_name, violations in results.items():
            if violations:
                print(f"\n{check_name}:")
                for v in violations:
                    print(f"  - {v}")
                total_violations += len(violations)

        if total_violations == 0:
            print("OK: All governance checks passed.")
            return 0
        else:
            print(f"\nTotal violations: {total_violations}")
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="sg-coach",
        description="Smart Guitar Coach CLI",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a practice session",
    )
    eval_parser.add_argument(
        "input",
        type=str,
        help="Path to session JSON or MIDI input JSON file",
    )
    eval_parser.add_argument(
        "--midi",
        action="store_true",
        help="Input is MIDI session input (MidiSessionInput)",
    )
    eval_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Include detailed output",
    )
    eval_parser.add_argument(
        "--persist",
        type=str,
        default=None,
        help="Path to JSONL file for practice history persistence",
    )
    eval_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="User ID for practice history entry",
    )

    # review command
    review_parser = subparsers.add_parser(
        "review",
        help="Show practice review (timeline + progress)",
    )
    review_parser.add_argument(
        "--history",
        required=True,
        type=str,
        help="Path to history JSONL file",
    )
    review_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="Filter by user ID",
    )
    review_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit timeline entries",
    )
    review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # goals command
    goals_parser = subparsers.add_parser(
        "goals",
        help="Show practice goals based on history",
    )
    goals_parser.add_argument(
        "--history",
        required=True,
        type=str,
        help="Path to history JSONL file",
    )
    goals_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="Filter by user ID",
    )
    goals_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # timeline command
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Show practice timeline",
    )
    timeline_parser.add_argument(
        "--history",
        required=True,
        type=str,
        help="Path to history JSONL file",
    )
    timeline_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="Filter by user ID",
    )
    timeline_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit timeline entries",
    )
    timeline_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Show practice dashboard data",
    )
    dashboard_parser.add_argument(
        "--history",
        required=True,
        type=str,
        help="Path to history JSONL file",
    )
    dashboard_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="Filter by user ID",
    )
    dashboard_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # playback command
    playback_parser = subparsers.add_parser(
        "playback",
        help="Build session playback data",
    )
    playback_parser.add_argument(
        "--session",
        required=True,
        type=str,
        help="Path to session JSON file",
    )
    playback_parser.add_argument(
        "--evaluation",
        required=True,
        type=str,
        help="Path to evaluation JSON file",
    )
    playback_parser.add_argument(
        "--assignments",
        type=str,
        default=None,
        help="Path to assignments JSON file (optional)",
    )
    playback_parser.add_argument(
        "--user-id",
        type=str,
        dest="user_id",
        default=None,
        help="User ID to include in playback data",
    )
    playback_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    playback_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose error output",
    )

    # teacher-review command
    teacher_review_parser = subparsers.add_parser(
        "teacher-review",
        help="Build teacher review data",
    )
    teacher_review_parser.add_argument(
        "--history",
        required=True,
        type=str,
        help="Path to history JSONL file",
    )
    teacher_review_parser.add_argument(
        "--session-id",
        type=str,
        dest="session_id",
        default=None,
        help="Session ID to include session review and playback",
    )
    teacher_review_parser.add_argument(
        "--student-id",
        type=str,
        dest="student_id",
        default=None,
        help="Student ID for filtering and metadata",
    )
    teacher_review_parser.add_argument(
        "--teacher-id",
        type=str,
        dest="teacher_id",
        default=None,
        help="Teacher ID for metadata",
    )
    teacher_review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio command group
    studio_parser = subparsers.add_parser(
        "studio",
        help="Studio roster management",
    )
    studio_subparsers = studio_parser.add_subparsers(
        dest="studio_command",
        help="Studio commands",
    )

    # studio create
    studio_create_parser = studio_subparsers.add_parser(
        "create",
        help="Create a new studio",
    )
    studio_create_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_create_parser.add_argument(
        "--name",
        required=True,
        type=str,
        help="Studio name",
    )
    studio_create_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Optional studio ID (auto-generated if not provided)",
    )
    studio_create_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio add-student
    studio_add_student_parser = studio_subparsers.add_parser(
        "add-student",
        help="Add a student to a studio",
    )
    studio_add_student_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_add_student_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Studio ID (optional if only one studio exists)",
    )
    studio_add_student_parser.add_argument(
        "--name",
        required=True,
        type=str,
        help="Student display name",
    )
    studio_add_student_parser.add_argument(
        "--student-id",
        type=str,
        dest="student_id",
        default=None,
        help="Optional student ID (auto-generated if not provided)",
    )
    studio_add_student_parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Optional notes about the student",
    )
    studio_add_student_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio add-teacher
    studio_add_teacher_parser = studio_subparsers.add_parser(
        "add-teacher",
        help="Add a teacher to a studio",
    )
    studio_add_teacher_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_add_teacher_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Studio ID (optional if only one studio exists)",
    )
    studio_add_teacher_parser.add_argument(
        "--name",
        required=True,
        type=str,
        help="Teacher display name",
    )
    studio_add_teacher_parser.add_argument(
        "--teacher-id",
        type=str,
        dest="teacher_id",
        default=None,
        help="Optional teacher ID (auto-generated if not provided)",
    )
    studio_add_teacher_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio list-students
    studio_list_students_parser = studio_subparsers.add_parser(
        "list-students",
        help="List students in a studio",
    )
    studio_list_students_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_list_students_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Studio ID (optional if only one studio exists)",
    )
    studio_list_students_parser.add_argument(
        "--all",
        action="store_true",
        help="Include inactive students",
    )
    studio_list_students_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio list-teachers
    studio_list_teachers_parser = studio_subparsers.add_parser(
        "list-teachers",
        help="List teachers in a studio",
    )
    studio_list_teachers_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_list_teachers_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Studio ID (optional if only one studio exists)",
    )
    studio_list_teachers_parser.add_argument(
        "--all",
        action="store_true",
        help="Include inactive teachers",
    )
    studio_list_teachers_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # studio overview
    studio_overview_parser = studio_subparsers.add_parser(
        "overview",
        help="Show studio overview with counts",
    )
    studio_overview_parser.add_argument(
        "--roster",
        required=True,
        type=str,
        help="Path to roster JSONL file",
    )
    studio_overview_parser.add_argument(
        "--studio-id",
        type=str,
        dest="studio_id",
        default=None,
        help="Studio ID (optional if only one studio exists)",
    )
    studio_overview_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # queue command group
    queue_parser = subparsers.add_parser(
        "queue",
        help="Practice queue management",
    )
    queue_subparsers = queue_parser.add_subparsers(
        dest="queue_command",
        help="Queue commands",
    )

    # queue build
    queue_build_parser = queue_subparsers.add_parser(
        "build",
        help="Build a practice queue from assignments",
    )
    queue_build_parser.add_argument(
        "--assignments",
        required=True,
        type=str,
        help="Path to assignments JSON file",
    )
    queue_build_parser.add_argument(
        "--student-id",
        type=str,
        dest="student_id",
        default=None,
        help="Student ID for the queue",
    )
    queue_build_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # queue next
    queue_next_parser = queue_subparsers.add_parser(
        "next",
        help="Get next eligible assignment from queue",
    )
    queue_next_parser.add_argument(
        "--queue",
        required=True,
        type=str,
        help="Path to queue JSON file",
    )
    queue_next_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # queue complete
    queue_complete_parser = queue_subparsers.add_parser(
        "complete",
        help="Mark an assignment as completed",
    )
    queue_complete_parser.add_argument(
        "--store",
        required=True,
        type=str,
        help="Path to queue store JSONL file",
    )
    queue_complete_parser.add_argument(
        "--assignment-id",
        required=True,
        type=str,
        dest="assignment_id",
        help="Assignment ID to complete",
    )
    queue_complete_parser.add_argument(
        "--queue-id",
        type=str,
        dest="queue_id",
        default=None,
        help="Queue ID (optional if only one queue in store)",
    )
    queue_complete_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # queue defer
    queue_defer_parser = queue_subparsers.add_parser(
        "defer",
        help="Defer an assignment",
    )
    queue_defer_parser.add_argument(
        "--store",
        required=True,
        type=str,
        help="Path to queue store JSONL file",
    )
    queue_defer_parser.add_argument(
        "--assignment-id",
        required=True,
        type=str,
        dest="assignment_id",
        help="Assignment ID to defer",
    )
    queue_defer_parser.add_argument(
        "--queue-id",
        type=str,
        dest="queue_id",
        default=None,
        help="Queue ID (optional if only one queue in store)",
    )
    queue_defer_parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Hours to defer (optional)",
    )
    queue_defer_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # queue abandon
    queue_abandon_parser = queue_subparsers.add_parser(
        "abandon",
        help="Abandon an assignment",
    )
    queue_abandon_parser.add_argument(
        "--store",
        required=True,
        type=str,
        help="Path to queue store JSONL file",
    )
    queue_abandon_parser.add_argument(
        "--assignment-id",
        required=True,
        type=str,
        dest="assignment_id",
        help="Assignment ID to abandon",
    )
    queue_abandon_parser.add_argument(
        "--queue-id",
        type=str,
        dest="queue_id",
        default=None,
        help="Queue ID (optional if only one queue in store)",
    )
    queue_abandon_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime command group
    runtime_parser = subparsers.add_parser(
        "runtime",
        help="Runtime practice session management",
    )
    runtime_subparsers = runtime_parser.add_subparsers(
        dest="runtime_command",
        help="Runtime commands",
    )

    # runtime start-next
    runtime_start_next_parser = runtime_subparsers.add_parser(
        "start-next",
        help="Start the next available assignment from queue",
    )
    runtime_start_next_parser.add_argument(
        "--queue",
        required=True,
        type=str,
        help="Path to queue JSON file",
    )
    runtime_start_next_parser.add_argument(
        "--assignments",
        required=True,
        type=str,
        help="Path to assignments JSON file",
    )
    runtime_start_next_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime complete
    runtime_complete_parser = runtime_subparsers.add_parser(
        "complete",
        help="Complete a runtime session with an outcome",
    )
    runtime_complete_parser.add_argument(
        "--runtime-session",
        required=True,
        type=str,
        dest="runtime_session",
        help="Path to runtime session JSON file",
    )
    runtime_complete_parser.add_argument(
        "--outcome",
        required=True,
        type=str,
        help="Practice outcome (completed, improved, worsened, repeated, abandoned)",
    )
    runtime_complete_parser.add_argument(
        "--queue",
        required=True,
        type=str,
        help="Path to queue JSON file",
    )
    runtime_complete_parser.add_argument(
        "--progress",
        required=True,
        type=str,
        help="Path to progress state JSON file",
    )
    runtime_complete_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime abandon
    runtime_abandon_parser = runtime_subparsers.add_parser(
        "abandon",
        help="Abandon a runtime session",
    )
    runtime_abandon_parser.add_argument(
        "--runtime-session",
        required=True,
        type=str,
        dest="runtime_session",
        help="Path to runtime session JSON file",
    )
    runtime_abandon_parser.add_argument(
        "--queue",
        required=True,
        type=str,
        help="Path to queue JSON file",
    )
    runtime_abandon_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime attach-evidence
    runtime_attach_evidence_parser = runtime_subparsers.add_parser(
        "attach-evidence",
        help="Attach SessionRecord and CoachEvaluation evidence to a runtime session",
    )
    runtime_attach_evidence_parser.add_argument(
        "--runtime-session",
        required=True,
        type=str,
        dest="runtime_session",
        help="Path to runtime session JSON file",
    )
    runtime_attach_evidence_parser.add_argument(
        "--session",
        required=True,
        type=str,
        help="Path to SessionRecord JSON file",
    )
    runtime_attach_evidence_parser.add_argument(
        "--evaluation",
        required=True,
        type=str,
        help="Path to CoachEvaluation JSON file",
    )
    runtime_attach_evidence_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime review
    runtime_review_parser = runtime_subparsers.add_parser(
        "review",
        help="Generate a review report for a runtime session",
    )
    runtime_review_parser.add_argument(
        "--runtime-session",
        required=True,
        type=str,
        dest="runtime_session",
        help="Path to runtime session JSON file",
    )
    runtime_review_parser.add_argument(
        "--runtime-result",
        required=False,
        type=str,
        dest="runtime_result",
        help="Path to runtime result JSON file (optional)",
    )
    runtime_review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # runtime longitudinal-review
    runtime_longitudinal_review_parser = runtime_subparsers.add_parser(
        "longitudinal-review",
        help="Generate a longitudinal progress review from multiple runtime review reports",
    )
    runtime_longitudinal_review_parser.add_argument(
        "--reports",
        required=True,
        type=str,
        help="Path to NDJSON file containing RuntimeReviewReport records",
    )
    runtime_longitudinal_review_parser.add_argument(
        "--student-id",
        required=False,
        type=str,
        dest="student_id",
        help="Student ID for the review (optional)",
    )
    runtime_longitudinal_review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # ledger command group
    ledger_parser = subparsers.add_parser(
        "ledger",
        help="Pedagogical evidence ledger management",
    )
    ledger_subparsers = ledger_parser.add_subparsers(
        dest="ledger_command",
        help="Ledger commands",
    )

    # ledger build
    ledger_build_parser = ledger_subparsers.add_parser(
        "build",
        help="Build pedagogical evidence ledger from sources",
    )
    ledger_build_parser.add_argument(
        "--runtime-reviews",
        required=False,
        type=str,
        dest="runtime_reviews",
        help="Path to runtime reviews file (JSON array or NDJSON)",
    )
    ledger_build_parser.add_argument(
        "--queue-events",
        required=False,
        type=str,
        dest="queue_events",
        help="Path to queue events file (JSON array or NDJSON)",
    )
    ledger_build_parser.add_argument(
        "--teacher-reviews",
        required=False,
        type=str,
        dest="teacher_reviews",
        help="Path to teacher reviews file (JSON array or NDJSON)",
    )
    ledger_build_parser.add_argument(
        "--student-id",
        required=False,
        type=str,
        dest="student_id",
        help="Student ID for the ledger",
    )
    ledger_build_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # ledger summary
    ledger_summary_parser = ledger_subparsers.add_parser(
        "summary",
        help="Generate summary from pedagogical evidence ledger",
    )
    ledger_summary_parser.add_argument(
        "--ledger",
        required=True,
        type=str,
        help="Path to ledger JSON file",
    )
    ledger_summary_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # adaptive-scheduling command
    adaptive_scheduling_parser = subparsers.add_parser(
        "adaptive-scheduling",
        help="Generate adaptive scheduling plan from ledger",
    )
    adaptive_scheduling_parser.add_argument(
        "--ledger",
        required=True,
        type=str,
        help="Path to ledger JSON file",
    )
    adaptive_scheduling_parser.add_argument(
        "--queue",
        required=False,
        type=str,
        help="Path to queue JSON file (optional)",
    )
    adaptive_scheduling_parser.add_argument(
        "--student-id",
        required=False,
        type=str,
        dest="student_id",
        help="Student ID for the plan (optional)",
    )
    adaptive_scheduling_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # mediation command group
    mediation_parser = subparsers.add_parser(
        "mediation",
        help="Teacher scheduling mediation management",
    )
    mediation_subparsers = mediation_parser.add_subparsers(
        dest="mediation_command",
        help="Mediation commands",
    )

    # mediation submit
    mediation_submit_parser = mediation_subparsers.add_parser(
        "submit",
        help="Submit a teacher mediation for a recommendation",
    )
    mediation_submit_parser.add_argument(
        "--recommendation",
        required=True,
        type=str,
        help="Path to recommendation JSON file",
    )
    mediation_submit_parser.add_argument(
        "--teacher-id",
        required=True,
        type=str,
        dest="teacher_id",
        help="Teacher ID submitting the mediation",
    )
    mediation_submit_parser.add_argument(
        "--action",
        required=True,
        type=str,
        choices=["approve", "approve_modified", "reject", "defer"],
        help="Mediation action",
    )
    mediation_submit_parser.add_argument(
        "--rationale",
        type=str,
        default=None,
        help="Rationale for the decision (required for approve_modified, reject, defer)",
    )
    mediation_submit_parser.add_argument(
        "--student-id",
        type=str,
        dest="student_id",
        default=None,
        help="Student ID (optional)",
    )
    mediation_submit_parser.add_argument(
        "--override-priority",
        type=str,
        dest="override_priority",
        default=None,
        help="Override priority (critical, high, normal, low) for approve_modified",
    )
    mediation_submit_parser.add_argument(
        "--override-repetition",
        type=int,
        dest="override_repetition",
        default=None,
        help="Override repetition count for approve_modified",
    )
    mediation_submit_parser.add_argument(
        "--override-delay",
        type=int,
        dest="override_delay",
        default=None,
        help="Override delay days for approve_modified",
    )
    mediation_submit_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # mediation apply
    mediation_apply_parser = mediation_subparsers.add_parser(
        "apply",
        help="Apply a mediation to a practice queue",
    )
    mediation_apply_parser.add_argument(
        "--mediation",
        required=True,
        type=str,
        help="Path to mediation JSON file",
    )
    mediation_apply_parser.add_argument(
        "--recommendation",
        required=True,
        type=str,
        help="Path to original recommendation JSON file",
    )
    mediation_apply_parser.add_argument(
        "--queue",
        required=True,
        type=str,
        help="Path to queue JSON file",
    )
    mediation_apply_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # timeline-view command
    timeline_view_parser = subparsers.add_parser(
        "timeline-view",
        help="Build pedagogical timeline view from ledger",
    )
    timeline_view_parser.add_argument(
        "--ledger",
        required=True,
        type=str,
        help="Path to ledger JSON file",
    )
    timeline_view_parser.add_argument(
        "--student-id",
        required=False,
        type=str,
        dest="student_id",
        help="Student ID for the view (optional)",
    )
    timeline_view_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # guided-session-view command
    guided_session_parser = subparsers.add_parser(
        "guided-session-view",
        help="Build guided practice session UX view",
    )
    guided_session_parser.add_argument(
        "--queue",
        required=False,
        type=str,
        help="Path to practice queue JSON file",
    )
    guided_session_parser.add_argument(
        "--runtime-session",
        required=False,
        type=str,
        dest="runtime_session",
        help="Path to runtime session JSON file",
    )
    guided_session_parser.add_argument(
        "--assignment",
        required=False,
        type=str,
        help="Path to assignment JSON file",
    )
    guided_session_parser.add_argument(
        "--playback",
        required=False,
        type=str,
        help="Path to playback data JSON file",
    )
    guided_session_parser.add_argument(
        "--adaptive-plan",
        required=False,
        type=str,
        dest="adaptive_plan",
        help="Path to adaptive scheduling plan JSON file",
    )
    guided_session_parser.add_argument(
        "--mediations",
        required=False,
        type=str,
        help="Path to mediations JSON file (array or single)",
    )
    guided_session_parser.add_argument(
        "--timeline",
        required=False,
        type=str,
        help="Path to pedagogical timeline view JSON file",
    )
    guided_session_parser.add_argument(
        "--student-id",
        required=False,
        type=str,
        dest="student_id",
        help="Student ID for the view (optional)",
    )
    guided_session_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # narrative command with subcommands
    narrative_parser = subparsers.add_parser(
        "narrative",
        help="Build pedagogical narratives",
    )
    narrative_subparsers = narrative_parser.add_subparsers(
        dest="narrative_command",
        help="Narrative commands",
    )

    # narrative guided-session
    narrative_guided_session_parser = narrative_subparsers.add_parser(
        "guided-session",
        help="Build narrative from guided practice session view",
    )
    narrative_guided_session_parser.add_argument(
        "--session-view",
        required=True,
        type=str,
        dest="session_view",
        help="Path to guided practice session view JSON file",
    )
    narrative_guided_session_parser.add_argument(
        "--audience",
        required=False,
        type=str,
        choices=["student", "teacher", "mixed"],
        default="mixed",
        help="Target audience for narrative wording",
    )
    narrative_guided_session_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # narrative runtime-review
    narrative_runtime_review_parser = narrative_subparsers.add_parser(
        "runtime-review",
        help="Build narrative from runtime review report",
    )
    narrative_runtime_review_parser.add_argument(
        "--review",
        required=True,
        type=str,
        help="Path to runtime review report JSON file",
    )
    narrative_runtime_review_parser.add_argument(
        "--audience",
        required=False,
        type=str,
        choices=["student", "teacher", "mixed"],
        default="mixed",
        help="Target audience for narrative wording",
    )
    narrative_runtime_review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # narrative longitudinal-review
    narrative_longitudinal_review_parser = narrative_subparsers.add_parser(
        "longitudinal-review",
        help="Build narrative from longitudinal progress review",
    )
    narrative_longitudinal_review_parser.add_argument(
        "--review",
        required=True,
        type=str,
        help="Path to longitudinal progress review JSON file",
    )
    narrative_longitudinal_review_parser.add_argument(
        "--audience",
        required=False,
        type=str,
        choices=["student", "teacher", "mixed"],
        default="teacher",
        help="Target audience for narrative wording",
    )
    narrative_longitudinal_review_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # workspace command with subcommands
    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Build session workspace projections",
    )
    workspace_subparsers = workspace_parser.add_subparsers(
        dest="workspace_command",
        help="Workspace commands",
    )

    # workspace session
    workspace_session_parser = workspace_subparsers.add_parser(
        "session",
        help="Build session workspace projection from guided session view",
    )
    workspace_session_parser.add_argument(
        "--session-view",
        required=True,
        type=str,
        dest="session_view",
        help="Path to guided practice session view JSON file",
    )
    workspace_session_parser.add_argument(
        "--narrative",
        required=False,
        type=str,
        help="Path to pedagogical narrative JSON file (optional)",
    )
    workspace_session_parser.add_argument(
        "--timeline",
        required=False,
        type=str,
        help="Path to pedagogical timeline view JSON file (optional)",
    )
    workspace_session_parser.add_argument(
        "--audience",
        required=False,
        type=str,
        choices=["student", "teacher", "mixed"],
        default="mixed",
        help="Target audience for workspace composition",
    )
    workspace_session_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # workspace export
    workspace_export_parser = workspace_subparsers.add_parser(
        "export",
        help="Export workspace as portable JSON package",
    )
    workspace_export_parser.add_argument(
        "--workspace",
        required=True,
        type=str,
        help="Path to session workspace projection JSON file",
    )
    workspace_export_parser.add_argument(
        "--narrative",
        required=False,
        type=str,
        help="Path to pedagogical narrative JSON file (optional)",
    )
    workspace_export_parser.add_argument(
        "--timeline",
        required=False,
        type=str,
        help="Path to pedagogical timeline view JSON file (optional)",
    )
    workspace_export_parser.add_argument(
        "--redaction",
        required=False,
        type=str,
        choices=["none", "student_safe", "anonymized"],
        default="none",
        help="Redaction level for export",
    )
    workspace_export_parser.add_argument(
        "--output",
        required=False,
        type=str,
        help="Output file path (if omitted, prints to stdout)",
    )
    workspace_export_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # workspace frontend-state
    workspace_frontend_state_parser = workspace_subparsers.add_parser(
        "frontend-state",
        help="Build frontend state projection from workspace",
    )
    workspace_frontend_state_parser.add_argument(
        "--workspace",
        required=True,
        type=str,
        help="Path to session workspace projection JSON file",
    )
    workspace_frontend_state_parser.add_argument(
        "--output",
        required=False,
        type=str,
        help="Output file path (if omitted, prints to stdout)",
    )
    workspace_frontend_state_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # frontend-event command with subcommands
    frontend_event_parser = subparsers.add_parser(
        "frontend-event",
        help="Frontend interaction event commands",
    )
    frontend_event_subparsers = frontend_event_parser.add_subparsers(
        dest="frontend_event_command",
        help="Frontend event commands",
    )

    # frontend-event apply
    frontend_event_apply_parser = frontend_event_subparsers.add_parser(
        "apply",
        help="Apply an interaction event to frontend state",
    )
    frontend_event_apply_parser.add_argument(
        "--state",
        required=True,
        type=str,
        help="Path to frontend state JSON file",
    )
    frontend_event_apply_parser.add_argument(
        "--event",
        required=True,
        type=str,
        help="Path to interaction event JSON file",
    )
    frontend_event_apply_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # frontend-event replay
    frontend_event_replay_parser = frontend_event_subparsers.add_parser(
        "replay",
        help="Replay interaction events to rebuild state",
    )
    frontend_event_replay_parser.add_argument(
        "--state",
        required=True,
        type=str,
        help="Path to initial frontend state JSON file",
    )
    frontend_event_replay_parser.add_argument(
        "--events",
        required=True,
        type=str,
        help="Path to events JSONL file",
    )
    frontend_event_replay_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # governance command with subcommands
    governance_parser = subparsers.add_parser(
        "governance",
        help="Governance check commands",
    )
    governance_subparsers = governance_parser.add_subparsers(
        dest="governance_command",
        help="Governance commands",
    )

    # governance check
    governance_check_parser = governance_subparsers.add_parser(
        "check",
        help="Run governance checks on a repository",
    )
    governance_check_parser.add_argument(
        "--repo-root",
        required=True,
        type=str,
        help="Path to repository root directory",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if args.command == "evaluate":
        return cmd_evaluate(args)
    elif args.command == "review":
        return cmd_review(args)
    elif args.command == "goals":
        return cmd_goals(args)
    elif args.command == "timeline":
        return cmd_timeline(args)
    elif args.command == "dashboard":
        return cmd_dashboard(args)
    elif args.command == "playback":
        return cmd_playback(args)
    elif args.command == "teacher-review":
        return cmd_teacher_review(args)
    elif args.command == "studio":
        if args.studio_command == "create":
            return cmd_studio_create(args)
        elif args.studio_command == "add-student":
            return cmd_studio_add_student(args)
        elif args.studio_command == "add-teacher":
            return cmd_studio_add_teacher(args)
        elif args.studio_command == "list-students":
            return cmd_studio_list_students(args)
        elif args.studio_command == "list-teachers":
            return cmd_studio_list_teachers(args)
        elif args.studio_command == "overview":
            return cmd_studio_overview(args)
        else:
            print("Error: Unknown studio command", file=sys.stderr)
            return 1
    elif args.command == "queue":
        if args.queue_command == "build":
            return cmd_queue_build(args)
        elif args.queue_command == "next":
            return cmd_queue_next(args)
        elif args.queue_command == "complete":
            return cmd_queue_complete(args)
        elif args.queue_command == "defer":
            return cmd_queue_defer(args)
        elif args.queue_command == "abandon":
            return cmd_queue_abandon(args)
        else:
            print("Error: Unknown queue command", file=sys.stderr)
            return 1
    elif args.command == "runtime":
        if args.runtime_command == "start-next":
            return cmd_runtime_start_next(args)
        elif args.runtime_command == "complete":
            return cmd_runtime_complete(args)
        elif args.runtime_command == "abandon":
            return cmd_runtime_abandon(args)
        elif args.runtime_command == "attach-evidence":
            return cmd_runtime_attach_evidence(args)
        elif args.runtime_command == "review":
            return cmd_runtime_review(args)
        elif args.runtime_command == "longitudinal-review":
            return cmd_runtime_longitudinal_review(args)
        else:
            print("Error: Unknown runtime command", file=sys.stderr)
            return 1
    elif args.command == "ledger":
        if args.ledger_command == "build":
            return cmd_ledger_build(args)
        elif args.ledger_command == "summary":
            return cmd_ledger_summary(args)
        else:
            print("Error: Unknown ledger command", file=sys.stderr)
            return 1
    elif args.command == "adaptive-scheduling":
        return cmd_adaptive_scheduling(args)
    elif args.command == "mediation":
        if args.mediation_command == "submit":
            return cmd_mediation_submit(args)
        elif args.mediation_command == "apply":
            return cmd_mediation_apply(args)
        else:
            print("Error: Unknown mediation command", file=sys.stderr)
            return 1
    elif args.command == "timeline-view":
        return cmd_timeline_view(args)
    elif args.command == "guided-session-view":
        return cmd_guided_session_view(args)
    elif args.command == "narrative":
        if args.narrative_command == "guided-session":
            return cmd_narrative_guided_session(args)
        elif args.narrative_command == "runtime-review":
            return cmd_narrative_runtime_review(args)
        elif args.narrative_command == "longitudinal-review":
            return cmd_narrative_longitudinal_review(args)
        else:
            print("Error: Unknown narrative command", file=sys.stderr)
            return 1
    elif args.command == "workspace":
        if args.workspace_command == "session":
            return cmd_workspace_session(args)
        elif args.workspace_command == "export":
            return cmd_workspace_export(args)
        elif args.workspace_command == "frontend-state":
            return cmd_workspace_frontend_state(args)
        else:
            print("Error: Unknown workspace command", file=sys.stderr)
            return 1
    elif args.command == "frontend-event":
        if args.frontend_event_command == "apply":
            return cmd_frontend_event_apply(args)
        elif args.frontend_event_command == "replay":
            return cmd_frontend_event_replay(args)
        else:
            print("Error: Unknown frontend-event command", file=sys.stderr)
            return 1
    elif args.command == "governance":
        if args.governance_command == "check":
            return cmd_governance_check(args)
        else:
            print("Error: Unknown governance command", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
