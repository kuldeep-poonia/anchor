"""Lightweight SQLite database for action auditing and approval states."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anchor.actions.models import Action
from anchor.policy.engine import PolicyDecision


class AuditDatabase:
    """Manages local SQLite audit history and pending approval states."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create sqlite connection with row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema using parameterized execution."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    action_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    content TEXT,
                    decision TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verified INTEGER DEFAULT 0,
                    snapshot_id TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contracts (
                    contract_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    contract_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def record_decision(
        self,
        action: Action,
        decision: PolicyDecision,
        status: str,
        snapshot_id: str | None = None,
    ) -> None:
        """Record an evaluated action and its policy decision."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_log (
                    action_id, timestamp, action_type, target, content,
                    decision, risk_level, reason, status, verified, snapshot_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.id,
                    datetime.now(timezone.utc).isoformat(),
                    action.type.value,
                    action.target,
                    action.content,
                    decision.decision.value,
                    decision.risk_level.value,
                    decision.reason,
                    status,
                    0,
                    snapshot_id,
                ),
            )
            conn.commit()

    def update_status(
        self,
        action_id: str,
        status: str,
        verified: bool = False,
        snapshot_id: str | None = None,
    ) -> None:
        """Update action status, verification outcome, and snapshot reference."""
        with self._get_connection() as conn:
            if snapshot_id:
                conn.execute(
                    """
                    UPDATE audit_log
                    SET status = ?, verified = ?, snapshot_id = ?
                    WHERE action_id = ?
                    """,
                    (status, 1 if verified else 0, snapshot_id, action_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE audit_log
                    SET status = ?, verified = ?
                    WHERE action_id = ?
                    """,
                    (status, 1 if verified else 0, action_id),
                )
            conn.commit()

    def get_action(self, action_id: str) -> dict[str, Any] | None:
        """Retrieve action details by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE action_id = ?",
                (action_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """List all actions currently waiting for user approval."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE status = 'PENDING_APPROVAL' ORDER BY timestamp ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_actions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent actions from audit log."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def record_contract(self, contract_id: str, goal: str, contract_json: str) -> None:
        """Store active contract configuration."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contracts (contract_id, timestamp, goal, contract_json)
                VALUES (?, ?, ?, ?)
                """,
                (contract_id, datetime.now(timezone.utc).isoformat(), goal, contract_json),
            )
            conn.commit()
