"""
v1.2 Versioning: Single source of truth for fixture generator version.

Bump CURRENT_GENERATOR_VERSION when you intentionally change fixture generation semantics.
"""
from __future__ import annotations

# Single source of truth for fixture generator version.
# Bump this when you intentionally change fixture generation semantics.
CURRENT_GENERATOR_VERSION = "1.2"


__all__ = [
    "CURRENT_GENERATOR_VERSION",
]
