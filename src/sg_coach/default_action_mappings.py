"""
Default Action Mappings — Registry of DiagnosisCode to ActionMapping.

Sprint 4: Canonical mappings for Layer 1 diagnosis codes.

These mappings define the default coaching actions for each diagnosis.
The recommendation engine uses this registry when no custom mappings are provided.
"""
from __future__ import annotations

from typing import Dict

from sg_spec.schemas.action_mapping import ActionMapping, RecommendedAction
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType, FeedbackDomain


# DIM_ORBIT_VIOLATION: Played note outside the expected diminished orbit
_DIM_ORBIT_VIOLATION_MAPPING = ActionMapping(
    diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
    domain=FeedbackDomain.harmony,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate orbit note",
            rationale="Focus on the note that fell outside the diminished orbit",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Review diminished orbit",
            rationale="The diminished orbit contains symmetric note patterns",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.assign_drill,
            label="Practice diminished patterns",
            rationale="Build familiarity with symmetric diminished structures",
            requires_curriculum=True,
        ),
    ],
    version="0.1",
)

# TIMING_GRID_DEVIATION: Note played too early or late
_TIMING_GRID_DEVIATION_MAPPING = ActionMapping(
    diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
    domain=FeedbackDomain.timing,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.slow_down,
            label="Reduce tempo",
            rationale="Slower tempo allows more precise placement",
            priority=1,
            params={"tempo_reduction_pct": 10},
        ),
        RecommendedAction(
            action_type=FeedbackActionType.repeat,
            label="Repeat with metronome",
            rationale="Lock in to the grid with audible reference",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.retry_section,
            label="Retry problem bars",
            rationale="Focus on the specific passage with timing issues",
            target_span_required=True,
        ),
    ],
    version="0.1",
)

# WRONG_NOTE: Played a different note than expected
_WRONG_NOTE_MAPPING = ActionMapping(
    diagnosis_code=DiagnosisCode.WRONG_NOTE,
    domain=FeedbackDomain.pitch,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate problem note",
            rationale="Practice the correct note in isolation",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Review expected note",
            rationale="Confirm the correct note before retrying",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.retry_section,
            label="Retry passage",
            rationale="Play the section again with correct note",
            target_span_required=True,
        ),
    ],
    version="0.1",
)

# PITCH_DEVIATION: Correct note but pitch (intonation) is off
_PITCH_DEVIATION_MAPPING = ActionMapping(
    diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
    domain=FeedbackDomain.pitch,
    default_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.isolate,
            label="Isolate pitch",
            rationale="Focus on intonation for this specific note",
            priority=1,
            target_span_required=True,
        ),
        RecommendedAction(
            action_type=FeedbackActionType.review_reference,
            label="Check tuning reference",
            rationale="Compare against reference pitch",
            priority=2,
        ),
    ],
    escalation_actions=[
        RecommendedAction(
            action_type=FeedbackActionType.repeat,
            label="Repeat with pitch focus",
            rationale="Play again while listening carefully to intonation",
        ),
    ],
    version="0.1",
)


# Registry: DiagnosisCode -> ActionMapping
DEFAULT_ACTION_MAPPINGS: Dict[DiagnosisCode, ActionMapping] = {
    DiagnosisCode.DIM_ORBIT_VIOLATION: _DIM_ORBIT_VIOLATION_MAPPING,
    DiagnosisCode.TIMING_GRID_DEVIATION: _TIMING_GRID_DEVIATION_MAPPING,
    DiagnosisCode.WRONG_NOTE: _WRONG_NOTE_MAPPING,
    DiagnosisCode.PITCH_DEVIATION: _PITCH_DEVIATION_MAPPING,
}


__all__ = [
    "DEFAULT_ACTION_MAPPINGS",
]
