"""ProfessionalBrain gate for permission-aware actions.

This gate checks persisted permission requests before allowing side-effectful
actions to proceed. It fails closed when the request is missing, expired, or
not approved.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..persistence.permissions import PermissionRepository


class ProfessionalBrainGate:
    """Permission gate that consults persisted ProfessionalBrain decisions.
    
    The ProfessionalBrain is responsible for safety and permissions. This Gate class
    provides a synchronous/fast check against the permission repository to
    determine if a specific action (tied to a request ID) is currently allowed.
    """

    def __init__(self, repository: PermissionRepository) -> None:
        self._repository = repository

    async def allow_action(self, request_id: str | None) -> bool:
        """Check if an action request is approved and active.
        
        Returns True ONLY if:
        1. request_id is provided.
        2. record exists in repository.
        3. status is 'approved'.
        4. expiration time has not passed.
        """
        if not request_id:
            return False

        record = await self._repository.get_request(request_id)
        if record is None:
            return False

        if record.status != "approved":
            return False

        if datetime.now(timezone.utc) >= record.expires_at:
            return False

        return True


__all__ = ["ProfessionalBrainGate"]
