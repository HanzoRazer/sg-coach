"""
Golden Fixture Tests — Validate pipeline reproducibility.

Sprint 15: MVP baseline hardening.

Golden fixtures ensure the coaching pipeline produces consistent,
reproducible outputs for known inputs. This catches regression in
coaching logic across code changes.
"""
import json
from pathlib import Path

import pytest

from sg_coach.runtime_pipeline import (
    normalize_runtime_output,
    run_fixture_pipeline,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MIDI_DIR = FIXTURES_DIR / "midi"
GOLDEN_DIR = FIXTURES_DIR / "golden"


def get_midi_fixtures() -> list[Path]:
    """Get all MIDI fixture files."""
    if not MIDI_DIR.exists():
        return []
    return sorted(MIDI_DIR.glob("*.json"))


def get_golden_path(midi_path: Path) -> Path:
    """Get golden output path for a MIDI fixture."""
    return GOLDEN_DIR / f"{midi_path.stem}_golden.json"


def generate_golden_fixture(midi_path: Path) -> dict:
    """Generate normalized golden output for a MIDI fixture."""
    result = run_fixture_pipeline(midi_path)
    return normalize_runtime_output(result)


def load_golden_fixture(golden_path: Path) -> dict | None:
    """Load golden fixture if it exists."""
    if not golden_path.exists():
        return None
    with open(golden_path) as f:
        return json.load(f)


def save_golden_fixture(golden_path: Path, data: dict) -> None:
    """Save golden fixture to file."""
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    with open(golden_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


class TestGoldenFixtures:
    """Test that pipeline outputs match golden fixtures."""

    @pytest.mark.parametrize("midi_path", get_midi_fixtures(), ids=lambda p: p.stem)
    def test_fixture_matches_golden(self, midi_path: Path):
        """Pipeline output should match stored golden fixture."""
        golden_path = get_golden_path(midi_path)
        golden = load_golden_fixture(golden_path)

        if golden is None:
            pytest.skip(f"Golden fixture not yet generated: {golden_path.name}")

        result = run_fixture_pipeline(midi_path)
        normalized = normalize_runtime_output(result)

        assert normalized == golden, (
            f"Pipeline output differs from golden fixture.\n"
            f"MIDI: {midi_path.name}\n"
            f"Golden: {golden_path.name}\n"
            f"Run 'pytest --generate-golden' to regenerate."
        )

    def test_all_midi_fixtures_have_golden(self):
        """Ensure all MIDI fixtures have corresponding golden files."""
        midi_fixtures = get_midi_fixtures()
        missing = []

        for midi_path in midi_fixtures:
            golden_path = get_golden_path(midi_path)
            if not golden_path.exists():
                missing.append(midi_path.name)

        if missing:
            pytest.skip(
                f"Missing golden fixtures for: {', '.join(missing)}. "
                f"Run generate_golden_fixtures() to create them."
            )


class TestGoldenFixtureGeneration:
    """Tests for golden fixture generation utilities."""

    def test_generate_golden_returns_dict(self):
        """generate_golden_fixture should return normalized dict."""
        midi_fixtures = get_midi_fixtures()
        if not midi_fixtures:
            pytest.skip("No MIDI fixtures available")

        result = generate_golden_fixture(midi_fixtures[0])
        assert isinstance(result, dict)

    def test_golden_output_is_normalized(self):
        """Golden output should have volatile fields removed."""
        midi_fixtures = get_midi_fixtures()
        if not midi_fixtures:
            pytest.skip("No MIDI fixtures available")

        result = generate_golden_fixture(midi_fixtures[0])

        def check_no_volatile(obj):
            if isinstance(obj, dict):
                assert "created_at" not in obj
                assert "updated_at" not in obj
                for v in obj.values():
                    check_no_volatile(v)
            elif isinstance(obj, list):
                for item in obj:
                    check_no_volatile(item)

        check_no_volatile(result)

    def test_golden_output_is_deterministic(self):
        """Same input should produce identical golden output."""
        midi_fixtures = get_midi_fixtures()
        if not midi_fixtures:
            pytest.skip("No MIDI fixtures available")

        midi_path = midi_fixtures[0]
        result1 = generate_golden_fixture(midi_path)
        result2 = generate_golden_fixture(midi_path)

        assert result1 == result2


def generate_all_golden_fixtures(overwrite: bool = False) -> list[str]:
    """
    Generate golden fixtures for all MIDI fixtures.

    Parameters
    ----------
    overwrite:
        If True, regenerate even if golden exists.

    Returns
    -------
    List of generated fixture names.
    """
    generated = []

    for midi_path in get_midi_fixtures():
        golden_path = get_golden_path(midi_path)

        if golden_path.exists() and not overwrite:
            continue

        data = generate_golden_fixture(midi_path)
        save_golden_fixture(golden_path, data)
        generated.append(golden_path.name)

    return generated


if __name__ == "__main__":
    print("Generating golden fixtures...")
    generated = generate_all_golden_fixtures(overwrite=True)
    if generated:
        print(f"Generated: {', '.join(generated)}")
    else:
        print("No fixtures generated (all exist or no MIDI fixtures found)")
