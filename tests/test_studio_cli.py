"""
Tests for Studio CLI commands.

Sprint 20: Multi-student studio support CLI.
"""
import json
from pathlib import Path

import pytest

from sg_coach.cli import main


class TestStudioCreate:
    """Tests for studio create command."""

    def test_create_studio(self, tmp_path):
        roster = tmp_path / "roster.jsonl"
        result = main([
            "studio", "create",
            "--roster", str(roster),
            "--name", "Test Studio",
        ])
        assert result == 0
        assert roster.exists()

    def test_create_studio_with_id(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        result = main([
            "studio", "create",
            "--roster", str(roster),
            "--name", "Custom Studio",
            "--studio-id", "studio_custom123",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["studio_id"] == "studio_custom123"
        assert output["name"] == "Custom Studio"

    def test_create_studio_pretty(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        result = main([
            "studio", "create",
            "--roster", str(roster),
            "--name", "Pretty Studio",
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out  # Pretty printed


class TestStudioAddStudent:
    """Tests for studio add-student command."""

    def test_add_student(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-student",
            "--roster", str(roster),
            "--name", "Alice",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["display_name"] == "Alice"
        assert output["active"] is True
        assert output["student_id"].startswith("student_")

    def test_add_student_with_id(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-student",
            "--roster", str(roster),
            "--name", "Bob",
            "--student-id", "student_bob123",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["student_id"] == "student_bob123"

    def test_add_student_with_notes(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-student",
            "--roster", str(roster),
            "--name", "Carol",
            "--notes", "Beginner guitarist",
        ])
        assert result == 0

    def test_add_student_roster_not_found(self, tmp_path, capsys):
        result = main([
            "studio", "add-student",
            "--roster", str(tmp_path / "nonexistent.jsonl"),
            "--name", "Student",
        ])
        assert result == 1

        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_add_student_multiple_studios_no_id(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio 1"])
        main(["studio", "create", "--roster", str(roster), "--name", "Studio 2"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-student",
            "--roster", str(roster),
            "--name", "Student",
        ])
        assert result == 1

        captured = capsys.readouterr()
        assert "Multiple studios" in captured.err


class TestStudioAddTeacher:
    """Tests for studio add-teacher command."""

    def test_add_teacher(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-teacher",
            "--roster", str(roster),
            "--name", "Mr. Smith",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["display_name"] == "Mr. Smith"
        assert output["active"] is True
        assert output["teacher_id"].startswith("teacher_")

    def test_add_teacher_with_id(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-teacher",
            "--roster", str(roster),
            "--name", "Ms. Jones",
            "--teacher-id", "teacher_jones",
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["teacher_id"] == "teacher_jones"


class TestStudioListStudents:
    """Tests for studio list-students command."""

    def test_list_students_empty(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "list-students",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 0
        assert output["students"] == []

    def test_list_students_with_data(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        main(["studio", "add-student", "--roster", str(roster), "--name", "Alice"])
        main(["studio", "add-student", "--roster", str(roster), "--name", "Bob"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "list-students",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 2

    def test_list_students_roster_not_found(self, tmp_path, capsys):
        result = main([
            "studio", "list-students",
            "--roster", str(tmp_path / "nonexistent.jsonl"),
        ])
        assert result == 1


class TestStudioListTeachers:
    """Tests for studio list-teachers command."""

    def test_list_teachers_empty(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "list-teachers",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 0

    def test_list_teachers_with_data(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        main(["studio", "add-teacher", "--roster", str(roster), "--name", "Mr. Smith"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "list-teachers",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 1


class TestStudioOverview:
    """Tests for studio overview command."""

    def test_overview_empty(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Empty Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "overview",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["name"] == "Empty Studio"
        assert output["active_student_count"] == 0
        assert output["active_teacher_count"] == 0

    def test_overview_with_members(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Full Studio"])
        main(["studio", "add-student", "--roster", str(roster), "--name", "Alice"])
        main(["studio", "add-student", "--roster", str(roster), "--name", "Bob"])
        main(["studio", "add-teacher", "--roster", str(roster), "--name", "Mr. Smith"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "overview",
            "--roster", str(roster),
        ])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["active_student_count"] == 2
        assert output["active_teacher_count"] == 1
        assert len(output["students"]) == 2
        assert len(output["teachers"]) == 1

    def test_overview_roster_not_found(self, tmp_path, capsys):
        result = main([
            "studio", "overview",
            "--roster", str(tmp_path / "nonexistent.jsonl"),
        ])
        assert result == 1

    def test_overview_pretty(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main(["studio", "create", "--roster", str(roster), "--name", "Studio"])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "overview",
            "--roster", str(roster),
            "--pretty",
        ])
        assert result == 0

        captured = capsys.readouterr()
        assert "\n" in captured.out


class TestStudioWithExplicitStudioId:
    """Tests for commands with explicit studio-id."""

    def test_add_student_with_studio_id(self, tmp_path, capsys):
        roster = tmp_path / "roster.jsonl"
        main([
            "studio", "create",
            "--roster", str(roster),
            "--name", "Studio 1",
            "--studio-id", "studio_001",
        ])
        main([
            "studio", "create",
            "--roster", str(roster),
            "--name", "Studio 2",
            "--studio-id", "studio_002",
        ])
        capsys.readouterr()  # Clear

        result = main([
            "studio", "add-student",
            "--roster", str(roster),
            "--studio-id", "studio_001",
            "--name", "Alice",
        ])
        assert result == 0
        capsys.readouterr()  # Clear

        # Verify student is in studio_001
        result = main([
            "studio", "list-students",
            "--roster", str(roster),
            "--studio-id", "studio_001",
        ])
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 1

        # Verify studio_002 is empty
        result = main([
            "studio", "list-students",
            "--roster", str(roster),
            "--studio-id", "studio_002",
        ])
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["count"] == 0
