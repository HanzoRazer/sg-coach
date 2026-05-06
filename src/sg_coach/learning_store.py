"""
Learning Store — Persistent append-only storage for LearningSignals.

Sprint 6: JSONL storage, no runtime wiring.

This module provides:
- LearningSignalStore: Append-only JSONL storage
- aggregate_user_effectiveness(): User-specific aggregation
- aggregate_global_effectiveness(): Global aggregation

Core rule: Sprint 6 creates durable memory, not blending or
production-grade storage concurrency.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Sequence, Union

from sg_spec.schemas.learning_aggregation import LearningSignalAggregateSet
from sg_spec.schemas.learning_store import (
    LearningSignalQuery,
    LearningStoreStats,
)
from sg_spec.schemas.user_feedback import LearningSignal

from .learning_aggregation import aggregate_effectiveness


def _signal_to_json(signal: LearningSignal) -> str:
    """Serialize a LearningSignal to JSON string."""
    return signal.model_dump_json()


def _signal_from_json(line: str) -> LearningSignal:
    """Deserialize a LearningSignal from JSON string."""
    return LearningSignal.model_validate_json(line)


class LearningSignalStore:
    """
    Append-only JSONL storage for LearningSignals.

    Each signal is stored as one JSON line in the file.
    Concurrent writes are out of scope for v1.

    Parameters
    ----------
    path:
        Path to the JSONL file. Parent directories will be created.

    Notes
    -----
    - Append-only: existing rows are never modified
    - One LearningSignal per line
    - Blank lines are ignored when reading
    - Invalid JSON raises immediately (no silent skipping)
    """

    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Path to the JSONL file."""
        return self._path

    def _ensure_parent_dirs(self) -> None:
        """Create parent directories if they don't exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, signal: LearningSignal) -> LearningSignal:
        """
        Append a single signal to the store.

        Parameters
        ----------
        signal:
            The signal to store.

        Returns
        -------
        The same signal (for chaining).
        """
        self._ensure_parent_dirs()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(_signal_to_json(signal) + "\n")
        return signal

    def append_many(
        self,
        signals: Sequence[LearningSignal],
    ) -> List[LearningSignal]:
        """
        Append multiple signals to the store.

        Parameters
        ----------
        signals:
            The signals to store.

        Returns
        -------
        List of the same signals (for chaining).
        """
        if not signals:
            return []

        self._ensure_parent_dirs()
        with open(self._path, "a", encoding="utf-8") as f:
            for signal in signals:
                f.write(_signal_to_json(signal) + "\n")
        return list(signals)

    def all(self) -> List[LearningSignal]:
        """
        Read all signals from the store.

        Returns
        -------
        List of all stored signals.

        Raises
        ------
        FileNotFoundError:
            If the store file doesn't exist.
        ValueError:
            If any line contains invalid JSON.
        """
        if not self._path.exists():
            return []

        signals: List[LearningSignal] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    signals.append(_signal_from_json(line))
                except Exception as e:
                    raise ValueError(
                        f"Invalid JSON at line {line_num} in {self._path}: {e}"
                    ) from e
        return signals

    def query(
        self,
        query: Optional[LearningSignalQuery] = None,
    ) -> List[LearningSignal]:
        """
        Query signals with optional filtering.

        Parameters
        ----------
        query:
            Filter parameters. If None, returns all signals.

        Returns
        -------
        List of matching signals.

        Notes
        -----
        - If query.user_id is set and include_global=True:
          returns signals where user_id matches OR user_id is None
        - If query.user_id is set and include_global=False:
          returns only signals where user_id matches
        - limit applies after filtering
        """
        signals = self.all()

        if query is None:
            return signals

        filtered: List[LearningSignal] = []
        for signal in signals:
            if not self._matches_query(signal, query):
                continue
            filtered.append(signal)

        if query.limit is not None:
            filtered = filtered[:query.limit]

        return filtered

    def _matches_query(
        self,
        signal: LearningSignal,
        query: LearningSignalQuery,
    ) -> bool:
        """Check if a signal matches the query filters."""
        # User ID filter with include_global logic
        if query.user_id is not None:
            if signal.user_id == query.user_id:
                pass  # matches
            elif signal.user_id is None and query.include_global:
                pass  # global signal included
            else:
                return False

        # Session ID filter
        if query.session_id is not None:
            if signal.session_id != query.session_id:
                return False

        # Instrument ID filter
        if query.instrument_id is not None:
            if signal.instrument_id != query.instrument_id:
                return False

        # Diagnosis code filter
        if query.diagnosis_code is not None:
            if signal.source_finding_code != query.diagnosis_code:
                return False

        # Action type filter
        if query.action_type is not None:
            if signal.action_type != query.action_type:
                return False

        return True

    def stats(self) -> LearningStoreStats:
        """
        Get statistics about the store.

        Returns
        -------
        LearningStoreStats with counts.
        """
        signals = self.all()

        total = len(signals)
        global_count = sum(1 for s in signals if s.user_id is None)
        user_count = total - global_count

        return LearningStoreStats(
            total_signals=total,
            user_signal_count=user_count,
            global_signal_count=global_count,
        )


def aggregate_user_effectiveness(
    store: LearningSignalStore,
    user_id: str,
) -> LearningSignalAggregateSet:
    """
    Aggregate effectiveness for a specific user.

    Parameters
    ----------
    store:
        The signal store to query.
    user_id:
        The user to aggregate for.

    Returns
    -------
    Aggregated effectiveness profiles for that user only.

    Notes
    -----
    - Does NOT include global signals (no blending in v1)
    - Uses include_global=False explicitly
    """
    query = LearningSignalQuery(
        user_id=user_id,
        include_global=False,
    )
    signals = store.query(query)
    return aggregate_effectiveness(signals)


def aggregate_global_effectiveness(
    store: LearningSignalStore,
) -> LearningSignalAggregateSet:
    """
    Aggregate effectiveness from global signals only.

    Parameters
    ----------
    store:
        The signal store to query.

    Returns
    -------
    Aggregated effectiveness profiles from global signals.

    Notes
    -----
    - Only uses signals where user_id is None
    """
    all_signals = store.all()
    global_signals = [s for s in all_signals if s.user_id is None]
    return aggregate_effectiveness(global_signals)


__all__ = [
    "LearningSignalStore",
    "aggregate_user_effectiveness",
    "aggregate_global_effectiveness",
]
