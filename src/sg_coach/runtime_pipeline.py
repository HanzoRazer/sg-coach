"""
Runtime Pipeline — Canonical coaching pipeline orchestration.

Sprint 15: MVP baseline hardening.

This module provides the single entrypoint for running the full coaching
pipeline from MIDI input to coaching results.

Pipeline stages:
1. MIDI input → SessionRecord
2. SessionRecord → CoachEvaluation
3. CoachEvaluation → ActionRecommendations
4. ActionRecommendations → DrillResolution → AssembledAssignments
5. (Optional) Persistence → Goals → CurriculumAlignment
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from sg_spec.schemas.action_mapping import ActionRecommendationSet
from sg_spec.schemas.midi_session import MidiSessionInput
from sg_spec.schemas.practice_assignment import AssembledPracticeAssignmentSet
from sg_spec.schemas.runtime_pipeline import RuntimeCoachingResult

from .action_recommender import recommend_actions
from .coach_policy import evaluate_session
from .curriculum_alignment import build_goal_driven_assignments
from .drill_resolver import resolve_drills_for_recommendations
from .goal_tracking import (
    build_weakness_progressions,
    generate_practice_goals,
)
from .practice_assignment_assembler import assemble_practice_assignments
from .practice_history import PracticeHistoryStore
from .session_builder import build_session_from_midi


RUNTIME_VERSION = "1.0.0"


def run_coaching_pipeline(
    midi_input: MidiSessionInput,
    *,
    history_store: Optional[PracticeHistoryStore] = None,
    history_path: Optional[Union[str, Path]] = None,
    persist: bool = False,
    user_id: Optional[str] = None,
) -> RuntimeCoachingResult:
    """
    Run the full coaching pipeline from MIDI input to results.

    Parameters
    ----------
    midi_input:
        The MIDI session input containing events and metadata.
    history_store:
        Optional existing practice history store.
    history_path:
        Optional path to create/use a history store.
    persist:
        Whether to persist the result to history.
    user_id:
        Optional user ID for personalization and history.

    Returns
    -------
    RuntimeCoachingResult with all pipeline outputs.

    Raises
    ------
    ValueError:
        If persist=True but neither history_store nor history_path provided.

    Notes
    -----
    Pipeline stages:
    1. MIDI → SessionRecord (build_session_from_midi)
    2. SessionRecord → CoachEvaluation (evaluate_session)
    3. CoachEvaluation → ActionRecommendations (recommend_actions)
    4. ActionRecommendations → DrillResolution (resolve_drills_for_recommendations)
    5. DrillResolution → AssembledAssignments (assemble_practice_assignments)
    6. (If history) → Goals → CurriculumAlignment
    7. (If persist) → Persistence
    """
    if persist and history_store is None and history_path is None:
        raise ValueError(
            "persist=True requires either history_store or history_path"
        )

    store = history_store
    if store is None and history_path is not None:
        store = PracticeHistoryStore(Path(history_path))

    session = build_session_from_midi(midi_input)

    evaluation = evaluate_session(session)

    recommendations: List[ActionRecommendationSet] = []
    for finding in evaluation.findings:
        rec_set = recommend_actions(finding)
        recommendations.append(rec_set)

    drill_results = []
    for rec_set in recommendations:
        results = resolve_drills_for_recommendations(
            diagnosis_code=rec_set.finding_code,
            recommendations=rec_set,
        )
        drill_results.extend(results)

    assignments = assemble_practice_assignments(
        findings=evaluation.findings,
        recommendation_sets=recommendations,
        drill_results=drill_results,
    )

    goals = []
    goal_driven_assignments = None

    if store is not None:
        progressions = build_weakness_progressions(
            history_store=store,
            user_id=user_id,
        )
        if progressions:
            goals = generate_practice_goals(progressions=progressions)

            if goals:
                goal_driven_assignments = build_goal_driven_assignments(
                    goals=goals,
                )

    persisted = False
    if persist and store is not None:
        store.append_session(
            session=session,
            evaluation=evaluation,
            assignments=assignments,
            user_id=user_id,
        )
        persisted = True

    return RuntimeCoachingResult(
        session=session,
        evaluation=evaluation,
        recommendations=recommendations,
        assignments=assignments,
        goals=goals,
        goal_driven_assignments=goal_driven_assignments,
        persisted=persisted,
        runtime_version=RUNTIME_VERSION,
    )


def normalize_runtime_output(result: RuntimeCoachingResult) -> dict:
    """
    Normalize a runtime result for golden fixture comparison.

    Removes:
    - Timestamps
    - Generated UUIDs
    - Unstable ordering

    Preserves:
    - Coaching semantics
    - Finding types/codes
    - Assignment content

    Parameters
    ----------
    result:
        The runtime coaching result to normalize.

    Returns
    -------
    Normalized dict suitable for comparison.
    """
    data = result.model_dump(mode="json")

    def strip_volatile(obj):
        if isinstance(obj, dict):
            keys_to_remove = []
            for key in obj:
                if key in (
                    "created_at",
                    "updated_at",
                    "timestamp",
                    "first_seen",
                    "last_seen",
                ):
                    keys_to_remove.append(key)
                elif key == "session_id":
                    val = obj[key]
                    val_str = str(val)
                    if len(val_str) == 36 and "-" in val_str:
                        obj[key] = "<uuid>"
                elif key == "id" and isinstance(obj[key], str):
                    if obj[key].startswith("pa_"):
                        obj[key] = "<generated_id>"

            for key in keys_to_remove:
                del obj[key]

            for key in obj:
                strip_volatile(obj[key])

        elif isinstance(obj, list):
            for item in obj:
                strip_volatile(item)

    strip_volatile(data)

    if "recommendations" in data and data["recommendations"]:
        for rec_set in data["recommendations"]:
            if "recommendations" in rec_set:
                rec_set["recommendations"].sort(
                    key=lambda r: (
                        r.get("diagnosis_code", ""),
                        r.get("action_type", ""),
                    )
                )

    if "assignments" in data and "assignments" in data["assignments"]:
        data["assignments"]["assignments"].sort(
            key=lambda a: (
                a.get("diagnosis_code", ""),
                a.get("title", ""),
            )
        )

    return data


def run_fixture_pipeline(fixture_path: Union[str, Path]) -> RuntimeCoachingResult:
    """
    Run the coaching pipeline from a fixture file.

    Parameters
    ----------
    fixture_path:
        Path to a MidiSessionInput JSON fixture.

    Returns
    -------
    RuntimeCoachingResult from running the pipeline.
    """
    import json

    path = Path(fixture_path)
    with open(path) as f:
        data = json.load(f)

    midi_input = MidiSessionInput.model_validate(data)
    return run_coaching_pipeline(midi_input)


__all__ = [
    "RUNTIME_VERSION",
    "run_coaching_pipeline",
    "normalize_runtime_output",
    "run_fixture_pipeline",
]
