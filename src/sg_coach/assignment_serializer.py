"""
UUID-safe JSON serialization for OTA / firmware payloads.

Converts SessionRecord, CoachEvaluation, PracticeAssignment into
deterministic JSON with:
- UUIDs as strings
- Datetimes as ISO-8601 with 'Z' suffix
- Stable key ordering (sort_keys=True)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from .schemas import CoachEvaluation, PracticeAssignment, SessionRecord


def _iso_z(dt: datetime) -> str:
    """
    Convert datetime to an ISO-8601 string with 'Z' (UTC) suffix.
    Accepts naive UTC datetimes (common in codebases that use datetime.utcnow()).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # Use seconds precision by default; firmware generally prefers compact stability.
    s = dt.isoformat(timespec="seconds")
    return s.replace("+00:00", "Z")


def _json_safe_model_dict(model: Any) -> Dict[str, Any]:
    """
    Pydantic v2: model_dump(mode="json") converts UUID/datetime to JSON-safe types.
    We still normalize datetime formatting to Z where present.
    """
    d: Dict[str, Any] = model.model_dump(mode="json")  # type: ignore[attr-defined]

    # Normalize any well-known datetime keys to Z
    for key in ("created_at",):
        if key in d and isinstance(d[key], str):
            # If it's already Z, keep; otherwise best-effort parse is out-of-scope.
            # We only guarantee Z when inputs were datetimes.
            pass
    return d


@dataclass(frozen=True)
class FirmwareEnvelope:
    """
    OTA-friendly wrapper:
    - Adds stable kind + schema_version
    - Allows bundling multiple artifacts in one message
    """

    kind: Literal["sg_coach_bundle"] = "sg_coach_bundle"
    schema_version: str = "v1"
    created_at_utc: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "created_at": _iso_z(self.created_at_utc or datetime.now(timezone.utc)),
        }


def serialize_session(session: SessionRecord) -> Dict[str, Any]:
    """
    SessionRecord -> JSON-safe dict for storage/OTA.
    """
    d = _json_safe_model_dict(session)
    # enforce Z formatting for created_at
    if isinstance(session.created_at, datetime):
        d["created_at"] = _iso_z(session.created_at)
    return d


def serialize_evaluation(evaluation: CoachEvaluation) -> Dict[str, Any]:
    """
    CoachEvaluation -> JSON-safe dict for storage/OTA.
    """
    d = _json_safe_model_dict(evaluation)
    if isinstance(evaluation.created_at, datetime):
        d["created_at"] = _iso_z(evaluation.created_at)
    return d


def serialize_assignment(assignment: PracticeAssignment) -> Dict[str, Any]:
    """
    PracticeAssignment -> JSON-safe dict for storage/OTA.
    """
    d = _json_safe_model_dict(assignment)
    if isinstance(assignment.created_at, datetime):
        d["created_at"] = _iso_z(assignment.created_at)
    return d


def serialize_bundle(
    *,
    session: SessionRecord,
    evaluation: CoachEvaluation,
    assignment: PracticeAssignment,
    envelope: Optional[FirmwareEnvelope] = None,
) -> Dict[str, Any]:
    """
    Wrap the triad (Session -> Coach -> Assignment) into one OTA payload.
    """
    env = envelope or FirmwareEnvelope()
    return {
        **env.to_dict(),
        "session": serialize_session(session),
        "evaluation": serialize_evaluation(evaluation),
        "assignment": serialize_assignment(assignment),
    }


def dumps_json(obj: Dict[str, Any], *, pretty: bool = False) -> str:
    """
    Stable JSON encoder:
    - sort_keys=True: deterministic output
    - separators: compact by default
    """
    if pretty:
        return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def dump_json_file(path: str | Path, obj: Dict[str, Any], *, pretty: bool = False) -> Path:
    """
    Write JSON to file with stable formatting.
    Creates parent directories if needed.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps_json(obj, pretty=pretty), encoding="utf-8")
    return p
