"""
Groove-Aware Evaluation Builder (v0.3)

Inputs:
  - SessionRecord (from v0.1 schema)
  - GrooveSnapshotV0 (from Groove Layer)
  - optional ControlIntentV0 (if Groove Layer already emitted it for the segment)

Outputs:
  - EvaluationV0_3 + CoachFeedbackV0

Deterministic; no AI dependency yet.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from .groove_contracts import ControlIntentV0, GrooveSnapshotV0
from .schemas import SessionRecord


class EvaluationBuilderV0_3:
    """
    Groove-aware evaluation builder.

    Inputs:
      - SessionRecord (events + optional groove snapshot)
      - GrooveSnapshotV0 (from Groove Layer)
      - optional ControlIntentV0 (if Groove Layer already emitted it for the segment)

    Outputs:
      - EvaluationV0_3 + CoachFeedbackV0

    Deterministic; no AI dependency yet.
    """

    # thresholds (tune later)
    DRIFT_PPM_FLAG = 1500.0
    STABILITY_WARN = 0.70
    STABILITY_BLOCK = 0.55
    DENSITY_OVERPLAY = 0.80

    def build(
        self,
        session: SessionRecord,
        groove: GrooveSnapshotV0,
        control_intent: ControlIntentV0 | None = None,
    ) -> Tuple[EvaluationV0_3, CoachFeedbackV0]:
        timing_score, consistency_score = self._score_from_session(session)

        flags = self._derive_flags(groove, timing_score, consistency_score)

        fb = self._build_feedback(flags, groove)

        ev = EvaluationV0_3(
            session_id=str(session.session_id),
            instrument_id=session.instrument_id,
            groove=groove,
            control_intent=control_intent,
            timing_score=timing_score,
            consistency_score=consistency_score,
            flags=flags,
        )
        return ev, fb

    def _score_from_session(self, session: SessionRecord) -> Tuple[float, float]:
        """
        v0 scoring: derive timing/consistency from SessionRecord performance data.
        """
        perf = session.performance

        # Timing score based on timing error (lower error = higher score)
        # Map 0-50ms error to 1.0-0.0 score
        mean_err = perf.timing_error_ms.mean
        timing = max(0.0, min(1.0, 1.0 - (mean_err / 50.0)))

        # Consistency score based on notes played vs expected
        if perf.notes_expected > 0:
            play_ratio = perf.notes_played / perf.notes_expected
            drop_ratio = perf.notes_dropped / perf.notes_expected
            consistency = max(0.0, min(1.0, play_ratio - drop_ratio * 0.5))
        else:
            consistency = 0.5

        return round(timing, 3), round(consistency, 3)

    def _derive_flags(
        self, groove: GrooveSnapshotV0, timing: float, consistency: float
    ) -> Dict[str, bool]:
        flags: Dict[str, bool] = {}

        if groove.drift_ppm >= self.DRIFT_PPM_FLAG:
            flags["tempo_drift"] = True

        if groove.density >= self.DENSITY_OVERPLAY:
            flags["overplaying"] = True

        if groove.stability < self.STABILITY_WARN:
            flags["instability"] = True

        if groove.stability < self.STABILITY_BLOCK:
            flags["instability_block"] = True

        if timing < 0.60:
            flags["low_confidence"] = True

        if consistency < 0.70:
            flags["inconsistent_dynamics"] = True

        return flags

    def _build_feedback(
        self, flags: Dict[str, bool], groove: GrooveSnapshotV0
    ) -> CoachFeedbackV0:
        hints: List[str] = []
        severity: str = "info"
        msg_parts: List[str] = []

        if flags.get("instability_block"):
            severity = "block"
            msg_parts.append("Stability is too low—simplify and slow down.")
            hints.extend(
                [
                    "Play only downstrokes for 30 seconds.",
                    "Count 1-2-3-4 out loud and match your strums to the count.",
                ]
            )
        elif flags.get("instability"):
            severity = "warn"
            msg_parts.append("Your groove is unstable—reduce complexity.")
            hints.extend(
                [
                    "Reduce to a simpler rhythm pattern.",
                    "Focus on landing strums exactly on the beat.",
                ]
            )

        if flags.get("tempo_drift"):
            severity = "warn" if severity == "info" else severity
            msg_parts.append("Tempo drift detected—re-center your time.")
            hints.append("Tap your foot on every beat and match your strum to it.")

        if flags.get("overplaying"):
            severity = "warn" if severity == "info" else severity
            msg_parts.append("You're playing too dense—leave space.")
            hints.append("Try halving the number of strums per bar.")

        if not msg_parts:
            msg_parts.append("Good control—take a small step forward.")
            hints.extend(
                [
                    "Keep accents consistent.",
                    "Maintain even dynamics between strokes.",
                ]
            )

        msg = " ".join(msg_parts)
        return CoachFeedbackV0(severity=severity, message=msg, hints=hints)


__all__ = ["EvaluationBuilderV0_3"]
