"""
Tests for v1.2 meta gate and fixture provenance policy.
"""
from pathlib import Path
import json

from sg_coach.meta_gate_v1_2 import run_gates, check_meta_required, check_fixture_provenance
from sg_coach.versioning_v1_2 import CURRENT_GENERATOR_VERSION


def test_meta_gate_fails_missing_meta(tmp_path: Path):
    """Test that gate fails when vector_meta_v1.json is missing."""
    golden = tmp_path / "golden"
    v = golden / "vector_000"
    v.mkdir(parents=True, exist_ok=True)

    ok, failures = run_gates(golden)
    assert not ok
    assert any(f.code == "META_REQUIRED" for f in failures)


def test_meta_gate_fails_missing_provenance(tmp_path: Path):
    """Test that gate fails when assignment lacks _fixture."""
    golden = tmp_path / "golden"
    v = golden / "vector_000"
    v.mkdir(parents=True, exist_ok=True)

    # Create meta so META_REQUIRED passes
    meta = {"schema_id": "sg_coach_golden_vector_meta", "schema_version": "v1", "seed": 123}
    (v / "vector_meta_v1.json").write_text(json.dumps(meta), encoding="utf-8")

    # Create assignment without _fixture
    assignment = {"tempo_nudge_bpm": 0, "density_cap": 0.5}
    (v / "assignment_v0_6.json").write_text(json.dumps(assignment), encoding="utf-8")

    ok, failures = run_gates(golden)
    assert not ok
    assert any(f.code == "FIXTURE_PROVENANCE_MISSING" for f in failures)


def test_meta_gate_fails_version_mismatch(tmp_path: Path):
    """Test that gate fails when generator_version doesn't match."""
    golden = tmp_path / "golden"
    v = golden / "vector_000"
    v.mkdir(parents=True, exist_ok=True)

    # Create meta
    meta = {"schema_id": "sg_coach_golden_vector_meta", "schema_version": "v1", "seed": 123}
    (v / "vector_meta_v1.json").write_text(json.dumps(meta), encoding="utf-8")

    # Create assignment with old version
    assignment = {
        "tempo_nudge_bpm": 0,
        "density_cap": 0.5,
        "_fixture": {"generator": "sg-coach", "generator_version": "0.9"},
    }
    (v / "assignment_v0_6.json").write_text(json.dumps(assignment), encoding="utf-8")

    ok, failures = run_gates(golden)
    assert not ok
    assert any(f.code == "FIXTURE_VERSION_MISMATCH" for f in failures)


def test_meta_gate_passes_when_valid(tmp_path: Path):
    """Test that gate passes when all requirements are met."""
    golden = tmp_path / "golden"
    v = golden / "vector_000"
    v.mkdir(parents=True, exist_ok=True)

    # Create valid meta
    meta = {"schema_id": "sg_coach_golden_vector_meta", "schema_version": "v1", "seed": 123}
    (v / "vector_meta_v1.json").write_text(json.dumps(meta), encoding="utf-8")

    # Create assignment with current version
    assignment = {
        "tempo_nudge_bpm": 0,
        "density_cap": 0.5,
        "_fixture": {"generator": "sg-coach", "generator_version": CURRENT_GENERATOR_VERSION},
    }
    (v / "assignment_v0_6.json").write_text(json.dumps(assignment), encoding="utf-8")

    ok, failures = run_gates(golden)
    assert ok
    assert len(failures) == 0
