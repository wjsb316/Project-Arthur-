"""OpsBrain policy and permission flow endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, status
from jsonschema import ValidationError

from ..protocol.validator import validate_message
from ..persistence.permissions import PermissionRepository

logger = logging.getLogger("arthur.ap.ops")

DEFAULT_TIMEOUT = 15


def _risk_tier_for_action(action: str) -> str:
    # All side-effect actions are treated as high risk until policy is expanded.
    return "high"


def build_ops_router(permission_repository: PermissionRepository) -> APIRouter:
    router = APIRouter(prefix="/ops/v1")

    @router.post("/side-effect")
    async def request_side_effect(message: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "send_note":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected send_note"},
            )

        args = payload.get("args", {}) or {}
        note = args.get("note")
        client_label = args.get("client_label")
        timeout_sec = max(0, int(args.get("timeout_sec", DEFAULT_TIMEOUT)))

        if not note or not client_label:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_fields", "reason": "note and client_label required"},
            )

        risk_tier = _risk_tier_for_action("send_note")
        request_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_sec)

        permission_repository.create_request(
            request_id=request_id,
            action="send_note",
            client_label=client_label,
            note=note,
            risk_tier=risk_tier,
            expires_at=expires_at,
        )

        response = {
            "id": message.get("id", request_id),
            "type": "tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream": False,
            "ack": True,
            "payload": {
                "name": "permission_request",
                "args": {
                    "request_id": request_id,
                    "risk_tier": risk_tier,
                    "action": "send_note",
                    "client_label": client_label,
                    "expires_in_sec": timeout_sec,
                },
            },
        }
        validate_message(response)
        logger.info(
            "ap_event",
            extra={
                "event": "permission_request",
                "severity": "info",
                "request_id": request_id,
                "risk_tier": risk_tier,
            },
        )
        return response

    @router.post("/permission-response")
    async def permission_response(message: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "permission_response":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected permission_response"},
            )

        args = payload.get("args", {}) or {}
        request_id = args.get("request_id")
        decision = (args.get("decision") or "").lower()

        if not request_id or decision not in {"yes", "no"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_fields", "reason": "request_id and decision yes/no required"},
            )

        record = permission_repository.get_request(request_id)
        if record is None:
            logger.warning(
                "ap_event",
                extra={"event": "permission_unknown", "severity": "warning", "request_id": request_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "unknown_request", "reason": "request not found"},
            )

        now = datetime.now(timezone.utc)
        if now >= record.expires_at:
            permission_repository.set_status(request_id, "expired")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "permission_expired", "reason": "request expired"},
            )

        if decision == "no":
            permission_repository.set_status(request_id, "denied")
            logger.info(
                "ap_event",
                extra={"event": "permission_denied", "severity": "info", "request_id": request_id},
            )
        else:
            permission_repository.set_status(request_id, "approved")
            permission_repository.record_delivery(request_id, record.client_label, record.note)
            logger.info(
                "ap_event",
                extra={
                    "event": "note_delivery",
                    "severity": "info",
                    "request_id": request_id,
                    "client_label": record.client_label,
                },
            )

        response = {
            "id": message.get("id", request_id),
            "type": "tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream": False,
            "ack": True,
            "payload": {
                "name": "permission_response",
                "args": {"request_id": request_id, "decision": decision},
            },
        }
        validate_message(response)
        return response

    return router


__all__ = ["build_ops_router"]
