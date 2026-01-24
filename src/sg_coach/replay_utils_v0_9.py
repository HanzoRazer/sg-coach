"""
v0.9 Replay Utilities: Structured diff reporting and seedable timestamps.

Provides:
- ReplayDiffV0_9: structured mismatch report with JSON diff
- json_diff(): unified diff of pretty-printed JSON
- seeded_utc_iso(): deterministic timestamps for testing
- normalize_assignment_for_compare(): stabilize non-deterministic fields
"""
from __future__ import annotations

import datetime as _dt
import json
import difflib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ReplayDiffV0_9:
    """Structured replay result with optional diff on mismatch."""

    ok: bool
    reason: str
    produced: Dict[str, Any] | None = None
    expected: Dict[str, Any] | None = None
    diff_text: str | None = None


def _json_pretty(x: Dict[str, Any]) -> str:
    return json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def json_diff(produced: Dict[str, Any], expected: Dict[str, Any], context: int = 3) -> str:
    """
    Unified diff of pretty-printed JSON (stable ordering).
    """
    a = _json_pretty(expected).splitlines(keepends=True)
    b = _json_pretty(produced).splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            a,
            b,
            fromfile="expected.json",
            tofile="produced.json",
            n=context,
        )
    )


def seeded_utc_iso(seed: int) -> str:
    """
    Deterministic UTC timestamp derived from seed.
    Useful for tests when fixtures don't pin created_at_utc.

    Base: 2000-01-01T00:00:00Z + seed seconds.
    """
    base = _dt.datetime(2000, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    ts = base + _dt.timedelta(seconds=int(seed))
    return ts.isoformat().replace("+00:00", "Z")


def normalize_assignment_for_compare(
    produced: Dict[str, Any],
    expected: Dict[str, Any],
    *,
    seed: int | None = None,
) -> Dict[str, Any]:
    """
    Normalize non-deterministic fields so comparisons are stable.

    Rules:
      - If expected includes created_at_utc: force produced to match it (fixture-authoritative)
      - Else if seed is provided: stamp produced.created_at_utc deterministically

    Provenance rule (v1.1):
      - If expected includes _fixture, copy it into produced so provenance stamps never fail gates.
    """
    out = dict(produced)

    if "created_at_utc" in expected:
        out["created_at_utc"] = expected["created_at_utc"]
    elif seed is not None:
        out["created_at_utc"] = seeded_utc_iso(seed)

    if "_fixture" in expected:
        out["_fixture"] = expected["_fixture"]

    return out


__all__ = [
    "ReplayDiffV0_9",
    "json_diff",
    "seeded_utc_iso",
    "normalize_assignment_for_compare",
]
