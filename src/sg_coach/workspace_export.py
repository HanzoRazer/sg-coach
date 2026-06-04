"""
Workspace Export Builder.

Sprint 37: Workspace Export & Share Package.

Provides:
- build_workspace_export_manifest(): Build export manifest
- build_workspace_export_package(): Build complete export package
- redact_workspace_export_package(): Apply redaction to export package

Core rules:
- Export packages are snapshots
- Export builders must not mutate source projections
- JSON is canonical in v1
- Redaction must not change pedagogical meaning
- Export packages are not evidence ledgers
"""
from __future__ import annotations

import secrets
from typing import Any

from sg_spec.schemas.pedagogical_narrative import PedagogicalNarrative
from sg_spec.schemas.pedagogical_visualization import PedagogicalTimelineView
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspacePaneType,
)
from sg_spec.schemas.workspace_export import (
    WORKSPACE_EXPORT_VERSION,
    WorkspaceExportFormat,
    WorkspaceExportManifest,
    WorkspaceExportPackage,
    WorkspaceExportRedactionLevel,
)


WORKSPACE_EXPORT_ENGINE_VERSION = "0.1.0"

STUDENT_SAFE_METADATA_KEYS = frozenset([
    "teacher_internal_notes",
    "private_teacher_notes",
    "internal_notes",
    "mediation_private_notes",
])

ANONYMIZED_ID_FIELDS = frozenset([
    "student_id",
    "teacher_id",
    "runtime_session_id",
])

ANONYMIZED_METADATA_PATTERNS = frozenset([
    "student_id",
    "teacher_id",
    "student_name",
    "teacher_name",
    "email",
    "phone",
    "runtime_session_id",
])


def _generate_export_id() -> str:
    """Generate unique export ID."""
    return f"wexp_{secrets.token_hex(6)}"


def _collect_included_sections(
    workspace: SessionWorkspaceProjection,
    narrative: PedagogicalNarrative | None,
    timeline: PedagogicalTimelineView | None,
) -> list[str]:
    """
    Collect included sections in deterministic order.

    Order:
    1. workspace (always)
    2. narrative (if present)
    3. timeline (if present)
    4. visible workspace pane types in order_index order
    """
    sections: list[str] = ["workspace"]

    if narrative is not None:
        sections.append("narrative")

    if timeline is not None:
        sections.append("timeline")

    if workspace.layout and workspace.layout.panes:
        visible_panes = sorted(
            [p for p in workspace.layout.panes if p.visible],
            key=lambda p: p.order_index,
        )
        for pane in visible_panes:
            pane_type_name = pane.pane_type.value
            if pane_type_name not in sections:
                sections.append(pane_type_name)

    return sections


def _count_export_artifacts(
    workspace: SessionWorkspaceProjection,
    narrative: PedagogicalNarrative | None,
    timeline: PedagogicalTimelineView | None,
) -> dict[str, int]:
    """Count artifacts for manifest."""
    counts: dict[str, int] = {}

    if workspace.layout and workspace.layout.panes:
        counts["workspace_panes_total"] = len(workspace.layout.panes)
        counts["workspace_panes_visible"] = sum(
            1 for p in workspace.layout.panes if p.visible
        )
    else:
        counts["workspace_panes_total"] = 0
        counts["workspace_panes_visible"] = 0

    if workspace.notes:
        counts["workspace_notes"] = len(workspace.notes)
    else:
        counts["workspace_notes"] = 0

    if narrative is not None:
        counts["narrative_sections"] = len(narrative.sections) if narrative.sections else 0
        counts["narrative_notes"] = len(narrative.notes) if narrative.notes else 0
    else:
        counts["narrative_sections"] = 0
        counts["narrative_notes"] = 0

    if timeline is not None:
        counts["timeline_events"] = timeline.total_events
        counts["diagnosis_groups"] = len(timeline.diagnosis_groups) if timeline.diagnosis_groups else 0
        counts["timeline_notes"] = len(timeline.notes) if timeline.notes else 0
    else:
        counts["timeline_events"] = 0
        counts["diagnosis_groups"] = 0
        counts["timeline_notes"] = 0

    return counts


def build_workspace_export_manifest(
    *,
    workspace: SessionWorkspaceProjection,
    narrative: PedagogicalNarrative | None = None,
    timeline: PedagogicalTimelineView | None = None,
    redaction_level: WorkspaceExportRedactionLevel = WorkspaceExportRedactionLevel.none,
) -> WorkspaceExportManifest:
    """
    Build export manifest from workspace and optional components.

    Parameters
    ----------
    workspace:
        The session workspace projection.
    narrative:
        Optional pedagogical narrative.
    timeline:
        Optional pedagogical timeline view.
    redaction_level:
        Redaction level to apply.

    Returns
    -------
    WorkspaceExportManifest with metadata about the export.
    """
    included_sections = _collect_included_sections(workspace, narrative, timeline)
    artifact_counts = _count_export_artifacts(workspace, narrative, timeline)

    return WorkspaceExportManifest(
        export_id=_generate_export_id(),
        format=WorkspaceExportFormat.json,
        redaction_level=redaction_level,
        workspace_id=workspace.workspace_id,
        student_id=workspace.student_id,
        runtime_session_id=workspace.runtime_session_id,
        included_sections=included_sections,
        artifact_counts=artifact_counts,
    )


def build_workspace_export_package(
    *,
    workspace: SessionWorkspaceProjection,
    narrative: PedagogicalNarrative | None = None,
    timeline: PedagogicalTimelineView | None = None,
    redaction_level: WorkspaceExportRedactionLevel = WorkspaceExportRedactionLevel.none,
) -> WorkspaceExportPackage:
    """
    Build complete workspace export package.

    Parameters
    ----------
    workspace:
        The session workspace projection.
    narrative:
        Optional pedagogical narrative.
    timeline:
        Optional pedagogical timeline view.
    redaction_level:
        Redaction level to apply.

    Returns
    -------
    WorkspaceExportPackage ready for export.
    """
    manifest = build_workspace_export_manifest(
        workspace=workspace,
        narrative=narrative,
        timeline=timeline,
        redaction_level=redaction_level,
    )

    package = WorkspaceExportPackage(
        manifest=manifest,
        workspace=workspace,
        narrative=narrative,
        timeline=timeline,
    )

    if redaction_level != WorkspaceExportRedactionLevel.none:
        package = redact_workspace_export_package(package, redaction_level)

    return package


def _redact_metadata_dict(
    metadata: dict[str, Any],
    redaction_level: WorkspaceExportRedactionLevel,
) -> dict[str, Any]:
    """Redact metadata dictionary based on redaction level."""
    if not metadata:
        return {}

    result = {}

    for key, value in metadata.items():
        should_remove = False

        if redaction_level == WorkspaceExportRedactionLevel.student_safe:
            if key in STUDENT_SAFE_METADATA_KEYS:
                should_remove = True

        elif redaction_level == WorkspaceExportRedactionLevel.anonymized:
            if key in STUDENT_SAFE_METADATA_KEYS:
                should_remove = True
            for pattern in ANONYMIZED_METADATA_PATTERNS:
                if pattern in key.lower():
                    should_remove = True
                    break

        if not should_remove:
            if isinstance(value, dict):
                result[key] = _redact_metadata_dict(value, redaction_level)
            elif isinstance(value, list):
                result[key] = [
                    _redact_metadata_dict(item, redaction_level)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

    return result


def _redact_model_dict(
    data: dict[str, Any],
    redaction_level: WorkspaceExportRedactionLevel,
) -> dict[str, Any]:
    """Recursively redact a model dictionary."""
    result = {}

    for key, value in data.items():
        if redaction_level == WorkspaceExportRedactionLevel.anonymized:
            if key in ANONYMIZED_ID_FIELDS:
                result[key] = None
                continue

        if key == "metadata" and isinstance(value, dict):
            result[key] = _redact_metadata_dict(value, redaction_level)
        elif isinstance(value, dict):
            result[key] = _redact_model_dict(value, redaction_level)
        elif isinstance(value, list):
            result[key] = [
                _redact_model_dict(item, redaction_level)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def redact_workspace_export_package(
    package: WorkspaceExportPackage,
    redaction_level: WorkspaceExportRedactionLevel,
) -> WorkspaceExportPackage:
    """
    Apply redaction to an export package.

    Parameters
    ----------
    package:
        The export package to redact.
    redaction_level:
        Redaction level to apply.

    Returns
    -------
    New WorkspaceExportPackage with redaction applied.
    Source package is not mutated.
    """
    if redaction_level == WorkspaceExportRedactionLevel.none:
        return package.model_copy(deep=True)

    package_data = package.model_dump(mode="python")

    manifest_data = package_data["manifest"]
    manifest_data["redaction_level"] = redaction_level.value

    if redaction_level == WorkspaceExportRedactionLevel.anonymized:
        manifest_data["student_id"] = None
        manifest_data["runtime_session_id"] = None

    manifest_data["metadata"] = _redact_metadata_dict(
        manifest_data.get("metadata", {}),
        redaction_level,
    )

    workspace_data = package_data["workspace"]
    workspace_data = _redact_model_dict(workspace_data, redaction_level)

    narrative_data = package_data.get("narrative")
    if narrative_data:
        narrative_data = _redact_model_dict(narrative_data, redaction_level)

    timeline_data = package_data.get("timeline")
    if timeline_data:
        timeline_data = _redact_model_dict(timeline_data, redaction_level)

    package_metadata = package_data.get("metadata", {})
    package_metadata = _redact_metadata_dict(package_metadata, redaction_level)

    return WorkspaceExportPackage(
        manifest=WorkspaceExportManifest.model_validate(manifest_data),
        workspace=workspace_data,
        narrative=narrative_data,
        timeline=timeline_data,
        metadata=package_metadata,
        version=package_data.get("version", WORKSPACE_EXPORT_VERSION),
    )


__all__ = [
    "WORKSPACE_EXPORT_ENGINE_VERSION",
    "build_workspace_export_manifest",
    "build_workspace_export_package",
    "redact_workspace_export_package",
]
