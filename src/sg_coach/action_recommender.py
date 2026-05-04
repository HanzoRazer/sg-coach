"""
Action Recommender — Turn CoachFindings into recommended actions.

Sprint 4: The recommendation engine that applies ActionMappings to findings.

This module implements the action selection rules defined in
docs/action_mapping_governance.md.

Usage:
    from sg_coach import recommend_actions, recommend_actions_batch

    # Single finding
    rec_set = recommend_actions(finding)

    # Batch
    rec_sets = recommend_actions_batch(evaluation.findings)
"""
from __future__ import annotations

from typing import List, Mapping, Optional, Sequence

from sg_spec.schemas.action_mapping import (
    ActionMapping,
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode

from .schemas import (
    CoachFinding,
    Severity,
    FeedbackSeverity,
)
from .default_action_mappings import DEFAULT_ACTION_MAPPINGS


def _normalize_severity(finding: CoachFinding) -> str:
    """
    Normalize finding severity to decision level.

    Returns one of: "info", "warning", "error", "critical"
    """
    # Check if finding has FeedbackSeverity via property
    try:
        fb_severity = finding.feedback_severity
        return fb_severity.value
    except (AttributeError, TypeError):
        pass

    # Fall back to legacy Severity
    severity = finding.severity
    if severity == Severity.info:
        return "info"
    elif severity == Severity.secondary:
        return "warning"
    elif severity == Severity.primary:
        return "error"
    else:
        return "warning"  # Safe default


def _has_location(finding: CoachFinding) -> bool:
    """
    Check if finding has usable location info.

    Location exists if any of:
    - finding.target_span is not None
    - finding.evidence.index is not None
    - finding.evidence.beat is not None
    """
    # Check target_span
    if hasattr(finding, "target_span") and finding.target_span is not None:
        return True

    # Check evidence fields
    evidence = finding.evidence
    if evidence is not None:
        if evidence.index is not None:
            return True
        if evidence.beat is not None:
            return True

    return False


def _filter_actions(
    actions: List[RecommendedAction],
    has_location: bool,
) -> List[RecommendedAction]:
    """
    Filter actions based on target_span_required and location availability.

    Actions with target_span_required=True are omitted if no location exists.
    """
    result = []
    for action in actions:
        if action.target_span_required and not has_location:
            continue  # Omit silently, don't fail
        result.append(action)
    return result


def recommend_actions(
    finding: CoachFinding,
    mappings: Optional[Mapping[DiagnosisCode, ActionMapping]] = None,
) -> ActionRecommendationSet:
    """
    Generate action recommendations for a single CoachFinding.

    Parameters
    ----------
    finding:
        The CoachFinding to generate recommendations for.
    mappings:
        Optional mapping registry. If None, uses DEFAULT_ACTION_MAPPINGS.

    Returns
    -------
    ActionRecommendationSet with recommended actions.

    Rules
    -----
    - finding.code determines the mapping
    - finding.severity determines default vs escalation actions
    - finding.target_span/evidence determines retry_section eligibility
    - Missing mapping returns empty set with source="no_mapping"
    - Actions requiring location are omitted if no location exists
    """
    if mappings is None:
        mappings = DEFAULT_ACTION_MAPPINGS

    # Get diagnosis code from finding
    code = finding.code
    if code is None:
        # No diagnosis code, cannot map
        return ActionRecommendationSet(
            finding_code=DiagnosisCode.DIM_ORBIT_VIOLATION,  # Placeholder, will be overwritten
            actions=[],
            source="no_code",
            confidence=0.0,
        )

    # Look up mapping
    mapping = mappings.get(code)
    if mapping is None:
        return ActionRecommendationSet(
            finding_code=code,
            actions=[],
            source="no_mapping",
            confidence=1.0,
        )

    # Normalize severity
    severity = _normalize_severity(finding)

    # Check for location
    has_loc = _has_location(finding)

    # Collect actions
    actions: List[RecommendedAction] = []

    # Add default actions (always)
    filtered_defaults = _filter_actions(list(mapping.default_actions), has_loc)
    actions.extend(filtered_defaults)

    # Add escalation actions for severe findings
    if severity in ("error", "critical"):
        filtered_escalations = _filter_actions(list(mapping.escalation_actions), has_loc)
        actions.extend(filtered_escalations)

    return ActionRecommendationSet(
        finding_code=code,
        finding_id=None,  # CoachFinding doesn't have an ID field currently
        actions=actions,
        source="action_mapping",
        confidence=1.0,
        version=mapping.version,
    )


def recommend_actions_batch(
    findings: Sequence[CoachFinding],
    mappings: Optional[Mapping[DiagnosisCode, ActionMapping]] = None,
) -> List[ActionRecommendationSet]:
    """
    Generate action recommendations for multiple CoachFindings.

    Parameters
    ----------
    findings:
        Sequence of CoachFindings to generate recommendations for.
    mappings:
        Optional mapping registry. If None, uses DEFAULT_ACTION_MAPPINGS.

    Returns
    -------
    List of ActionRecommendationSets, one per finding.

    Notes
    -----
    - Order matches input findings order
    - Does not deduplicate actions across findings (v1 behavior)
    """
    if mappings is None:
        mappings = DEFAULT_ACTION_MAPPINGS

    return [recommend_actions(finding, mappings) for finding in findings]


__all__ = [
    "recommend_actions",
    "recommend_actions_batch",
]
