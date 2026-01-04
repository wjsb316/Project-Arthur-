"""Append-only audit log persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AuditEntry:
    """Immutable record of a single audit event."""
    id: int
    event: str
    severity: str
    trace_id: str | None
    details: dict | None
    created_at: datetime


class AuditLog:
    """Append-only audit log backed by SQLite.
    
    This log tracks system events for observability, security, and debugging.
    It is designed to be immutable (no update/delete methods exposed).
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    trace_id TEXT,
                    details TEXT,
                    created_at INTEGER NOT NULL
                );
                """
            )
            conn.commit()

    def append(
        self,
        event: str,
        *,
        severity: str = "info",
        trace_id: str | None = None,
        details: dict | None = None,
    ) -> int:
        """Record a new event in the audit log."""
        payload = json.dumps(details) if details is not None else None
        timestamp = int(datetime.now(timezone.utc).timestamp())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log (event, severity, trace_id, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event, severity, trace_id, payload, timestamp),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_entries(self, limit: int = 200) -> Iterable[AuditEntry]:
        """Retrieve recent audit entries."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event, severity, trace_id, details, created_at
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        details = json.loads(row[4]) if row[4] else None
        created_at = datetime.fromtimestamp(row[5], tz=timezone.utc)
        return AuditEntry(
            id=row[0],
            event=row[1],
            severity=row[2],
            trace_id=row[3],
            details=details,
            created_at=created_at,
        )
