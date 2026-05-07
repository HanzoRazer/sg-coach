"""
CLI for sg-coach.

Sprint 11: Minimal CLI for coaching evaluation.
Sprint 15: Extended with review, goals, timeline commands.

Usage:
    sg-coach evaluate <session.json>
    sg-coach evaluate --midi <midi_input.json>
    sg-coach evaluate --midi <midi_input.json> --persist <history.jsonl>
    sg-coach review --history <history.jsonl>
    sg-coach goals --history <history.jsonl>
    sg-coach timeline --history <history.jsonl>
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
