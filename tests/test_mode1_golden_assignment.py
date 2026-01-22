"""
Golden snapshot test for Mode-1 coaching spine.

This test is CONTRACT ENFORCEMENT — it prevents silent drift in the
deterministic Session → CoachEvaluation → PracticeAssignment pipeline.

To update the golden file (one-time bless):
    UPDATE_GOLDEN=1 pytest -q -k test_mode1_golden_assignment

After blessing, the golden file becomes LAW and CI will enforce it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from sg_coach.assignment_policy import plan_assignment
from sg_coach.assignment_serializer import serialize_assignment
from sg_coach.schemas import (
    CoachEvaluation,
    PerformanceSummary,
    ProgramRef,
    ProgramType,
    SessionRecord,
    SessionTiming,
    TimingErrorStats,
)


GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_FILE = GOLDEN_DIR / "mode1_assignment_v1.json"

# Canonical session ID for deterministic output
CANONICAL_SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")


def _load_canonical_session() -> SessionRecord:
    """
    Minimal, deterministic "facts-only" session.
    This is the canonical regression vector for Mode-1.
    
    DO NOT CHANGE unless you are bumping the contract version.
    """
    return SessionRecord(
        session_id=CANONICAL_SESSION_ID,
        instrument_id="sg-golden-001",
        engine_version="zt-band@0.2.0",
        program_ref=ProgramRef(
            type=ProgramType.ztprog,
            name="golden_vector_program",
            hash="sha256:golden",
        ),
        timing=SessionTiming(
            bpm=120.0,
            grid=16,
            strict=True,
            late_drop_ms=35,
            ghost_vel_max=22,
            panic_enabled=True,
        ),
        duration_s=180,
        performance=PerformanceSummary(
            bars_played=8,
            notes_expected=100,
            notes_played=97,
            notes_dropped=3,
            timing_error_ms=TimingErrorStats(mean=18.0, std=8.0, max=45.0),
            error_by_step={"7": 32.0, "15": 28.0},
        ),
        events={"late_drops": 3, "panic_triggered": False},
    )


def _make_canonical_evaluation(session_id: UUID) -> CoachEvaluation:
    """
    Canonical evaluation for golden vector.
    Uses fixed values to ensure deterministic assignment output.
    """
    return CoachEvaluation.model_validate({
        "session_id": str(session_id),
        "coach_version": "coach-rules@0.1.0",
        "focus_recommendation": {
            "concept": "grid_alignment",
            "reason": "Timing consistency on step 7 needs work",
        },
        "confidence": 0.85,
        "findings": [],
        "strengths": [],
        "weaknesses": [],
    })


def _normalize_for_comparison(d: dict) -> dict:
    """
    Remove fields that vary between runs (timestamps, generated IDs).
    """
    result = dict(d)
    # Remove fields that are generated fresh each time
    result.pop("assignment_id", None)
    result.pop("created_at", None)
    return result


@pytest.mark.contract
def test_mode1_golden_assignment_snapshot():
    """
    Verify that the Mode-1 assignment pipeline produces stable output.
    
    This test locks the deterministic behavior of:
    SessionRecord → CoachEvaluation → PracticeAssignment
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    session = _load_canonical_session()
    evaluation = _make_canonical_evaluation(session.session_id)
    assignment = plan_assignment(session=session, evaluation=evaluation)

    # Serialize to JSON-safe dict
    current = serialize_assignment(assignment)
    current_normalized = _normalize_for_comparison(current)

    update = os.environ.get("UPDATE_GOLDEN", "").strip().lower() in {"1", "true", "yes"}
    
    if update or not GOLDEN_FILE.exists():
        GOLDEN_FILE.write_text(
            json.dumps(current_normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Golden file updated (set UPDATE_GOLDEN=0 to enforce).")

    expected = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))

    assert current_normalized == expected, (
        f"Mode-1 assignment output has drifted from golden vector.\n"
        f"If this is intentional, run: UPDATE_GOLDEN=1 pytest -k test_mode1_golden_assignment\n"
        f"Then bump COACH_CONTRACT_VERSION if the change affects OTA payloads."
    )
