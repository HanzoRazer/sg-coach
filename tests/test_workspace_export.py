"""
Tests for workspace_export module.

Sprint 37: Workspace Export & Share Package.
"""
from __future__ import annotations

import pytest

from sg_spec.schemas.guided_practice_view import (
    GuidedPracticeAdaptiveView,
    GuidedPracticeAssignmentView,
    GuidedPracticePlaybackView,
    GuidedPracticeSessionView,
    GuidedPracticeTeacherMediationView,
)
from sg_spec.schemas.pedagogical_narrative import (
    NarrativeAudience,
    NarrativeSeverity,
    NarrativeSection,
    PedagogicalNarrative,
)
from sg_spec.schemas.pedagogical_visualization import (
    PedagogicalTimelineView,
)
from sg_spec.schemas.practice_assignment import PracticeAssignmentType
from sg_spec.schemas.session_workspace import (
    SessionWorkspaceProjection,
    WorkspaceAudience,
    WorkspaceLayout,
    WorkspacePane,
    WorkspacePaneType,
)
from sg_spec.schemas.workspace_export import (
    WORKSPACE_EXPORT_VERSION,
    WorkspaceExportFormat,
    WorkspaceExportManifest,
    WorkspaceExportPackage,
    WorkspaceExportRedactionLevel,
)

from sg_coach.workspace_export import (
    WORKSPACE_EXPORT_ENGINE_VERSION,
    build_workspace_export_manifest,
    build_workspace_export_package,
    redact_workspace_export_package,
)


def _create_minimal_workspace() -> SessionWorkspaceProjection:
    """Create minimal workspace for testing."""
    return SessionWorkspaceProjection(
        workspace_id="swp_test123456",
        audience=WorkspaceAudience.mixed,
    )


def _create_workspace_with_layout() -> SessionWorkspaceProjection:
    """Create workspace with layout and panes."""
    panes = [
        WorkspacePane(
            pane_id="swpane_001",
            pane_type=WorkspacePaneType.assignment,
            title="Assignment",
            visible=True,
            order_index=0,
        ),
        WorkspacePane(
            pane_id="swpane_002",
            pane_type=WorkspacePaneType.playback,
            title="Playback",
            visible=True,
            order_index=1,
        ),
        WorkspacePane(
            pane_id="swpane_003",
            pane_type=WorkspacePaneType.adaptive_guidance,
            title="Adaptive Guidance",
            visible=False,
            order_index=2,
        ),
        WorkspacePane(
            pane_id="swpane_004",
            pane_type=WorkspacePaneType.teacher_mediation,
            title="Teacher Mediation",
            visible=True,
            order_index=3,
        ),
    ]

    layout = WorkspaceLayout(
        layout_id="swl_test123456",
        audience=WorkspaceAudience.mixed,
        panes=panes,
    )

    return SessionWorkspaceProjection(
        workspace_id="swp_test123456",
        student_id="student_123",
        runtime_session_id="rts_test123456",
        audience=WorkspaceAudience.mixed,
        layout=layout,
        notes=["Test note 1", "Test note 2"],
        metadata={
            "source": "test",
            "teacher_internal_notes": "private",
            "student_id": "student_123",
        },
    )


def _create_narrative() -> PedagogicalNarrative:
    """Create pedagogical narrative for testing."""
    return PedagogicalNarrative(
        narrative_id="pn_test12345678",
        audience=NarrativeAudience.mixed,
        title="Test Narrative",
        overview="Test overview",
        sections=[
            NarrativeSection(
                section_id="pns_test123456",
                title="Test Section 1",
                summary="Test summary 1",
                severity=NarrativeSeverity.informational,
            ),
            NarrativeSection(
                section_id="pns_test789012",
                title="Test Section 2",
                summary="Test summary 2",
                severity=NarrativeSeverity.warning,
            ),
        ],
        notes=["Narrative note"],
        metadata={
            "private_teacher_notes": "secret",
            "student_name": "John Doe",
        },
    )


def _create_timeline() -> PedagogicalTimelineView:
    """Create timeline view for testing."""
    return PedagogicalTimelineView(
        student_id="student_123",
        total_events=5,
        diagnosis_groups=[],
        timeline_events=[],
        notes=["Timeline note 1", "Timeline note 2", "Timeline note 3"],
    )


class TestWorkspaceExportEngineVersion:
    """Test engine version constant."""

    def test_version_is_string(self) -> None:
        assert isinstance(WORKSPACE_EXPORT_ENGINE_VERSION, str)
        assert len(WORKSPACE_EXPORT_ENGINE_VERSION) > 0


class TestBuildWorkspaceExportManifest:
    """Test build_workspace_export_manifest function."""

    def test_minimal_manifest(self) -> None:
        workspace = _create_minimal_workspace()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert manifest.export_id.startswith("wexp_")
        assert manifest.format == WorkspaceExportFormat.json
        assert manifest.redaction_level == WorkspaceExportRedactionLevel.none
        assert manifest.workspace_id == "swp_test123456"

    def test_manifest_export_id_unique(self) -> None:
        workspace = _create_minimal_workspace()

        manifest1 = build_workspace_export_manifest(workspace=workspace)
        manifest2 = build_workspace_export_manifest(workspace=workspace)

        assert manifest1.export_id != manifest2.export_id

    def test_manifest_includes_workspace_id(self) -> None:
        workspace = _create_workspace_with_layout()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert manifest.workspace_id == "swp_test123456"
        assert manifest.student_id == "student_123"
        assert manifest.runtime_session_id == "rts_test123456"

    def test_manifest_included_sections_workspace_only(self) -> None:
        workspace = _create_workspace_with_layout()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert "workspace" in manifest.included_sections
        assert manifest.included_sections[0] == "workspace"

    def test_manifest_included_sections_with_narrative(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
        )

        assert "workspace" in manifest.included_sections
        assert "narrative" in manifest.included_sections
        assert manifest.included_sections.index("workspace") < manifest.included_sections.index("narrative")

    def test_manifest_included_sections_with_timeline(self) -> None:
        workspace = _create_workspace_with_layout()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            timeline=timeline,
        )

        assert "workspace" in manifest.included_sections
        assert "timeline" in manifest.included_sections

    def test_manifest_included_sections_with_all(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        assert manifest.included_sections[:3] == ["workspace", "narrative", "timeline"]

    def test_manifest_included_sections_visible_panes(self) -> None:
        workspace = _create_workspace_with_layout()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert "assignment" in manifest.included_sections
        assert "playback" in manifest.included_sections
        assert "teacher_mediation" in manifest.included_sections
        assert "adaptive_guidance" not in manifest.included_sections

    def test_manifest_artifact_counts(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        assert manifest.artifact_counts["workspace_panes_total"] == 4
        assert manifest.artifact_counts["workspace_panes_visible"] == 3
        assert manifest.artifact_counts["workspace_notes"] == 2
        assert manifest.artifact_counts["narrative_sections"] == 2
        assert manifest.artifact_counts["narrative_notes"] == 1
        assert manifest.artifact_counts["timeline_events"] == 5
        assert manifest.artifact_counts["timeline_notes"] == 3

    def test_manifest_artifact_counts_no_optional(self) -> None:
        workspace = _create_minimal_workspace()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert manifest.artifact_counts["narrative_sections"] == 0
        assert manifest.artifact_counts["timeline_events"] == 0

    def test_manifest_redaction_level(self) -> None:
        workspace = _create_minimal_workspace()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.student_safe,
        )

        assert manifest.redaction_level == WorkspaceExportRedactionLevel.student_safe


class TestBuildWorkspaceExportPackage:
    """Test build_workspace_export_package function."""

    def test_minimal_package(self) -> None:
        workspace = _create_minimal_workspace()

        package = build_workspace_export_package(workspace=workspace)

        assert package.manifest.export_id.startswith("wexp_")
        assert package.workspace is not None
        assert package.narrative is None
        assert package.timeline is None
        assert package.version == WORKSPACE_EXPORT_VERSION

    def test_package_with_narrative(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
        )

        assert package.narrative is not None

    def test_package_with_timeline(self) -> None:
        workspace = _create_workspace_with_layout()
        timeline = _create_timeline()

        package = build_workspace_export_package(
            workspace=workspace,
            timeline=timeline,
        )

        assert package.timeline is not None

    def test_package_with_all(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        assert package.workspace is not None
        assert package.narrative is not None
        assert package.timeline is not None

    def test_package_serializes_to_json(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        data = package.model_dump(mode="json")

        assert "manifest" in data
        assert "workspace" in data
        assert "narrative" in data
        assert "timeline" in data

    def test_package_no_redaction_default(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(workspace=workspace)

        assert package.manifest.redaction_level == WorkspaceExportRedactionLevel.none


class TestRedactWorkspaceExportPackage:
    """Test redact_workspace_export_package function."""

    def test_none_redaction_preserves_all(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.none,
        )

        assert redacted.manifest.student_id == "student_123"

    def test_student_safe_removes_teacher_notes(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.student_safe,
        )

        workspace_data = redacted.workspace
        if isinstance(workspace_data, dict):
            metadata = workspace_data.get("metadata", {})
            assert "teacher_internal_notes" not in metadata

    def test_student_safe_keeps_student_id(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.student_safe,
        )

        assert redacted.manifest.student_id == "student_123"

    def test_anonymized_removes_student_id(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        assert redacted.manifest.student_id is None
        assert redacted.manifest.runtime_session_id is None

    def test_anonymized_removes_ids_from_workspace(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        workspace_data = redacted.workspace
        if isinstance(workspace_data, dict):
            assert workspace_data.get("student_id") is None
            assert workspace_data.get("runtime_session_id") is None

    def test_anonymized_removes_id_from_metadata(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        workspace_data = redacted.workspace
        if isinstance(workspace_data, dict):
            metadata = workspace_data.get("metadata", {})
            assert "student_id" not in metadata

    def test_anonymized_removes_name_from_narrative_metadata(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()

        package = build_workspace_export_package(
            workspace=workspace,
            narrative=narrative,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        if isinstance(redacted.narrative, dict):
            metadata = redacted.narrative.get("metadata", {})
            assert "student_name" not in metadata

    def test_redaction_does_not_mutate_source(self) -> None:
        workspace = _create_workspace_with_layout()

        original_student_id = workspace.student_id

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        assert workspace.student_id == original_student_id
        assert package.manifest.student_id == original_student_id

    def test_redaction_preserves_pedagogical_ids(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        assert redacted.manifest.workspace_id == "swp_test123456"

    def test_redaction_updates_manifest_level(self) -> None:
        workspace = _create_workspace_with_layout()

        package = build_workspace_export_package(
            workspace=workspace,
            redaction_level=WorkspaceExportRedactionLevel.none,
        )

        redacted = redact_workspace_export_package(
            package,
            WorkspaceExportRedactionLevel.anonymized,
        )

        assert redacted.manifest.redaction_level == WorkspaceExportRedactionLevel.anonymized


class TestIncludedSectionsOrder:
    """Test included_sections ordering."""

    def test_workspace_first(self) -> None:
        workspace = _create_workspace_with_layout()

        manifest = build_workspace_export_manifest(workspace=workspace)

        assert manifest.included_sections[0] == "workspace"

    def test_narrative_before_timeline(self) -> None:
        workspace = _create_minimal_workspace()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        narrative_index = manifest.included_sections.index("narrative")
        timeline_index = manifest.included_sections.index("timeline")
        assert narrative_index < timeline_index

    def test_visible_panes_after_timeline(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        timeline_index = manifest.included_sections.index("timeline")
        if "assignment" in manifest.included_sections:
            assignment_index = manifest.included_sections.index("assignment")
            assert timeline_index < assignment_index

    def test_panes_in_order_index_order(self) -> None:
        workspace = _create_workspace_with_layout()

        manifest = build_workspace_export_manifest(workspace=workspace)

        if "assignment" in manifest.included_sections and "playback" in manifest.included_sections:
            assignment_index = manifest.included_sections.index("assignment")
            playback_index = manifest.included_sections.index("playback")
            assert assignment_index < playback_index

    def test_no_duplicate_sections(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        assert len(manifest.included_sections) == len(set(manifest.included_sections))


class TestArtifactCountsCompleteness:
    """Test artifact_counts field completeness."""

    def test_all_standard_keys_present(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        expected_keys = [
            "workspace_panes_total",
            "workspace_panes_visible",
            "workspace_notes",
            "narrative_sections",
            "narrative_notes",
            "timeline_events",
            "diagnosis_groups",
            "timeline_notes",
        ]

        for key in expected_keys:
            assert key in manifest.artifact_counts

    def test_counts_are_integers(self) -> None:
        workspace = _create_workspace_with_layout()
        narrative = _create_narrative()
        timeline = _create_timeline()

        manifest = build_workspace_export_manifest(
            workspace=workspace,
            narrative=narrative,
            timeline=timeline,
        )

        for key, value in manifest.artifact_counts.items():
            assert isinstance(value, int)

    def test_counts_are_non_negative(self) -> None:
        workspace = _create_minimal_workspace()

        manifest = build_workspace_export_manifest(workspace=workspace)

        for key, value in manifest.artifact_counts.items():
            assert value >= 0
