"""WebSocket gateway for Arthur Prime.

This endpoint accepts JSON-line framed protocol messages and validates them
against the Arthur protocol v1.1 schema. It fails closed on malformed JSON or
schema violations.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Iterable

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from jsonschema import ValidationError

from ..protocol.validator import validate_message


def _iter_lines(message: str) -> Iterable[str]:
    for line in message.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def build_gateway_router() -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/v1")
    async def websocket_gateway(websocket: WebSocket) -> None:  # pragma: no cover - exercised via tests
        await websocket.accept()
        while True:
            try:
                text = await websocket.receive_text()
            except WebSocketDisconnect:
                return
            except Exception:  # noqa: BLE001
                await websocket.close(code=1002)
                return

            for line in _iter_lines(text):
                try:
                    payload = json.loads(line)
                except JSONDecodeError:
                    await websocket.close(code=1003, reason="invalid_json")
                    return

                if not isinstance(payload, dict):
                    await websocket.close(code=1003, reason="invalid_message")
                    return

                if not all(key in payload for key in ("id", "type", "timestamp", "payload")):
                    await websocket.close(code=1003, reason="missing_fields")
                    return

                try:
                    validate_message(payload)
                except ValidationError:
                    await websocket.close(code=1003, reason="invalid_schema")
                    return

    return router


__all__ = ["build_gateway_router"]

