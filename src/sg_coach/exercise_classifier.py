"""
Exercise Classifier

Determines exercise type from program_ref to enable targeted evaluation.
Used by evaluate_session to decide which evaluators to run.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from .schemas import ProgramRef


class ExerciseCategory(str, Enum):
    """High-level exercise categories for evaluation routing."""
    DIMINISHED_NAVIGATION = "diminished_navigation"
    TIMING_GRID = "timing_grid"
    TIMING = "timing"
    TECHNIQUE = "technique"
    HARMONIC = "harmonic"
    GENERAL = "general"


# Program name patterns that indicate diminished navigation exercises
DIMINISHED_PATTERNS = [
    "diminished/",
    "dim_orbit",
    "dim_navigation",
    "dim_rotation",
    "diminished_orbit",
    "diminished_navigation",
]

# Program name patterns that indicate timing grid exercises
TIMING_GRID_PATTERNS = [
    "timing_grid",
    "timing_quarter_notes",
    "timing_layer1a",
    "timing/grid",
    "grid_timing",
]


def classify_exercise(program_ref: ProgramRef) -> ExerciseCategory:
    """
    Classify an exercise based on its program_ref.

    Parameters
    ----------
    program_ref:
        Reference to the exercise program.

    Returns
    -------
    The exercise category for evaluation routing.
    """
    name_lower = program_ref.name.lower()

    # Check for diminished navigation exercises
    for pattern in DIMINISHED_PATTERNS:
        if pattern in name_lower:
            return ExerciseCategory.DIMINISHED_NAVIGATION

    # Check for timing grid exercises
    for pattern in TIMING_GRID_PATTERNS:
        if pattern in name_lower:
            return ExerciseCategory.TIMING_GRID

    # Default to general
    return ExerciseCategory.GENERAL


def is_timing_grid_exercise(program_ref: ProgramRef) -> bool:
    """
    Check if an exercise is a timing grid exercise.

    This is the gate for running the timing grid evaluator.
    """
    return classify_exercise(program_ref) == ExerciseCategory.TIMING_GRID


def is_diminished_exercise(program_ref: ProgramRef) -> bool:
    """
    Check if an exercise is a diminished navigation exercise.

    This is the gate for running the diminished orbit evaluator.
    """
    return classify_exercise(program_ref) == ExerciseCategory.DIMINISHED_NAVIGATION


def extract_key_from_program(program_ref: ProgramRef) -> Optional[str]:
    """
    Extract the key from a program name if present.

    Convention: program names ending in _C, _G, _D, etc. indicate the key.
    Example: "dim_orbit_awareness_C" -> "C"
    """
    name = program_ref.name

    # Try to find key suffix pattern (e.g., "_C", "_G", "_Bb")
    if "_" in name:
        parts = name.split("_")
        last = parts[-1].rstrip(".ztprog").rstrip(".ztex")

        # Check if it looks like a key name (1-2 chars, starts with A-G)
        if len(last) <= 2 and last[0].upper() in "ABCDEFG":
            return last.upper() if len(last) == 1 else last[0].upper() + last[1]

    return None


__all__ = [
    "ExerciseCategory",
    "classify_exercise",
    "is_diminished_exercise",
    "is_timing_grid_exercise",
    "extract_key_from_program",
    "DIMINISHED_PATTERNS",
    "TIMING_GRID_PATTERNS",
]
