# src/sg_coach/groove_intent_engine_v1.py
"""
Deterministic GrooveProfileV1 -> GrooveControlIntentV1 baseline engine.

This is a minimal, explainable, rule-based mapper for the Profile -> Intent boundary.
It exists primarily to enable deterministic replay testing.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

# Engine identity for diff headers and lineage tracking
ENGINE_SCHEMA_VERSION: str = "v1"
ENGINE_SALT: str = "v1"  # bump only when you intentionally change intent-id lineage / baseline mapping
ENGINE_IDENTITY: str = f"{ENGINE_SCHEMA_VERSION}+salt:{ENGINE_SALT}"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _midpoint(r: Tuple[float, float]) -> float:
    return (float(r[0]) + float(r[1])) / 2.0


def _stable_intent_id(profile_id: str, salt: str = ENGINE_SALT) -> str:
    h = hashlib.sha256(f"{salt}:{profile_id}".encode("utf-8")).hexdigest()[:12]
    return f"gci_{h}"


def generate_groove_control_intent_v1(
    profile: Dict[str, Any],
    *,
    now_utc: Optional[datetime] = None,
    horizon_ms: int = 2000,
) -> Dict[str, Any]:
    """
    Deterministic GrooveProfileV1 -> GrooveControlIntentV1 baseline.

    This is intentionally conservative and rule-based:
    - target_bpm = midpoint of supported_bpm_range
    - lock_strength = clamp(groove_elasticity.lock_threshold, 0..1)
    - microshift_ms = clamp(timing_bias.mean_offset_ms, ±30ms)
    - drift_correction from tempo_stability.drift_slope
    - control_modes from tempo_stability.confidence & error_recovery signals
    - recovery.enabled from panic_probability/self_correction_rate
    """

    # Fixed timestamp unless injected (keeps vectors deterministic)
    if now_utc is None:
        now_utc = datetime(2026, 1, 24, 10, 30, 0, tzinfo=timezone.utc)

    timing_bias = profile.get("timing_bias", {}) or {}
    tempo_stability = profile.get("tempo_stability", {}) or {}
    error_recovery = profile.get("error_recovery", {}) or {}
    groove_elasticity = profile.get("groove_elasticity", {}) or {}
    confidence_band = profile.get("confidence_band", {}) or {}

    profile_id = str(profile.get("profile_id", "gp_unknown"))

    # Tempo target (contract-safe, deterministic)
    bpm_range = tempo_stability.get("supported_bpm_range", [80, 140])
    try:
        target_bpm = _midpoint((float(bpm_range[0]), float(bpm_range[1])))
    except Exception:
        target_bpm = 110.0

    # lock strength
    lock_strength = float(groove_elasticity.get("lock_threshold", 0.70))
    lock_strength = _clamp(lock_strength, 0.0, 1.0)

    # microshift (adapter later clamps too; contract can carry intent)
    microshift_ms = float(timing_bias.get("mean_offset_ms", 0.0))
    microshift_ms = _clamp(microshift_ms, -30.0, 30.0)

    # drift correction tier from drift_slope
    drift_slope = float(tempo_stability.get("drift_slope", 0.0))
    if drift_slope < 0.20:
        drift_correction: Literal["none", "soft", "aggressive"] = "none"
    elif drift_slope < 0.60:
        drift_correction = "soft"
    else:
        drift_correction = "aggressive"

    # control modes
    tempo_conf = float(tempo_stability.get("confidence", confidence_band.get("upper", 0.85) or 0.85))
    panic_p = float(error_recovery.get("panic_probability", 0.0))
    self_corr = float(error_recovery.get("self_correction_rate", 0.8))

    control_modes: List[Literal["follow", "assist", "stabilize", "challenge", "recover"]] = []

    # Stabilize when we have strong evidence of tempo personality & decent lock threshold.
    if tempo_conf >= 0.80 and lock_strength >= 0.60:
        control_modes.append("stabilize")
    else:
        control_modes.append("follow")

    # Recover mode if panic risk is non-trivial or self-correction is weak.
    if panic_p >= 0.20 or self_corr <= 0.60:
        control_modes.append("recover")

    # Assist when we're not fully locking, but confidence is high enough to help.
    if lock_strength <= 0.75 and tempo_conf >= 0.70:
        control_modes.append("assist")

    # Keep deterministic ordering and uniqueness
    seen = set()
    control_modes = [m for m in control_modes if not (m in seen or seen.add(m))]

    # recovery block
    recovery_enabled = bool(panic_p >= 0.12 or self_corr <= 0.75)
    grace_beats = float(error_recovery.get("mean_recovery_beats", 2.0))
    grace_beats = _clamp(grace_beats, 0.0, 8.0)

    # Dynamics – conservative baseline
    # assist_gain relates to confidence; expression_window inversely relates to lock strength.
    assist_gain = _clamp(0.25 + 0.75 * tempo_conf, 0.0, 1.0)
    expression_window = _clamp(1.0 - lock_strength, 0.0, 1.0)

    intent = {
        "schema_id": "groove_control_intent",
        "schema_version": "v1",
        "intent_id": _stable_intent_id(profile_id),
        "profile_id": profile_id,
        "generated_at_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "horizon_ms": int(_clamp(float(horizon_ms), 50.0, 60000.0)),
        "confidence": _clamp(tempo_conf, 0.0, 1.0),
        "control_modes": control_modes,
        "tempo": {
            "target_bpm": round(float(target_bpm), 3),
            "lock_strength": round(float(lock_strength), 3),
            "drift_correction": drift_correction,
        },
        "timing": {
            "microshift_ms": round(float(microshift_ms), 3),
            "anticipation_bias": str(timing_bias.get("direction", "neutral")),
        },
        "dynamics": {
            "assist_gain": round(float(assist_gain), 3),
            "expression_window": round(float(expression_window), 3),
        },
        "recovery": {
            "enabled": recovery_enabled,
            "grace_beats": round(float(grace_beats), 3),
        },
        "reason_codes": ["profile_to_intent_v1"],
        "extensions": {},
    }
    return intent
