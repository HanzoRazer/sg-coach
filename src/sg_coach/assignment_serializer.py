"""
Assignment Serializer: PracticeAssignment -> on-wire JSON bundle.

Produces a FirmwareEnvelope suitable for OTA delivery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from .schemas import PracticeAssignment


def _iso_z(dt: datetime) -> str:
    """Format datetime as ISO 8601 with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FirmwareEnvelope(BaseModel):
    """Wrapper for OTA delivery of assignment."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0.0")
    bundle_type: str = Field(default="assignment")
    created_at: str  # ISO 8601
    payload: Dict[str, Any]


def serialize_bundle(assignment: PracticeAssignment) -> Dict[str, Any]:
    """
    Convert PracticeAssignment to on-wire JSON envelope.

    Returns a dict that can be JSON-serialized for OTA delivery.
    """
    payload = assignment.model_dump(mode="json")

    envelope = FirmwareEnvelope(
        created_at=_iso_z(assignment.created_at),
        payload=payload,
    )

    return envelope.model_dump(mode="json")


def deserialize_bundle(data: Dict[str, Any]) -> PracticeAssignment:
    """
    Reconstruct PracticeAssignment from on-wire envelope.

    Validates the envelope structure before extracting the payload.
    """
    envelope = FirmwareEnvelope.model_validate(data)
    return PracticeAssignment.model_validate(envelope.payload)


__all__ = ["FirmwareEnvelope", "serialize_bundle", "deserialize_bundle"]
