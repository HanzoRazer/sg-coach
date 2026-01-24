"""
v0.8 SQLite Store: Persistent session state with SQLite backend.

Persists:
- sessions: session_id, instrument_id, commit_state_json
- evaluations: JSON blobs (append-only)
- assignments: JSON blobs (append-only)

Designed for:
- Device runtime (with WAL mode for durability)
- Deterministic replay tests
- Future migration to production database
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .assignment_v0_6 import AssignmentV0_6, CommitStateV0
from .commit_state_reducer_v0_7 import reduce_commit_state
from .evaluation_v0_3 import CoachFeedbackV0, EvaluationV0_3
from .planner_v0_6 import PlannerPolicyV0_6, plan_next_v0_6


@dataclass
class SqliteStoreConfigV0_8:
    """
    SQLite store config:
      - db_path can be ':memory:' or a file path
      - foreign_keys enabled
      - WAL mode enabled for device durability (safe default)
    """

    db_path: str
    enable_wal: bool = True


class SQLiteCoachStoreV0_8:
    """
    SQLite-backed session store shim.

    Persists:
      - sessions: session_id, instrument_id, commit_state_json
      - evaluations: JSON blobs (append-only)
      - assignments: JSON blobs (append-only)

    Compatibility:
      - planner_v0_6 expects history_assignments duck-typed objects with attributes.
      - we store JSON and rehydrate into SimpleNamespace for duck typing.
    """

    def __init__(self, cfg: SqliteStoreConfigV0_8) -> None:
        self.cfg = cfg
        self._conn = sqlite3.connect(cfg.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        if cfg.enable_wal and cfg.db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL;")
        self.migrate()

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass

    def migrate(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
              session_id TEXT PRIMARY KEY,
              instrument_id TEXT NOT NULL,
              commit_state_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evaluations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              instrument_id TEXT NOT NULL,
              evaluated_at_utc TEXT,
              payload_json TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS assignments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              instrument_id TEXT NOT NULL,
              created_at_utc TEXT,
              payload_json TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations(session_id, id);
            CREATE INDEX IF NOT EXISTS idx_assignments_session ON assignments(session_id, id);
            """
        )
        self._conn.commit()

    # ---------------------------
    # Session helpers
    # ---------------------------

    def _get_session_row(self, session_id: str) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT session_id, instrument_id, commit_state_json FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        return cur.fetchone()

    def get_or_create_session(self, session_id: str, instrument_id: str) -> None:
        """Ensure session exists in database."""
        row = self._get_session_row(session_id)
        if row is not None:
            return
        empty_commit = CommitStateV0().model_dump(mode="json")
        self._conn.execute(
            "INSERT INTO sessions(session_id, instrument_id, commit_state_json) VALUES(?,?,?)",
            (
                session_id,
                instrument_id,
                json.dumps(empty_commit, separators=(",", ":"), sort_keys=True),
            ),
        )
        self._conn.commit()

    def get_commit_state(self, session_id: str) -> CommitStateV0:
        """Get commit state for session, or default if not found."""
        row = self._get_session_row(session_id)
        if row is None:
            return CommitStateV0()
        data = json.loads(row["commit_state_json"])
        return CommitStateV0.model_validate(data)

    def set_commit_state(self, session_id: str, commit_state: CommitStateV0) -> None:
        """Update commit state for session."""
        self._conn.execute(
            "UPDATE sessions SET commit_state_json = ? WHERE session_id = ?",
            (
                json.dumps(
                    commit_state.model_dump(mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                session_id,
            ),
        )
        self._conn.commit()

    # ---------------------------
    # History retrieval
    # ---------------------------

    def _get_recent_json_blobs(
        self,
        table: str,
        session_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            f"SELECT payload_json FROM {table} WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = cur.fetchall()
        blobs = [json.loads(r["payload_json"]) for r in rows]
        if limit > 0 and len(blobs) > limit:
            return blobs[-limit:]
        return blobs

    def get_recent_assignments(self, session_id: str, limit: int) -> List[object]:
        """
        Return duck-typed objects with attrs (tempo_nudge_bpm, density_cap, allow_probe, commit_state?).
        """
        from types import SimpleNamespace

        blobs = self._get_recent_json_blobs("assignments", session_id, limit)
        return [SimpleNamespace(**b) for b in blobs]

    def get_recent_evaluations(self, session_id: str, limit: int) -> List[EvaluationV0_3]:
        """Return recent evaluations as validated models."""
        blobs = self._get_recent_json_blobs("evaluations", session_id, limit)
        out: List[EvaluationV0_3] = []
        for b in blobs:
            out.append(EvaluationV0_3.model_validate(b))
        return out

    # ---------------------------
    # Append operations
    # ---------------------------

    def append_evaluation(self, e: EvaluationV0_3) -> None:
        """Append evaluation to history."""
        self.get_or_create_session(e.session_id, e.instrument_id)
        payload = e.model_dump(mode="json")
        self._conn.execute(
            "INSERT INTO evaluations(session_id, instrument_id, evaluated_at_utc, payload_json) VALUES(?,?,?,?)",
            (
                e.session_id,
                e.instrument_id,
                payload.get("evaluated_at_utc"),
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
            ),
        )
        self._conn.commit()

    def append_assignment(self, a: AssignmentV0_6) -> None:
        """Append assignment to history and update commit state."""
        self.get_or_create_session(a.session_id, a.instrument_id)
        payload = a.model_dump(mode="json")
        self._conn.execute(
            "INSERT INTO assignments(session_id, instrument_id, created_at_utc, payload_json) VALUES(?,?,?,?)",
            (
                a.session_id,
                a.instrument_id,
                payload.get("created_at_utc"),
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
            ),
        )
        self._conn.commit()
        self.set_commit_state(a.session_id, a.commit_state)

    # ---------------------------
    # Core: next assignment
    # ---------------------------

    def next_assignment(
        self,
        evaluation: EvaluationV0_3,
        feedback: CoachFeedbackV0,
        policy: PlannerPolicyV0_6 = PlannerPolicyV0_6(),
    ) -> AssignmentV0_6:
        """
        Flow:
          1) ensure session exists
          2) reduce commit_state one tick
          3) pull history windows
          4) call plan_next_v0_6
          5) persist evaluation + assignment + commit_state
        """
        self.get_or_create_session(evaluation.session_id, evaluation.instrument_id)

        prior_commit = self.get_commit_state(evaluation.session_id)
        reduced_commit = reduce_commit_state(prior_commit)

        history_assignments = self.get_recent_assignments(
            evaluation.session_id, policy.lookback_n
        )
        history_evaluations = self.get_recent_evaluations(
            evaluation.session_id, policy.lookback_n
        )

        assignment = plan_next_v0_6(
            evaluation,
            feedback,
            history_assignments=history_assignments,
            history_evaluations=history_evaluations,
            prior_commit_state=reduced_commit,
            policy=policy,
        )

        self.append_evaluation(evaluation)
        self.append_assignment(assignment)

        return assignment


__all__ = [
    "SqliteStoreConfigV0_8",
    "SQLiteCoachStoreV0_8",
]
