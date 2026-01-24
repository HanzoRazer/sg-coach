"""
v0.7 Store Shim: In-memory session state for device-local identity pattern.

Provides:
- SessionStateV0_7: minimal in-memory store state for a single session
- InMemoryCoachStoreV0_7: store shim that persists history + commit_state

This is intended for:
- Device runtime
- Unit tests
- Later replacement by SQLite without changing planner interface
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .assignment_v0_6 import AssignmentV0_6, CommitStateV0
from .commit_state_reducer_v0_7 import reduce_commit_state
from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from .planner_v0_6 import PlannerPolicyV0_6, plan_next_v0_6


@dataclass
class SessionStateV0_7:
    """
    Minimal in-memory store state for a single session.

    This is the "device-local identity" pattern:
      - key by session_id
      - no user identity required
      - persists only runtime planning state
    """

    session_id: str
    instrument_id: str

    commit_state: CommitStateV0 = field(default_factory=CommitStateV0)
    evaluations: List[EvaluationV0_3] = field(default_factory=list)
    # Can hold v0.5/v0.6 assignments (duck typing)
    assignments: List[Any] = field(default_factory=list)


class InMemoryCoachStoreV0_7:
    """
    Store shim that:
      - keeps session state (history + commit_state)
      - produces next assignment using v0.6 planner
      - applies commit_state reducer between ticks

    Intended for:
      - device runtime
      - unit tests
      - later replacement by SQLite without changing planner interface
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionStateV0_7] = {}

    def get_or_create(self, session_id: str, instrument_id: str) -> SessionStateV0_7:
        """Get existing session state or create new one."""
        st = self._sessions.get(session_id)
        if st is None:
            st = SessionStateV0_7(session_id=session_id, instrument_id=instrument_id)
            self._sessions[session_id] = st
        # if instrument_id changes mid-session, we keep original (device invariant)
        return st

    def get(self, session_id: str) -> Optional[SessionStateV0_7]:
        """Get session state by ID, or None if not found."""
        return self._sessions.get(session_id)

    def append_evaluation(self, e: EvaluationV0_3) -> None:
        """Append an evaluation to session history."""
        st = self.get_or_create(e.session_id, e.instrument_id)
        st.evaluations.append(e)

    def append_assignment(
        self, a: Any, session_id: str, instrument_id: str
    ) -> None:
        """Append an assignment to session history."""
        st = self.get_or_create(session_id, instrument_id)
        st.assignments.append(a)
        # persist commit_state forward if assignment has it
        commit_state = getattr(a, "commit_state", None)
        if isinstance(commit_state, CommitStateV0):
            st.commit_state = commit_state

    def next_assignment(
        self,
        evaluation: EvaluationV0_3,
        feedback: CoachFeedbackV0,
        policy: PlannerPolicyV0_6 = PlannerPolicyV0_6(),
    ) -> AssignmentV0_6:
        """
        Core flow:
          1) load session
          2) reduce commit_state (one tick)
          3) call plan_next_v0_6 with history + reduced commit_state
          4) store evaluation + assignment
        """
        st = self.get_or_create(evaluation.session_id, evaluation.instrument_id)

        # Step 1: advance commit_state one tick (decrement/reset)
        reduced_commit = reduce_commit_state(st.commit_state)

        # Step 2: plan using history
        assignment = plan_next_v0_6(
            evaluation,
            feedback,
            history_assignments=st.assignments,
            history_evaluations=st.evaluations,
            prior_commit_state=reduced_commit,
            policy=policy,
        )

        # Step 3: persist
        st.evaluations.append(evaluation)
        st.assignments.append(assignment)
        st.commit_state = assignment.commit_state

        return assignment


__all__ = [
    "SessionStateV0_7",
    "InMemoryCoachStoreV0_7",
]
