"""SQLAlchemy persistence for permission requests and note delivery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models.professional import PermissionRequest, DeliveredNote


class PermissionRepository:
    """Persists permission requests and delivered notes using SQLAlchemy."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_request(
        self,
        request_id: str,
        action: str,
        client_label: str,
        note: str,
        risk_tier: str,
        expires_at: datetime,
    ) -> None:
        """Create a new permission request."""
        async with self._session_factory() as session:
            req = PermissionRequest(
                request_id=request_id,
                action=action,
                client_label=client_label,
                note=note,
                risk_tier=risk_tier,
                expires_at=expires_at,
                status="pending"
            )
            session.add(req)
            await session.commit()

    async def get_request(self, request_id: str) -> Optional[PermissionRequest]:
        """Retrieve a permission request by ID."""
        async with self._session_factory() as session:
            stmt = select(PermissionRequest).where(PermissionRequest.request_id == request_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_status(self, request_id: str, status: str) -> None:
        """Update the status of a permission request (e.g., 'approved', 'denied')."""
        async with self._session_factory() as session:
            stmt = select(PermissionRequest).where(PermissionRequest.request_id == request_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            
            if record:
                record.status = status
                await session.commit()

    async def is_approved(self, request_id: str) -> bool:
        """Check if a specific request is currently approved and valid."""
        record = await self.get_request(request_id)
        if record is None:
            return False
        if record.status != "approved":
            return False
        if datetime.now(timezone.utc) >= record.expires_at:
            return False
        return True

    async def record_delivery(self, request_id: str, client_label: str, note: str) -> None:
        """Record that a notification note was delivered to a client."""
        delivered_at = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            delivery = DeliveredNote(
                request_id=request_id,
                client_label=client_label,
                note=note,
                delivered_at=delivered_at
            )
            session.add(delivery)
            await session.commit()

    async def was_delivered(self, request_id: str) -> bool:
        """Check if a note for this request has already been delivered."""
        async with self._session_factory() as session:
            stmt = select(DeliveredNote).where(DeliveredNote.request_id == request_id).limit(1)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
