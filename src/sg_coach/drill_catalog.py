"""
Drill Catalog — Static v1 drill mappings for Layer 1 diagnosis codes.

Sprint 8: Static catalog only, no curriculum automation.

This module provides:
- DEFAULT_DRILL_CATALOG: Mapping from (DiagnosisCode, FeedbackActionType) to DrillReference

This is a temporary catalog. sg-curriculum becomes the canonical
drill source later.
"""
from __future__ import annotations

from typing import Dict, Tuple

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.drill_resolution import DrillDifficulty, DrillReference
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType


# Static drill catalog for Layer 1 diagnosis codes
DEFAULT_DRILL_CATALOG: Dict[Tuple[DiagnosisCode, FeedbackActionType], DrillReference] = {
    # DIM_ORBIT_VIOLATION + assign_drill
    (DiagnosisCode.DIM_ORBIT_VIOLATION, FeedbackActionType.assign_drill): DrillReference(
        drill_id="diminished_orbit_isolation_v1",
        title="Diminished Orbit Isolation",
        description="Practice diminished seventh arpeggios in isolation to build orbit awareness",
        diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
        action_type=FeedbackActionType.assign_drill,
        difficulty=DrillDifficulty.intermediate,
        estimated_duration_sec=180,
        tags=["diminished", "arpeggio", "orbit", "isolation"],
        params={
            "tempo_bpm": 60,
            "repetition_count": 4,
        },
    ),

    # TIMING_GRID_DEVIATION + assign_drill
    (DiagnosisCode.TIMING_GRID_DEVIATION, FeedbackActionType.assign_drill): DrillReference(
        drill_id="timing_grid_quarter_note_reset_v1",
        title="Quarter Note Timing Reset",
        description="Reset timing accuracy with quarter note exercises against a metronome",
        diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        action_type=FeedbackActionType.assign_drill,
        difficulty=DrillDifficulty.beginner,
        estimated_duration_sec=120,
        tags=["timing", "metronome", "quarter-note", "reset"],
        params={
            "tempo_bpm": 80,
            "duration_bars": 8,
            "threshold_ms": 30,
        },
    ),

    # WRONG_NOTE + assign_drill
    (DiagnosisCode.WRONG_NOTE, FeedbackActionType.assign_drill): DrillReference(
        drill_id="single_note_reference_recall_v1",
        title="Single Note Reference Recall",
        description="Practice identifying and playing single notes accurately",
        diagnosis_code=DiagnosisCode.WRONG_NOTE,
        action_type=FeedbackActionType.assign_drill,
        difficulty=DrillDifficulty.beginner,
        estimated_duration_sec=90,
        tags=["note", "recall", "accuracy", "pitch"],
        params={
            "fret_range": [0, 12],
            "repetition_count": 8,
        },
    ),

    # PITCH_DEVIATION + assign_drill
    (DiagnosisCode.PITCH_DEVIATION, FeedbackActionType.assign_drill): DrillReference(
        drill_id="pitch_centering_sustain_v1",
        title="Pitch Centering Sustain",
        description="Sustain notes while centering pitch to eliminate deviation",
        diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
        action_type=FeedbackActionType.assign_drill,
        difficulty=DrillDifficulty.intermediate,
        estimated_duration_sec=150,
        tags=["pitch", "intonation", "sustain", "centering"],
        params={
            "sustain_duration_sec": 4,
            "cents_threshold": 10,
            "repetition_count": 6,
        },
    ),
}


__all__ = [
    "DEFAULT_DRILL_CATALOG",
]
