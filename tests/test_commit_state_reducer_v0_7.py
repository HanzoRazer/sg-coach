"""
Tests for v0.7 commit state reducer.
"""
from sg_coach.assignment_v0_6 import CommitMode, CommitStateV0
from sg_coach.commit_state_reducer_v0_7 import reduce_commit_state


def test_reduce_commit_state_none_noop():
    """Test that mode=none returns as-is."""
    s = CommitStateV0()
    assert reduce_commit_state(s) == s


def test_reduce_commit_state_decrements_and_resets():
    """Test that reducer decrements cycles and resets when zero."""
    s = CommitStateV0(mode=CommitMode.hold, cycles_remaining=2, note="x")

    s1 = reduce_commit_state(s)
    assert s1.mode == CommitMode.hold
    assert s1.cycles_remaining == 1

    s2 = reduce_commit_state(s1)
    assert s2.mode == CommitMode.none
    assert s2.cycles_remaining == 0


def test_reduce_commit_state_cooldown_decrements():
    """Test cooldown mode also decrements correctly."""
    s = CommitStateV0(mode=CommitMode.cooldown, cycles_remaining=3, note="cooldown test")

    s1 = reduce_commit_state(s)
    assert s1.mode == CommitMode.cooldown
    assert s1.cycles_remaining == 2
    assert s1.note == "cooldown test"

    s2 = reduce_commit_state(s1)
    assert s2.mode == CommitMode.cooldown
    assert s2.cycles_remaining == 1

    s3 = reduce_commit_state(s2)
    assert s3.mode == CommitMode.none
    assert s3.cycles_remaining == 0


def test_reduce_commit_state_already_zero_resets():
    """Test that cycles_remaining=0 resets to none."""
    s = CommitStateV0(mode=CommitMode.hold, cycles_remaining=0, note="should reset")
    result = reduce_commit_state(s)
    assert result.mode == CommitMode.none
    assert result.cycles_remaining == 0
