"""
Tests for sg_coach.ota_payload (OTA packaging and verification).
"""
from __future__ import annotations

from uuid import uuid4

from sg_coach.assignment_policy import plan_assignment
from sg_coach.assignment_serializer import serialize_bundle
from sg_coach.schemas import (
    CoachEvaluation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    TimingErrorStats,
)
from sg_coach.ota_payload import build_ota_payload, verify_ota_payload


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


def _make_evaluation(session_id) -> CoachEvaluation:
    return CoachEvaluation.model_validate({
        "session_id": str(session_id),
        "coach_version": "coach-rules@0.1.0",
        "focus_recommendation": {"concept": "grid_alignment", "reason": "test"},
        "confidence": 0.85,
    })


def test_ota_pack_unsigned_verifies():
    """Unsigned OTA payload passes integrity check."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)
    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)
    payload = build_ota_payload(bundle_obj=bundle)
    ok, reason = verify_ota_payload(payload)
    assert ok, reason


def test_ota_pack_signed_verifies_with_key():
    """Signed OTA payload verifies with correct key."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)
    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)
    key = b"supersecretkey-supersecretkey"
    payload = build_ota_payload(bundle_obj=bundle, signer_key=key, signer_kid="k1")
    ok, reason = verify_ota_payload(payload, signer_key=key)
    assert ok, reason


def test_ota_tamper_fails_digest():
    """Tampered bundle fails SHA256 integrity check."""
    s = _make_session()
    ev = _make_evaluation(s.session_id)
    a = plan_assignment(session=s, evaluation=ev)
    bundle = serialize_bundle(session=s, evaluation=ev, assignment=a)
    payload = build_ota_payload(bundle_obj=bundle)
    # tamper
    payload["bundle"]["session"]["instrument_id"] = "sg-999999"
    ok, reason = verify_ota_payload(payload)
    assert not ok
    assert "bundle_sha256 mismatch" in reason
