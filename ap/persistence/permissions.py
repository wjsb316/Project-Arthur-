"""SQLite persistence for permission requests and note delivery."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class PermissionRecord:
    request_id: str
    action: str
    client_label: str
    note: str
    risk_tier: str
    expires_at: datetime
    status: str


class PermissionRepository:
    """Persists permission requests and delivered notes."""

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
                CREATE TABLE IF NOT EXISTS permission_requests (
                    request_id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    client_label TEXT NOT NULL,
                    note TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS delivered_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    client_label TEXT NOT NULL,
                    note TEXT NOT NULL,
                    delivered_at INTEGER NOT NULL
                );
                """
            )
            conn.commit()

    def create_request(
        self,
        request_id: str,
        action: str,
        client_label: str,
        note: str,
        risk_tier: str,
        expires_at: datetime,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO permission_requests (request_id, action, client_label, note, risk_tier, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (request_id, action, client_label, note, risk_tier, int(expires_at.timestamp())),
            )
            conn.commit()

    def get_request(self, request_id: str) -> Optional[PermissionRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT request_id, action, client_label, note, risk_tier, expires_at, status
                FROM permission_requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if not row:
            return None
        return PermissionRecord(
            request_id=row[0],
            action=row[1],
            client_label=row[2],
            note=row[3],
            risk_tier=row[4],
            expires_at=datetime.fromtimestamp(row[5], tz=timezone.utc),
            status=row[6],
        )

    def set_status(self, request_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE permission_requests SET status=? WHERE request_id=?",
                (status, request_id),
            )
            conn.commit()

    def is_approved(self, request_id: str) -> bool:
        record = self.get_request(request_id)
        if record is None:
            return False
        if record.status != "approved":
            return False
        if datetime.now(timezone.utc) >= record.expires_at:
            return False
        return True

    def record_delivery(self, request_id: str, client_label: str, note: str) -> None:
        delivered_at = int(datetime.now(timezone.utc).timestamp())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO delivered_notes (request_id, client_label, note, delivered_at)
                VALUES (?, ?, ?, ?)
                """,
                (request_id, client_label, note, delivered_at),
            )
            conn.commit()

    def was_delivered(self, request_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM delivered_notes WHERE request_id=? LIMIT 1", (request_id,)
            ).fetchone()
        return bool(row)

