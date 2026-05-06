"""
Tests for Practice Assignment Assembler.

Sprint 9: Tests for assignment assembly.
"""
import pytest

from sg_coach.practice_assignment_assembler import (
    assemble_practice_assignment,
    assemble_practice_assignments,
)
from sg_spec.schemas.action_mapping import (
    ActionRecommendationSet,
    RecommendedAction,
)
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.coach_schemas import CoachFinding, TargetSpan
from sg_spec.schemas.drill_resolution import (
    DrillReference,
    DrillResolutionRequest,
    DrillResolutionResult,
)
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignmentSet,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)


def make_finding(
    code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    finding_id: str | None = "finding_001",
    target_span: TargetSpan | None = None,
) -> CoachFinding:
    """Helper to create test findings."""
    return CoachFinding(
        id=finding_id,
        type="timing",
        severity="primary",
        interpretation="Test finding",
        code=code,
        target_span=target_span,
    )


def make_action(
    action_type: FeedbackActionType = FeedbackActionType.slow_down,
    label: str = "Test action",
    rationale: str | None = "Test rationale",
    priority: int = 0,
    params: dict | None = None,
) -> RecommendedAction:
    """Helper to create test actions."""
    return RecommendedAction(
        action_type=action_type,
        label=label,
        rationale=rationale,
        priority=priority,
        params=params or {},
    )


def make_rec_set(
    actions: list[RecommendedAction],
    finding_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    rec_set_id: str | None = "rec_set_001",
) -> ActionRecommendationSet:
    """Helper to create test recommendation sets."""
    return ActionRecommendationSet(
        id=rec_set_id,
        finding_code=finding_code,
        actions=actions,
    )


def make_drill_result(
    resolved: bool = True,
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    action_type: FeedbackActionType = FeedbackActionType.assign_drill,
    drill_id: str = "test_drill_v1",
    drill_title: str = "Test Drill",
    reason: str | None = None,
) -> DrillResolutionResult:
    """Helper to create test drill resolution results."""
    request = DrillResolutionRequest(
        diagnosis_code=diagnosis_code,
        action_type=action_type,
    )
    drill = None
    if resolved:
        drill = DrillReference(
            drill_id=drill_id,
            title=drill_title,
            description="Test drill description",
        )
    return DrillResolutionResult(
        resolved=resolved,
        request=request,
        drill=drill,
        reason=reason,
    )


class TestAssembleNonDrillAssignments:
    """Test assembly of non-drill assignments."""

    def test_assemble_slow_down_assignment(self):
        finding = make_finding()
        action = make_action(
            action_type=FeedbackActionType.slow_down,
            label="Slow down the tempo",
            rationale="Reduce tempo by 10 BPM",
        )

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
        )

        assert assignment.assignment_type == PracticeAssignmentType.slow_down
        assert assignment.status == PracticeAssignmentStatus.ready
        assert assignment.title == "Slow down the tempo"
        assert assignment.instructions == "Reduce tempo by 10 BPM"
        assert assignment.drill is None

    def test_assemble_repeat_assignment(self):
        action = make_action(
            action_type=FeedbackActionType.repeat,
            label="Repeat this section",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.assignment_type == PracticeAssignmentType.repeat
        assert assignment.status == PracticeAssignmentStatus.ready

    def test_assemble_review_reference_as_review(self):
        action = make_action(
            action_type=FeedbackActionType.review_reference,
            label="Review the reference",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.assignment_type == PracticeAssignmentType.review
        assert assignment.status == PracticeAssignmentStatus.ready

    def test_assemble_retry_section_assignment(self):
        action = make_action(
            action_type=FeedbackActionType.retry_section,
            label="Retry the marked section",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.assignment_type == PracticeAssignmentType.retry_section
        assert assignment.status == PracticeAssignmentStatus.ready

    def test_assemble_isolate_assignment(self):
        action = make_action(
            action_type=FeedbackActionType.isolate,
            label="Isolate the difficult passage",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.assignment_type == PracticeAssignmentType.isolate
        assert assignment.status == PracticeAssignmentStatus.ready


class TestAssembleDrillAssignments:
    """Test assembly of drill-backed assignments."""

    def test_assemble_resolved_drill_assignment(self):
        finding = make_finding(code=DiagnosisCode.TIMING_GRID_DEVIATION)
        action = make_action(
            action_type=FeedbackActionType.assign_drill,
            label="Practice timing drill",
        )
        drill_result = make_drill_result(
            resolved=True,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            drill_id="timing_grid_quarter_note_reset_v1",
            drill_title="Quarter Note Timing Reset",
        )

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
            drill_resolution=drill_result,
        )

        assert assignment.assignment_type == PracticeAssignmentType.drill
        assert assignment.status == PracticeAssignmentStatus.ready
        assert assignment.drill is not None
        assert assignment.drill.drill_id == "timing_grid_quarter_note_reset_v1"
        assert assignment.title == "Quarter Note Timing Reset"
        assert "description" in assignment.instructions.lower() or len(assignment.instructions) > 0

    def test_assemble_unresolved_drill_when_resolution_fails(self):
        action = make_action(
            action_type=FeedbackActionType.assign_drill,
            label="Practice drill",
            rationale="A drill for this issue",
        )
        drill_result = make_drill_result(
            resolved=False,
            reason="no_matching_drill",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
            drill_resolution=drill_result,
        )

        assert assignment.assignment_type == PracticeAssignmentType.unresolved
        assert assignment.status == PracticeAssignmentStatus.unresolved
        assert assignment.reason == "no_matching_drill"
        assert assignment.drill is None
        assert assignment.params.get("drill_resolution_reason") == "no_matching_drill"

    def test_assemble_unresolved_drill_when_resolution_missing(self):
        action = make_action(
            action_type=FeedbackActionType.assign_drill,
            label="Practice drill",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
            drill_resolution=None,
        )

        assert assignment.assignment_type == PracticeAssignmentType.unresolved
        assert assignment.status == PracticeAssignmentStatus.unresolved
        assert assignment.reason == "missing_drill_resolution"
        assert assignment.drill is None


class TestAssignmentIdGeneration:
    """Test assignment ID auto-generation."""

    def test_auto_generates_with_pa_prefix(self):
        action = make_action()

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.id is not None
        assert assignment.id.startswith("pa_")
        assert len(assignment.id) == 15  # "pa_" + 12 hex chars

    def test_generates_unique_ids(self):
        action = make_action()

        ids = [
            assemble_practice_assignment(
                finding=None,
                recommendation=action,
            ).id
            for _ in range(50)
        ]

        assert len(set(ids)) == 50


class TestDiagnosisCodePropagation:
    """Test diagnosis code propagation."""

    def test_propagates_from_explicit_arg(self):
        action = make_action()
        finding = make_finding(code=DiagnosisCode.WRONG_NOTE)

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
            diagnosis_code=DiagnosisCode.PITCH_DEVIATION,
        )

        # Explicit arg takes precedence
        assert assignment.diagnosis_code == DiagnosisCode.PITCH_DEVIATION

    def test_falls_back_to_finding_code(self):
        action = make_action()
        finding = make_finding(code=DiagnosisCode.DIM_ORBIT_VIOLATION)

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
        )

        assert assignment.diagnosis_code == DiagnosisCode.DIM_ORBIT_VIOLATION

    def test_none_when_no_source(self):
        action = make_action()

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.diagnosis_code is None


class TestLinkagePropagation:
    """Test linkage ID propagation."""

    def test_finding_id_propagates(self):
        finding = make_finding(finding_id="finding_abc")
        action = make_action()

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
        )

        assert assignment.finding_id == "finding_abc"

    def test_recommendation_set_id_propagates(self):
        action = make_action()

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
            recommendation_set_id="rec_set_xyz",
        )

        assert assignment.recommendation_id == "rec_set_xyz"

    def test_target_span_propagates_from_finding(self):
        span = TargetSpan(start_time_sec=5.0, end_time_sec=10.0, bar=2)
        finding = make_finding(target_span=span)
        action = make_action()

        assignment = assemble_practice_assignment(
            finding=finding,
            recommendation=action,
        )

        assert assignment.target_span is not None
        assert assignment.target_span.bar == 2
        assert assignment.target_span.start_time_sec == 5.0


class TestRankingMetadataPropagation:
    """Test ranking metadata propagation."""

    def test_priority_propagates_from_recommendation(self):
        action = make_action(priority=5)

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.priority == 5

    def test_rank_score_propagates_from_personalized_rank_score(self):
        action = make_action(params={"personalized_rank_score": 0.85})

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.rank_score == 0.85

    def test_rank_score_falls_back_to_rank_score(self):
        action = make_action(params={"rank_score": 0.75})

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.rank_score == 0.75

    def test_personalized_rank_score_takes_precedence(self):
        action = make_action(params={
            "personalized_rank_score": 0.90,
            "rank_score": 0.70,
        })

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.rank_score == 0.90


class TestParamsCopying:
    """Test that params are copied, not mutated."""

    def test_params_are_copied(self):
        original_params = {"tempo": 80, "bars": 4}
        action = make_action(params=original_params)

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        # Params should be in assignment
        assert assignment.params.get("tempo") == 80
        # Original should not be mutated
        assert action.params == {"tempo": 80, "bars": 4}

    def test_rank_score_params_not_in_final_params(self):
        action = make_action(params={
            "tempo": 80,
            "personalized_rank_score": 0.85,
            "rank_score": 0.75,
        })

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        # Rank scores should be extracted, not in params
        assert "personalized_rank_score" not in assignment.params
        assert "rank_score" not in assignment.params
        assert assignment.params.get("tempo") == 80


class TestBatchAssembly:
    """Test batch assembly behavior."""

    def test_creates_assignments_for_all_actions(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="Slow"),
            make_action(FeedbackActionType.repeat, label="Repeat"),
            make_action(FeedbackActionType.isolate, label="Isolate"),
        ]
        rec_set = make_rec_set(actions)

        result = assemble_practice_assignments(
            recommendation_sets=[rec_set],
        )

        assert len(result.assignments) == 3

    def test_matches_drill_result_by_diagnosis_code_and_action_type(self):
        actions = [
            make_action(FeedbackActionType.assign_drill, label="Timing drill"),
        ]
        rec_set = make_rec_set(
            actions,
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )
        drill_result = make_drill_result(
            resolved=True,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            drill_id="timing_drill_v1",
        )

        result = assemble_practice_assignments(
            recommendation_sets=[rec_set],
            drill_results=[drill_result],
        )

        assert len(result.assignments) == 1
        assert result.assignments[0].drill is not None
        assert result.assignments[0].drill.drill_id == "timing_drill_v1"

    def test_handles_missing_findings(self):
        actions = [make_action(FeedbackActionType.slow_down)]
        rec_set = make_rec_set(actions)

        result = assemble_practice_assignments(
            findings=None,
            recommendation_sets=[rec_set],
        )

        assert len(result.assignments) == 1
        assert result.assignments[0].finding_id is None

    def test_matches_finding_by_code(self):
        finding = make_finding(
            code=DiagnosisCode.TIMING_GRID_DEVIATION,
            finding_id="matched_finding",
        )
        actions = [make_action(FeedbackActionType.slow_down)]
        rec_set = make_rec_set(
            actions,
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )

        result = assemble_practice_assignments(
            findings=[finding],
            recommendation_sets=[rec_set],
        )

        assert result.assignments[0].finding_id == "matched_finding"

    def test_returns_expected_count(self):
        rec_sets = [
            make_rec_set([
                make_action(FeedbackActionType.slow_down),
                make_action(FeedbackActionType.repeat),
            ]),
            make_rec_set([
                make_action(FeedbackActionType.isolate),
            ]),
        ]

        result = assemble_practice_assignments(
            recommendation_sets=rec_sets,
        )

        assert len(result.assignments) == 3

    def test_preserves_action_order(self):
        actions = [
            make_action(FeedbackActionType.slow_down, label="First"),
            make_action(FeedbackActionType.repeat, label="Second"),
            make_action(FeedbackActionType.isolate, label="Third"),
        ]
        rec_set = make_rec_set(actions)

        result = assemble_practice_assignments(
            recommendation_sets=[rec_set],
        )

        assert result.assignments[0].title == "First"
        assert result.assignments[1].title == "Second"
        assert result.assignments[2].title == "Third"


class TestAssembledPracticeAssignmentSetOutput:
    """Test that batch assembly returns correct output type."""

    def test_returns_assignment_set(self):
        rec_set = make_rec_set([make_action()])

        result = assemble_practice_assignments(
            recommendation_sets=[rec_set],
        )

        assert isinstance(result, AssembledPracticeAssignmentSet)
        assert result.source == "practice_assignment_assembler"
        assert result.version == "0.1"

    def test_empty_recommendation_sets(self):
        result = assemble_practice_assignments(
            recommendation_sets=[],
        )

        assert len(result.assignments) == 0


class TestInstructionsFallback:
    """Test instructions fallback behavior."""

    def test_uses_rationale_when_available(self):
        action = make_action(
            label="Do something",
            rationale="Detailed explanation of what to do",
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.instructions == "Detailed explanation of what to do"

    def test_falls_back_to_label_when_no_rationale(self):
        action = make_action(
            label="Do this thing",
            rationale=None,
        )

        assignment = assemble_practice_assignment(
            finding=None,
            recommendation=action,
        )

        assert assignment.instructions == "Do this thing"


class TestIntegration:
    """Integration tests for full assembly flow."""

    def test_full_pipeline_with_drill(self):
        # Create finding
        finding = CoachFinding(
            id="finding_timing_001",
            type="timing",
            severity="primary",
            interpretation="Timing is off",
            code=DiagnosisCode.TIMING_GRID_DEVIATION,
            target_span=TargetSpan(start_time_sec=5.0, end_time_sec=10.0),
        )

        # Create recommendation set
        rec_set = ActionRecommendationSet(
            id="rec_set_001",
            finding_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            finding_id="finding_timing_001",
            actions=[
                RecommendedAction(
                    action_type=FeedbackActionType.slow_down,
                    label="Reduce tempo",
                    rationale="Slow down by 10 BPM",
                    priority=1,
                ),
                RecommendedAction(
                    action_type=FeedbackActionType.assign_drill,
                    label="Practice timing",
                    rationale="Work on quarter notes",
                    priority=2,
                    params={"personalized_rank_score": 0.92},
                ),
            ],
        )

        # Create drill result
        drill_result = DrillResolutionResult(
            resolved=True,
            request=DrillResolutionRequest(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                action_type=FeedbackActionType.assign_drill,
            ),
            drill=DrillReference(
                drill_id="timing_grid_quarter_note_reset_v1",
                title="Quarter Note Timing Reset",
                description="Reset timing accuracy with quarter notes",
            ),
        )

        # Assemble assignments
        result = assemble_practice_assignments(
            findings=[finding],
            recommendation_sets=[rec_set],
            drill_results=[drill_result],
        )

        # Verify
        assert len(result.assignments) == 2

        # First: slow_down
        slow_down = result.assignments[0]
        assert slow_down.assignment_type == PracticeAssignmentType.slow_down
        assert slow_down.status == PracticeAssignmentStatus.ready
        assert slow_down.finding_id == "finding_timing_001"
        assert slow_down.recommendation_id == "rec_set_001"
        assert slow_down.target_span is not None

        # Second: drill
        drill = result.assignments[1]
        assert drill.assignment_type == PracticeAssignmentType.drill
        assert drill.status == PracticeAssignmentStatus.ready
        assert drill.drill is not None
        assert drill.drill.drill_id == "timing_grid_quarter_note_reset_v1"
        assert drill.rank_score == 0.92
        assert drill.priority == 2
