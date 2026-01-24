# sg_coach.fixtures — re-exported from sg_spec.ai.coach.fixtures
"""Backward compatibility stub. Use sg_spec.ai.coach.fixtures directly."""
import sg_spec.ai.coach.fixtures as _fx
from pathlib import Path

# Expose the golden fixtures path
GOLDEN_ROOT = Path(_fx.__file__).parent / "golden"
