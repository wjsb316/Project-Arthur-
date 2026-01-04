"""Audit export endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..persistence.audit import AuditLog


def build_audit_router(audit_log: AuditLog) -> APIRouter:
    """Build the audit data router.
    
    Provides endpoints for observability and debugging of the system log.
    """
    router = APIRouter(prefix="/audit/v1")

    @router.get("/export")
    async def export() -> dict:
        """Export all audit log entries."""
        entries = audit_log.list_entries()
        return {
            "entries": [
                {
                    "id": entry.id,
                    "event": entry.event,
                    "severity": entry.severity,
                    "trace_id": entry.trace_id,
                    "details": entry.details,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in entries
            ]
        }

    return router


__all__ = ["build_audit_router"]
