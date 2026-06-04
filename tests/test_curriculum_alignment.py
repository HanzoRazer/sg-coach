"""
Tests for Curriculum Alignment builders.

Sprint 14: Tests for goal-driven curriculum alignment and assignment selection.
Sprint 21: Updated to use sg-curriculum as canonical authority.
"""
import pytest

from sg_coach.curriculum_alignment import (
    align_goal_to_curriculum,
    build_goal_driven_assignment,
    build_goal_driven_assignments,
    curriculum_reference_to_drill_reference,
)
from sg_curriculum import DEFAULT_CURRICULUM_REGISTRY
from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.curriculum_alignment import (
    CurriculumAlignmentRequest,
    CurriculumAlignmentResult,
    CurriculumContentType,
    CurriculumReference,
)
from sg_spec.schemas.drill_resolution import DrillDifficulty, DrillReference
from sg_spec.schemas.feedback_vocabulary import FeedbackActionType
from sg_spec.schemas.goal_tracking import GoalStatus, PracticeGoal
from sg_spec.schemas.practice_assignment import (
    AssembledPracticeAssignment,
    PracticeAssignmentStatus,
    PracticeAssignmentType,
)


def make_goal(
    diagnosis_code: DiagnosisCode = DiagnosisCode.TIMING_GRID_DEVIATION,
    goal_id: str | None = "goal_timing_grid_deviation",
    status: GoalStatus = GoalStatus.active,
) -> PracticeGoal:
    """Helper to create test goal."""
    return PracticeGoal(
        id=goal_id,
        diagnosis_code=diagnosis_code,
        title="Test Goal",
        description="Test description",
        status=status,
    )


class TestDefaultRegistry:
    """Test DEFAULT_CURRICULUM_REGISTRY from sg-curriculum."""

    def test_contains_dim_orbit_violation(self):
        assert DiagnosisCode.DIM_ORBIT_VIOLATION in DEFAULT_CURRICULUM_REGISTRY

    def test_contains_timing_grid_deviation(self):
        assert DiagnosisCode.TIMING_GRID_DEVIATION in DEFAULT_CURRICULUM_REGISTRY

    def test_contains_wrong_note(self):
        assert DiagnosisCode.WRONG_NOTE in DEFAULT_CURRICULUM_REGISTRY

    def test_contains_pitch_deviation(self):
        assert DiagnosisCode.PITCH_DEVIATION in DEFAULT_CURRICULUM_REGISTRY

    def test_all_references_are_drills(self):
        for code, ref in DEFAULT_CURRICULUM_REGISTRY.items():
            assert ref.content_type == CurriculumContentType.drill

    def test_all_references_have_diagnosis_code(self):
        for code, ref in DEFAULT_CURRICULUM_REGISTRY.items():
            assert ref.diagnosis_code == code

    def test_all_references_have_content_id(self):
        for code, ref in DEFAULT_CURRICULUM_REGISTRY.items():
            assert len(ref.content_id) > 0

    def test_all_references_have_title(self):
        for code, ref in DEFAULT_CURRICULUM_REGISTRY.items():
            assert len(ref.title) > 0


class TestAlignGoalToCurriculum:
    """Test align_goal_to_curriculum function."""

    def test_resolves_known_diagnosis_code(self):
        goal = make_goal(DiagnosisCode.TIMING_GRID_DEVIATION)
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)
        assert result.resolved is True
        assert result.curriculum_reference is not None

    def test_preserves_request(self):
        goal = make_goal()
        request = CurriculumAlignmentRequest(
            goal=goal,
            preferred_difficulty=DrillDifficulty.advanced,
        )
        result = align_goal_to_curriculum(request)
        assert result.request.preferred_difficulty == DrillDifficulty.advanced
        assert result.request.goal.id == goal.id

    def test_sets_goal_id_on_reference(self):
        goal = make_goal(goal_id="goal_test_123")
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)
        assert result.curriculum_reference.goal_id == "goal_test_123"

    def test_goal_without_id_leaves_reference_goal_id_none(self):
        goal = make_goal(goal_id=None)
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)
        assert result.curriculum_reference.goal_id is None

    def test_unmapped_diagnosis_returns_unresolved(self):
        goal = PracticeGoal(
            id="goal_unknown",
            diagnosis_code=DiagnosisCode.RUSHING,
            title="Unknown Goal",
            description="No mapping",
        )
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)
        assert result.resolved is False
        assert result.curriculum_reference is None
        assert result.reason == "no_curriculum_alignment"

    def test_registry_reference_not_mutated(self):
        original_ref = DEFAULT_CURRICULUM_REGISTRY[DiagnosisCode.TIMING_GRID_DEVIATION]
        original_goal_id = original_ref.goal_id

        goal = make_goal(goal_id="goal_test_mutation")
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)

        assert result.curriculum_reference.goal_id == "goal_test_mutation"
        assert original_ref.goal_id == original_goal_id

    def test_preferred_difficulty_overrides_registry(self):
        goal = make_goal()
        request = CurriculumAlignmentRequest(
            goal=goal,
            preferred_difficulty=DrillDifficulty.advanced,
        )
        result = align_goal_to_curriculum(request)
        assert result.curriculum_reference.difficulty == DrillDifficulty.advanced

    def test_uses_custom_registry(self):
        custom_ref = CurriculumReference(
            content_id="custom_drill_v1",
            title="Custom Drill",
            content_type=CurriculumContentType.drill,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )
        custom_registry = {DiagnosisCode.TIMING_GRID_DEVIATION: custom_ref}

        goal = make_goal()
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request, registry=custom_registry)
        assert result.curriculum_reference.content_id == "custom_drill_v1"

    def test_all_layer_1_codes_resolve(self):
        layer_1_codes = [
            DiagnosisCode.DIM_ORBIT_VIOLATION,
            DiagnosisCode.TIMING_GRID_DEVIATION,
            DiagnosisCode.WRONG_NOTE,
            DiagnosisCode.PITCH_DEVIATION,
        ]
        for code in layer_1_codes:
            goal = make_goal(diagnosis_code=code, goal_id=f"goal_{code.value}")
            request = CurriculumAlignmentRequest(goal=goal)
            result = align_goal_to_curriculum(request)
            assert result.resolved is True, f"Failed for {code}"


class TestCurriculumReferenceToDrillReference:
    """Test curriculum_reference_to_drill_reference function."""

    def test_converts_drill_reference(self):
        ref = CurriculumReference(
            content_id="test_drill_v1",
            title="Test Drill",
            content_type=CurriculumContentType.drill,
            source="sg-coach",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            difficulty=DrillDifficulty.intermediate,
            tags=["timing", "test"],
            params={"tempo_bpm": 100, "description": "A test drill"},
        )
        drill = curriculum_reference_to_drill_reference(ref)
        assert isinstance(drill, DrillReference)
        assert drill.drill_id == "test_drill_v1"
        assert drill.title == "Test Drill"
        assert drill.source == "sg-coach"
        assert drill.diagnosis_code == DiagnosisCode.TIMING_GRID_DEVIATION
        assert drill.difficulty == DrillDifficulty.intermediate
        assert drill.tags == ["timing", "test"]
        assert drill.description == "A test drill"
        assert drill.action_type == FeedbackActionType.assign_drill

    def test_non_drill_raises_valueerror(self):
        ref = CurriculumReference(
            content_id="test_lesson_v1",
            title="Test Lesson",
            content_type=CurriculumContentType.lesson,
        )
        with pytest.raises(ValueError) as exc_info:
            curriculum_reference_to_drill_reference(ref)
        assert "non-drill" in str(exc_info.value).lower()

    def test_exercise_raises_valueerror(self):
        ref = CurriculumReference(
            content_id="test_exercise_v1",
            title="Test Exercise",
            content_type=CurriculumContentType.exercise,
        )
        with pytest.raises(ValueError):
            curriculum_reference_to_drill_reference(ref)

    def test_description_from_params(self):
        ref = CurriculumReference(
            content_id="test_drill_v1",
            title="Test Drill",
            content_type=CurriculumContentType.drill,
            params={"description": "Custom description"},
        )
        drill = curriculum_reference_to_drill_reference(ref)
        assert drill.description == "Custom description"

    def test_no_description_when_not_in_params(self):
        ref = CurriculumReference(
            content_id="test_drill_v1",
            title="Test Drill",
            content_type=CurriculumContentType.drill,
            params={},
        )
        drill = curriculum_reference_to_drill_reference(ref)
        assert drill.description is None


class TestBuildGoalDrivenAssignment:
    """Test build_goal_driven_assignment function."""

    def test_creates_ready_drill_assignment(self):
        goal = make_goal()
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.assignment_type == PracticeAssignmentType.drill
        assert assignment.status == PracticeAssignmentStatus.ready
        assert assignment.drill is not None

    def test_preserves_goal_id_in_params(self):
        goal = make_goal(goal_id="goal_test_123")
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.params["goal_id"] == "goal_test_123"

    def test_preserves_diagnosis_code(self):
        goal = make_goal(diagnosis_code=DiagnosisCode.WRONG_NOTE)
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.diagnosis_code == DiagnosisCode.WRONG_NOTE

    def test_unresolved_alignment_creates_unresolved_assignment(self):
        goal = PracticeGoal(
            id="goal_unmapped",
            diagnosis_code=DiagnosisCode.RUSHING,
            title="Unmapped Goal",
            description="No curriculum alignment",
        )
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.assignment_type == PracticeAssignmentType.unresolved
        assert assignment.status == PracticeAssignmentStatus.unresolved
        assert assignment.reason == "no_curriculum_alignment"

    def test_assignment_id_from_goal_id(self):
        goal = make_goal(goal_id="goal_timing_grid_deviation")
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.id == "pa_goal_timing_grid_deviation"

    def test_assignment_id_without_goal_id(self):
        goal = make_goal(
            goal_id=None,
            diagnosis_code=DiagnosisCode.WRONG_NOTE,
        )
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert assignment.id == "pa_goal_wrong_note"

    def test_instructions_reference_goal_title(self):
        goal = PracticeGoal(
            id="goal_test",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Reduce timing errors",
            description="Test",
        )
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert "Reduce timing errors" in assignment.instructions

    def test_includes_curriculum_content_id_in_params(self):
        goal = make_goal()
        request = CurriculumAlignmentRequest(goal=goal)
        alignment_result = align_goal_to_curriculum(request)

        assignment = build_goal_driven_assignment(
            goal=goal,
            alignment_result=alignment_result,
        )
        assert "curriculum_content_id" in assignment.params


class TestBuildGoalDrivenAssignments:
    """Test build_goal_driven_assignments function."""

    def test_creates_assignments_for_active_goals(self):
        goals = [
            make_goal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                goal_id="goal_1",
                status=GoalStatus.active,
            ),
            make_goal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                goal_id="goal_2",
                status=GoalStatus.active,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 2

    def test_skips_completed_goals(self):
        goals = [
            make_goal(status=GoalStatus.active),
            make_goal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                goal_id="goal_completed",
                status=GoalStatus.completed,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 1

    def test_skips_abandoned_goals(self):
        goals = [
            make_goal(status=GoalStatus.active),
            make_goal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                goal_id="goal_abandoned",
                status=GoalStatus.abandoned,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 1

    def test_includes_improving_goals(self):
        goals = [
            make_goal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                goal_id="goal_improving",
                status=GoalStatus.improving,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 1

    def test_includes_regressed_goals(self):
        goals = [
            make_goal(
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                goal_id="goal_regressed",
                status=GoalStatus.regressed,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 1

    def test_preferred_difficulty_applied(self):
        goals = [make_goal()]
        result = build_goal_driven_assignments(
            goals=goals,
            preferred_difficulty=DrillDifficulty.advanced,
        )
        assert result.assignments[0].drill.difficulty == DrillDifficulty.advanced

    def test_empty_goals_returns_empty_set(self):
        result = build_goal_driven_assignments(goals=[])
        assert len(result.assignments) == 0

    def test_all_completed_goals_returns_empty_set(self):
        goals = [
            make_goal(
                goal_id="goal_1",
                status=GoalStatus.completed,
            ),
            make_goal(
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                goal_id="goal_2",
                status=GoalStatus.completed,
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        assert len(result.assignments) == 0

    def test_uses_custom_registry(self):
        custom_ref = CurriculumReference(
            content_id="custom_drill_v1",
            title="Custom Drill",
            content_type=CurriculumContentType.drill,
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
        )
        custom_registry = {DiagnosisCode.TIMING_GRID_DEVIATION: custom_ref}

        goals = [make_goal()]
        result = build_goal_driven_assignments(
            goals=goals,
            registry=custom_registry,
        )
        assert result.assignments[0].drill.drill_id == "custom_drill_v1"


class TestBuildProgressionRecommendation:
    """Test build_progression_recommendation function (Sprint 22)."""

    def test_returns_recommendation_for_known_diagnosis(self):
        from sg_coach.curriculum_alignment import build_progression_recommendation
        from sg_spec.schemas.curriculum_progression import (
            CurriculumProgressState,
            CurriculumRecommendation,
        )

        progress = CurriculumProgressState(
            student_id="test_student",
            completed_content_ids=[],
        )
        rec = build_progression_recommendation(
            diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
            progress_state=progress,
        )
        assert rec is not None
        assert isinstance(rec, CurriculumRecommendation)
        assert rec.content_id == "diminished_orbit_navigation_foundation_v1"

    def test_returns_none_for_unknown_diagnosis(self):
        from sg_coach.curriculum_alignment import build_progression_recommendation
        from sg_spec.schemas.curriculum_progression import CurriculumProgressState

        progress = CurriculumProgressState(
            student_id="test_student",
            completed_content_ids=[],
        )
        rec = build_progression_recommendation(
            diagnosis_code=DiagnosisCode.RUSHING,
            progress_state=progress,
        )
        assert rec is None

    def test_returns_none_when_all_completed(self):
        from sg_coach.curriculum_alignment import build_progression_recommendation
        from sg_spec.schemas.curriculum_progression import CurriculumProgressState

        progress = CurriculumProgressState(
            student_id="test_student",
            completed_content_ids=["diminished_orbit_navigation_foundation_v1"],
        )
        rec = build_progression_recommendation(
            diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
            progress_state=progress,
        )
        assert rec is None

    def test_prerequisite_satisfied_for_foundation(self):
        from sg_coach.curriculum_alignment import build_progression_recommendation
        from sg_spec.schemas.curriculum_progression import CurriculumProgressState

        progress = CurriculumProgressState(
            student_id="test_student",
            completed_content_ids=[],
        )
        rec = build_progression_recommendation(
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            progress_state=progress,
        )
        assert rec is not None
        assert rec.prerequisite_satisfied is True
        assert rec.recommended_next is True


class TestSchemaExports:
    """Test that curriculum alignment functions are exported correctly."""

    def test_import_from_sg_coach(self):
        from sg_coach import (
            align_goal_to_curriculum,
            build_goal_driven_assignment,
            build_goal_driven_assignments,
            curriculum_reference_to_drill_reference,
        )
        assert align_goal_to_curriculum is not None
        assert curriculum_reference_to_drill_reference is not None
        assert build_goal_driven_assignment is not None
        assert build_goal_driven_assignments is not None

    def test_import_build_progression_recommendation(self):
        from sg_coach import build_progression_recommendation
        assert build_progression_recommendation is not None
