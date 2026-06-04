"""
Tests for sg-curriculum integration.

Sprint 21: Validate sg-coach correctly uses sg-curriculum as canonical authority.
Sprint 22: Updated version check for progression engine.
"""
import pytest

from sg_spec.schemas.adaptive_feedback import DiagnosisCode
from sg_spec.schemas.curriculum_alignment import CurriculumAlignmentRequest
from sg_spec.schemas.goal_tracking import PracticeGoal

from sg_coach.curriculum_alignment import (
    align_goal_to_curriculum,
    build_goal_driven_assignments,
)
from sg_curriculum import (
    CURRICULUM_VERSION,
    DEFAULT_CURRICULUM_REGISTRY,
    get_curriculum_for_diagnosis,
)


class TestCurriculumIntegration:
    """Test sg-coach integration with sg-curriculum."""

    def test_curriculum_version_accessible(self):
        assert CURRICULUM_VERSION == "0.2.0"

    def test_registry_imported_from_sg_curriculum(self):
        assert DEFAULT_CURRICULUM_REGISTRY is not None
        assert len(DEFAULT_CURRICULUM_REGISTRY) == 4

    def test_lookup_returns_same_content_as_registry(self):
        for code in DEFAULT_CURRICULUM_REGISTRY:
            refs = get_curriculum_for_diagnosis(code)
            assert len(refs) == 1
            assert refs[0].content_id == DEFAULT_CURRICULUM_REGISTRY[code].content_id

    def test_alignment_uses_sg_curriculum(self):
        goal = PracticeGoal(
            id="goal_test",
            diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
            title="Test Goal",
            description="Test",
        )
        request = CurriculumAlignmentRequest(goal=goal)
        result = align_goal_to_curriculum(request)

        assert result.resolved is True
        # Content should come from sg-curriculum
        assert result.curriculum_reference.source == "sg-curriculum"

    def test_content_ids_unchanged_after_extraction(self):
        expected_content_ids = {
            DiagnosisCode.DIM_ORBIT_VIOLATION: "diminished_orbit_navigation_foundation_v1",
            DiagnosisCode.TIMING_GRID_DEVIATION: "timing_grid_alignment_foundation_v1",
            DiagnosisCode.WRONG_NOTE: "single_note_accuracy_foundation_v1",
            DiagnosisCode.PITCH_DEVIATION: "pitch_centering_foundation_v1",
        }
        for code, expected_id in expected_content_ids.items():
            refs = get_curriculum_for_diagnosis(code)
            assert refs[0].content_id == expected_id

    def test_goal_driven_assignments_use_sg_curriculum(self):
        goals = [
            PracticeGoal(
                id="goal_1",
                diagnosis_code=DiagnosisCode.TIMING_GRID_DEVIATION,
                title="Test Goal 1",
                description="Test",
            ),
            PracticeGoal(
                id="goal_2",
                diagnosis_code=DiagnosisCode.WRONG_NOTE,
                title="Test Goal 2",
                description="Test",
            ),
        ]
        result = build_goal_driven_assignments(goals=goals)
        
        assert len(result.assignments) == 2
        for assignment in result.assignments:
            assert assignment.drill is not None
            # Verify content comes from sg-curriculum
            assert assignment.params.get("curriculum_content_id") is not None

    def test_alignment_deterministic(self):
        goal = PracticeGoal(
            id="goal_test",
            diagnosis_code=DiagnosisCode.DIM_ORBIT_VIOLATION,
            title="Test Goal",
            description="Test",
        )
        request = CurriculumAlignmentRequest(goal=goal)
        
        result1 = align_goal_to_curriculum(request)
        result2 = align_goal_to_curriculum(request)
        
        assert result1.curriculum_reference.content_id == result2.curriculum_reference.content_id
        assert result1.curriculum_reference.title == result2.curriculum_reference.title
