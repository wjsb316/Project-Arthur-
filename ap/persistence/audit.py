"""Append-only audit log persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models.audit import AuditLogEntry


class AuditLog:
    """Append-only audit log backed by SQLAlchemy.
    
    This log tracks system events for observability, security, and debugging.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def append(
        self,
        event: str,
        *,
        severity: str = "info",
        trace_id: str | None = None,
        details: dict | None = None,
    ) -> int:
        """Record a new event in the audit log."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            entry = AuditLogEntry(
                event=event,
                severity=severity,
                trace_id=trace_id,
                details=details, # Model property setter handles JSON conversion
                created_at=now
            )
            session.add(entry)
            await session.commit()
            return entry.id

    async def list_entries(self, limit: int = 200) -> List[AuditLogEntry]:
        """Retrieve recent audit entries."""
        async with self._session_factory() as session:
            stmt = select(AuditLogEntry).order_by(desc(AuditLogEntry.id)).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
