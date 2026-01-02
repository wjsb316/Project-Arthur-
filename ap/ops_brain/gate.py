"""OpsBrain gate for permission-aware actions.

This gate checks persisted permission requests before allowing side-effectful
actions to proceed. It fails closed when the request is missing, expired, or
not approved.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..persistence.permissions import PermissionRepository


class OpsBrainGate:
    """Permission gate that consults persisted OpsBrain decisions."""

    def __init__(self, repository: PermissionRepository) -> None:
        self._repository = repository

    def allow_action(self, request_id: str | None) -> bool:
        if not request_id:
            return False

        record = self._repository.get_request(request_id)
        if record is None:
            return False

        if record.status != "approved":
            return False

        if datetime.now(timezone.utc) >= record.expires_at:
            return False

        return True


__all__ = ["OpsBrainGate"]
