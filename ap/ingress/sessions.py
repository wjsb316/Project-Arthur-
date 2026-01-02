"""Session authentication endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import anyio
from fastapi import APIRouter, Body, HTTPException, status
from jsonschema import ValidationError

from ..persistence.pairing import PairingRepository
from ..protocol.validator import validate_message

logger = logging.getLogger("arthur.ap.sessions")


def build_sessions_router(pairing_repository: PairingRepository) -> APIRouter:
    router = APIRouter(prefix="/session/v1")

    @router.post("/client-hello")
    async def client_hello(message: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "client_hello":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected client_hello"},
            )

        args = payload.get("args", {})
        token = args.get("session_bootstrap_token")
        device_id = args.get("device_id")
        capabilities = args.get("capabilities", []) or []
        if not token or not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_fields", "reason": "token and device_id required"},
            )

        record = await anyio.to_thread.run_sync(pairing_repository.get_device_by_bootstrap, token)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_token", "reason": "token not recognized"},
            )

        if device_id != record.device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "device_mismatch", "reason": "device does not match token"},
            )

        session_id = record.session_id or str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)

        await anyio.to_thread.run_sync(
            pairing_repository.create_session, session_id, record.device_id, expires_at
        )
        await anyio.to_thread.run_sync(
            pairing_repository.update_device_seen, record.device_id, list(capabilities)
        )

        logger.info(
            "ap_event", extra={"event": "ap_online", "severity": "info", "device_id": record.device_id}
        )

        response_message = {
            "id": message.get("id", session_id),
            "type": "tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream": False,
            "ack": True,
            "payload": {
                "name": "server_hello",
                "args": {
                    "protocol_version": "1.1",
                    "session_id": session_id,
                    "expires_in_sec": 3600,
                },
            },
        }
        validate_message(response_message)
        return response_message

    @router.post("/refresh")
    async def session_refresh(message: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "session_refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected session_refresh"},
            )

        args = payload.get("args", {})
        session_id = args.get("session_id")
        device_id = args.get("device_id")
        capabilities = args.get("capabilities", []) or []

        if not session_id or not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_fields", "reason": "session_id and device_id required"},
            )

        record = await anyio.to_thread.run_sync(pairing_repository.get_session, session_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "session_not_found", "reason": "session unknown"},
            )

        if record.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "device_mismatch", "reason": "device does not match session"},
            )

        now = datetime.now(timezone.utc)
        if now >= record.expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"error": "expired", "reason": "session expired"},
            )

        new_expires_at = now + timedelta(seconds=3600)

        await anyio.to_thread.run_sync(
            pairing_repository.refresh_session, record.session_id, new_expires_at
        )
        await anyio.to_thread.run_sync(
            pairing_repository.update_device_seen, record.device_id, list(capabilities)
        )

        logger.info(
            "ap_event",
            extra={"event": "session_refresh", "severity": "info", "device_id": record.device_id},
        )

        response_message = {
            "id": message.get("id", record.session_id),
            "type": "tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream": False,
            "ack": True,
            "payload": {
                "name": "session_refresh",
                "args": {
                    "session_id": record.session_id,
                    "expires_in_sec": 3600,
                },
            },
        }
        validate_message(response_message)
        return response_message

    return router


__all__ = ["build_sessions_router"]
