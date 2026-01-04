"""SQLite persistence for pairing requests and device registry."""

from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class PairingRecord:
    """Represents a pending pairing request."""
    pair_request_id: str
    pair_code: str
    device_id: str
    expires_at: datetime
    status: str


@dataclass
class DeviceRegistryRecord:
    """Represents a paired device and its capabilities."""
    device_id: str
    client_label: str
    role: str
    session_id: str
    session_bootstrap_token: str
    last_seen: datetime | None
    capabilities: list[str]


@dataclass
class SessionRecord:
    """Represents an active authenticated session."""
    session_id: str
    device_id: str
    expires_at: datetime


class PairingRepository:
    """Stores pending pairing requests and device registry records.
    
    Manages the lifecycle of device pairing:
    1. Pending Pair: Initial request with a short-lived code.
    2. Device Registry: Long-lived record of a paired device.
    3. Session: Active authenticated session for a device.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_pairs (
                    pair_request_id TEXT PRIMARY KEY,
                    pair_code TEXT NOT NULL UNIQUE,
                    device_id TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_registry (
                    device_id TEXT PRIMARY KEY,
                    client_label TEXT NOT NULL,
                    role TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    session_bootstrap_token TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_seen INTEGER,
                    capabilities TEXT
                );
                """
            )
            self._ensure_device_registry_columns(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                """
            )
            conn.commit()

    def _ensure_device_registry_columns(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(device_registry);")
        existing = {row[1] for row in cursor.fetchall()}
        migrations: list[tuple[str, str]] = []
        if "session_bootstrap_token" not in existing:
            migrations.append(("session_bootstrap_token", "TEXT NOT NULL DEFAULT ''"))
        if "last_seen" not in existing:
            migrations.append(("last_seen", "INTEGER"))
        if "capabilities" not in existing:
            migrations.append(("capabilities", "TEXT"))

        for column, definition in migrations:
            conn.execute(f"ALTER TABLE device_registry ADD COLUMN {column} {definition};")

    def add_pending(
        self,
        pair_request_id: str,
        pair_code: str,
        device_id: str,
        expires_at: datetime,
    ) -> None:
        """Create a new pending pairing request."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pending_pairs (pair_request_id, pair_code, device_id, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (pair_request_id, pair_code, device_id, int(expires_at.timestamp())),
            )
            conn.commit()

    def list_pending(self) -> Iterable[PairingRecord]:
        """List all currently pending pairing requests."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT pair_request_id, pair_code, device_id, expires_at, status
                FROM pending_pairs
                WHERE status = 'pending'
                ORDER BY expires_at ASC
                """
            )
            rows = cursor.fetchall()
        return (
            PairingRecord(
                pair_request_id=row[0],
                pair_code=row[1],
                device_id=row[2],
                expires_at=datetime.fromtimestamp(row[3], tz=timezone.utc),
                status=row[4],
            )
            for row in rows
        )

    def approve(self, identifier: str) -> bool:
        """Approve a pairing request by ID or code."""
        return self._update_status(identifier, "approved")

    def deny(self, identifier: str) -> bool:
        """Deny a pairing request by ID or code."""
        return self._update_status(identifier, "denied")

    def _update_status(self, identifier: str, status: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE pending_pairs
                SET status = ?
                WHERE pair_request_id = ? OR pair_code = ?
                """,
                (status, identifier, identifier),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_by_request_id(self, pair_request_id: str) -> Optional[PairingRecord]:
        """Retrieve a specific pairing request."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT pair_request_id, pair_code, device_id, expires_at, status
                FROM pending_pairs
                WHERE pair_request_id = ?
                """,
                (pair_request_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return PairingRecord(
                pair_request_id=row[0],
                pair_code=row[1],
                device_id=row[2],
                expires_at=datetime.fromtimestamp(row[3], tz=timezone.utc),
                status=row[4],
            )

    def get_device_by_bootstrap(self, token: str) -> Optional[DeviceRegistryRecord]:
        """Find a device by its bootstrap token."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT device_id, client_label, role, session_id, session_bootstrap_token, created_at, last_seen, capabilities
                FROM device_registry
                WHERE session_bootstrap_token = ?
                """,
                (token,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            capabilities = json.loads(row[7]) if row[7] else []
            last_seen = datetime.fromtimestamp(row[6], tz=timezone.utc) if row[6] else None
            return DeviceRegistryRecord(
                device_id=row[0],
                client_label=row[1],
                role=row[2],
                session_id=row[3],
                session_bootstrap_token=row[4],
                last_seen=last_seen,
                capabilities=capabilities,
            )

    def update_device_seen(self, device_id: str, capabilities: list[str]) -> None:
        """Update the last_seen timestamp and capabilities for a device."""
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE device_registry
                SET last_seen = ?, capabilities = ?
                WHERE device_id = ?
                """,
                (timestamp, json.dumps(capabilities), device_id),
            )
            conn.commit()

    def create_session(self, session_id: str, device_id: str, expires_at: datetime) -> None:
        """Create or update a session for a device."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (session_id, device_id, expires_at)
                VALUES (?, ?, ?)
                """,
                (session_id, device_id, int(expires_at.timestamp())),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Retrieve session details by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT session_id, device_id, expires_at
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return SessionRecord(
                session_id=row[0],
                device_id=row[1],
                expires_at=datetime.fromtimestamp(row[2], tz=timezone.utc),
            )

    def refresh_session(self, session_id: str, expires_at: datetime) -> None:
        """Extend the expiration time of a session."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET expires_at = ?
                WHERE session_id = ?
                """,
                (int(expires_at.timestamp()), session_id),
            )
            conn.commit()

    def mark_completed(
        self,
        pair_request_id: str,
        client_label: str,
        role: str,
        session_id: str,
        session_bootstrap_token: str,
    ) -> None:
        """Finalize pairing: update request status and create device registry entry."""
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_pairs
                SET status = 'completed'
                WHERE pair_request_id = ?
                """,
                (pair_request_id,),
            )
            conn.execute(
                """
                INSERT INTO device_registry (device_id, client_label, role, session_id, session_bootstrap_token, created_at)
                SELECT device_id, ?, ?, ?, ?, ?
                FROM pending_pairs
                WHERE pair_request_id = ?
                ON CONFLICT(device_id) DO UPDATE SET
                    client_label=excluded.client_label,
                    role=excluded.role,
                    session_id=excluded.session_id,
                    session_bootstrap_token=excluded.session_bootstrap_token,
                    created_at=excluded.created_at
                """,
                (
                    client_label,
                    role,
                    session_id,
                    session_bootstrap_token,
                    timestamp,
                    pair_request_id,
                ),
            )
            conn.commit()
