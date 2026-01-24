"""
Tests for v1.1 vector metadata and fixture provenance stamping.
"""
from pathlib import Path
import json

from sg_coach.golden_meta_v1_1 import META_FILENAME, read_vector_meta, ensure_vector_meta
from sg_coach.golden_update_v1_0 import update_goldens
from sg_coach.versioning_v1_2 import CURRENT_GENERATOR_VERSION


def test_vector_meta_created_and_provenance_stamped(tmp_path: Path):
    """Test that vector meta is created and assignment gets provenance stamp."""
    # Copy one vector into tmp workspace
    root = Path(__file__).resolve().parents[1]
    vec_src = root / "src" / "sg_coach" / "fixtures" / "golden" / "vector_006"
    vec = tmp_path / "vector_006"
    vec.mkdir(parents=True, exist_ok=True)

    for f in vec_src.glob("*"):
        if f.is_file():
            (vec / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

    # Ensure meta created
    m = ensure_vector_meta(vec, seed=777, now_utc_iso="2026-01-01T00:00:00Z", notes="test")
    assert (vec / META_FILENAME).exists()
    m2 = read_vector_meta(vec)
    assert m2 is not None
    assert m2.seed == 777

    # Force a mismatch by modifying the expected assignment
    # This will cause update_goldens to regenerate with provenance
    af = vec / "assignment_v0_6.json"
    existing = json.loads(af.read_text(encoding="utf-8"))
    existing["_force_mismatch"] = True
    af.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # Run update in a golden root wrapper so it can find vector_* dirs
    golden_root = tmp_path
    res = update_goldens(golden_root, seed=123, allow_update=True)
    assert res.total >= 1
    assert res.updated >= 1  # Should have updated at least one

    # Verify assignment fixture has _fixture provenance
    data = json.loads(af.read_text(encoding="utf-8"))
    assert "_fixture" in data
    assert data["_fixture"]["generator"] == "sg-coach"
    assert data["_fixture"]["generator_version"] == CURRENT_GENERATOR_VERSION
    # Seed should be from vector_meta (777), not CLI seed (123)
    assert data["_fixture"]["seed_used"] == 777
    # The _force_mismatch key should be gone (regenerated)
    assert "_force_mismatch" not in data
