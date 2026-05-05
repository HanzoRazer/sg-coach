"""
Learning Aggregation — Convert signals to effectiveness profiles.

Sprint 5 Dev Order 4: Aggregation only, no adaptation.

This module provides:
- aggregate_effectiveness(): Groups signals into ActionEffectivenessProfile
- compute_aggregate_confidence(): Calculates confidence from sample size

Core rule: Weak signals should not influence effectiveness,
but they should remain visible.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.learning_aggregation import (
    ActionEffectivenessProfile,
    LearningSignalAggregateSet,
)
from sg_spec.schemas.user_feedback import LearningSignal

from .learning_weight import WEAK_SIGNAL_THRESHOLD, is_weak_signal


def aggregate_profile_key(
    signal: LearningSignal,
) -> Tuple[DiagnosisCode, FeedbackActionType]:
    """Extract the grouping key from a signal."""
    return (signal.source_finding_code, signal.action_type)


def compute_aggregate_confidence(usable_count: int) -> float:
    """
    Compute confidence from usable signal count.

    Formula: min(1.0, usable_count / 10)
    """
    return min(1.0, usable_count / 10)


def aggregate_effectiveness(
    signals: Sequence[LearningSignal],
    *,
    include_weak: bool = False,
) -> LearningSignalAggregateSet:
    """
    Aggregate LearningSignals into ActionEffectivenessProfiles.

    Groups signals by (source_finding_code, action_type) and computes
    aggregate statistics for each group.

    Parameters
    ----------
    signals:
        Sequence of LearningSignal records to aggregate.
    include_weak:
        If True, include weak signals in average_weight calculation.
        Default False excludes them.

    Returns
    -------
    LearningSignalAggregateSet with one profile per unique
    (diagnosis_code, action_type) combination.

    Notes
    -----
    - Does not mutate input signals
    - Does not store profiles
    - Does not change recommendation ranking
    - Weak signals remain visible in weak_signal_count
    """
    if not signals:
        return LearningSignalAggregateSet(profiles=[], total_signals=0)

    # Group signals by key
    groups: Dict[Tuple[DiagnosisCode, FeedbackActionType], List[LearningSignal]] = (
        defaultdict(list)
    )
    for signal in signals:
        key = aggregate_profile_key(signal)
        groups[key].append(signal)

    # Build profiles
    profiles: List[ActionEffectivenessProfile] = []
    for (diagnosis_code, action_type), group_signals in groups.items():
        signal_count = len(group_signals)
        weak_signals = [s for s in group_signals if is_weak_signal(s.weight)]
        weak_signal_count = len(weak_signals)

        if include_weak:
            usable_signals = group_signals
            usable_signal_count = signal_count
        else:
            usable_signals = [s for s in group_signals if not is_weak_signal(s.weight)]
            usable_signal_count = len(usable_signals)

        if usable_signal_count == 0:
            average_weight = 0.0
            confidence = 0.0
        else:
            total_weight = sum(s.weight for s in usable_signals)
            average_weight = total_weight / usable_signal_count
            confidence = compute_aggregate_confidence(usable_signal_count)

        profiles.append(ActionEffectivenessProfile(
            diagnosis_code=diagnosis_code,
            action_type=action_type,
            average_weight=average_weight,
            signal_count=signal_count,
            usable_signal_count=usable_signal_count,
            weak_signal_count=weak_signal_count,
            confidence=confidence,
        ))

    return LearningSignalAggregateSet(
        profiles=profiles,
        total_signals=len(signals),
    )


__all__ = [
    "aggregate_profile_key",
    "compute_aggregate_confidence",
    "aggregate_effectiveness",
]
