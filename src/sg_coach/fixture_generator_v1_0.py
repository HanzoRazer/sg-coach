"""
v1.0 Fixture Generator: Library wrapper for golden fixture generation.

Provides a clean API for other tooling (CI, scripts, future golden builder).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from .golden_update_v1_0 import _produce_assignment_json


def generate_assignment_fixture(vector_dir: Path, *, seed: int | None = None) -> Optional[Dict[str, Any]]:
    """
    Generate the expected assignment fixture for a single vector directory.
    Writes are not performed here; caller decides persistence.
    
    Returns None if the vector doesn't have required fixtures.
    """
    return _produce_assignment_json(vector_dir, seed=seed)


__all__ = [
    "generate_assignment_fixture",
]
