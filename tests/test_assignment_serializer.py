"""
Tests for sg_coach.assignment_serializer (UUID-safe JSON export).
"""
from __future__ import annotations

import json
from uuid import UUID, uuid4

from sg_coach.assignment_serializer import dumps_json, serialize_bundle
from sg_coach.assignment_policy import plan_assignment
from sg_coach.schemas import (
    CoachEvaluation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    TimingErrorStats,
)


def _make_session() -> SessionRecord:
    return SessionRecord(
        session_id=uuid4(),
        instrument_id="sg-000142",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="salsa_minor_Dm",
            hash="sha256:abc123",
        ),
        timing=SessionTiming(
            bpm=110,
            grid=16,
            strict=True,
            late_drop_ms=35,
            ghost_vel_max=22,
            panic_enabled=True,
        ),
        duration_s=240,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=100,
            notes_dropped=0,
            timing_error_ms=TimingErrorStats(mean=14.0, std=6.0, max=40.0),
            error_by_step={"7": 32.0, "3": 18.0},
        ),
        events={"late_drops": 2, "panic_triggered": False},
    )


def _make_evaluation(session_id: UUID) -> CoachEvaluation:
    """Minimal CoachEvaluation for testing."""
    return CoachEvaluation.model_validate({
        "session_id": str(session_id),
        "coach_version": "coach-rules@0.1.0",
        "focus_recommendation": {"concept": "grid_alignment", "reason": "test"},
        "confidence": 0.85,
    })


def test_bundle_is_json_safe_and_has_expected_keys():
    """Bundle contains expected envelope keys and serializes cleanly."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)

    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)
    assert bundle["kind"] == "sg_coach_bundle"
    assert bundle["schema_version"] == "v1"
    assert "session" in bundle and "evaluation" in bundle and "assignment" in bundle

    # JSON serialization should not raise (UUID/datetime must be safe)
    txt = dumps_json(bundle)
    obj = json.loads(txt)
    assert obj["kind"] == "sg_coach_bundle"


def test_ids_are_strings_in_json_payload():
    """UUIDs are converted to strings in the serialized output."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)
    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)

    # Pydantic json mode should have converted UUIDs to strings
    assert isinstance(bundle["session"]["session_id"], str)
    UUID(bundle["session"]["session_id"])  # validate format

    assert isinstance(bundle["assignment"]["assignment_id"], str)
    UUID(bundle["assignment"]["assignment_id"])


def test_created_at_uses_z_suffix():
    """All created_at fields use ISO-8601 with Z suffix."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)
    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)

    assert bundle["created_at"].endswith("Z")
    assert bundle["session"]["created_at"].endswith("Z")
    assert bundle["evaluation"]["created_at"].endswith("Z")
    assert bundle["assignment"]["created_at"].endswith("Z")
