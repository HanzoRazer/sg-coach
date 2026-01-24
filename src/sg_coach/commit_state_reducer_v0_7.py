"""
v0.7 Commit State Reducer.

Single source of truth for commit_state countdown logic.
"""
from __future__ import annotations

from .assignment_v0_6 import CommitMode, CommitStateV0


def reduce_commit_state(prior: CommitStateV0) -> CommitStateV0:
    """
    Single-step reducer for commit_state.

    Rules:
      - If mode=none: return as-is
      - If cycles_remaining > 0: decrement by 1
      - If after decrement cycles_remaining == 0: reset to CommitStateV0() (mode=none)
    """
    if prior.mode == CommitMode.none:
        return prior

    if prior.cycles_remaining <= 0:
        return CommitStateV0()

    next_cycles = prior.cycles_remaining - 1
    if next_cycles <= 0:
        return CommitStateV0()

    return CommitStateV0(mode=prior.mode, cycles_remaining=next_cycles, note=prior.note)


__all__ = ["reduce_commit_state"]
