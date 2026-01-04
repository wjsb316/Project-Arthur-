"""Streaming ingress for user utterances backed by the model provider."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import StreamingResponse
from jsonschema import ValidationError

from ..protocol.validator import validate_message
from ..models import ModelProvider, ProviderHealth
from ..memory import MemoryStore, MemoryEntry
from ..friend_brain import FriendBrain
from ..persistence.audit import AuditLog

MAX_UTTERANCE_LENGTH = 2048
STREAM_DELAY_SECONDS = 0.01

logger = logging.getLogger("arthur.ap.streaming")


class StreamManager:
    """Tracks active streams and cancellation signals."""

    def __init__(self, provider: ModelProvider) -> None:
        self._cancellations: dict[str, asyncio.Event] = {}
        self._provider = provider

    def register(self, stream_id: str) -> asyncio.Event:
        """Register a new stream and return its cancellation event."""
        event = asyncio.Event()
        self._cancellations[stream_id] = event
        return event

    async def cancel(self, stream_id: str) -> bool:
        """Cancel an active stream by ID. Returns True if found."""
        event = self._cancellations.get(stream_id)
        if event:
            event.set()
            await self._provider.cancel(stream_id)
            return True
        return False

    def cleanup(self, stream_id: str) -> None:
        """Remove a stream from tracking."""
        self._cancellations.pop(stream_id, None)


@dataclass
class StreamState:
    """Context for an active assistant response stream."""
    stream_id: str
    trace_id: str | None
    text: str


async def _assistant_stream(
    state: StreamState,
    cancel_event: asyncio.Event,
    manager: StreamManager,
    provider: ModelProvider,
    friend_brain: FriendBrain,
    audit_log: AuditLog,
) -> AsyncGenerator[str, None]:
    """Orchestrates the streaming response generation.
    
    1. Streams raw tokens from the provider.
    2. Wraps tokens in protocol messages (assistant_delta).
    3. Accumulates text for final tone analysis.
    4. Emits a final completion message (assistant_final).
    """
    start_time = time.perf_counter()
    tokens: list[str] = []
    try:
        async for index, token in _enumerate_provider_stream(
            provider.stream(state.stream_id, state.text, cancel_event), cancel_event
        ):
            if cancel_event.is_set():
                break
            tokens.append(token)
            delta = {
                "id": state.stream_id,
                "type": "tool",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stream": True,
                "delta_index": index,
                "payload": {
                    "name": "assistant_delta",
                    "args": {
                        "text": token,
                        "confidence": 0.5,
                        "model_health": "ok",
                        "trace_id": state.trace_id,
                    },
                },
            }
            validate_message(delta)
            yield json.dumps(delta) + "\n"

        if cancel_event.is_set():
            return

        final_text = "".join(tokens) if tokens else state.text
        toned_text = friend_brain.apply_tone(final_text)
        confidence, model_health = await _build_confidence_and_health(provider)
        final = {
            "id": state.stream_id,
            "type": "tool",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stream": True,
            "complete": True,
            "payload": {
                "name": "assistant_final",
                "args": {
                    "text": toned_text,
                    "confidence": confidence,
                    "model_health": model_health,
                    "trace_id": state.trace_id,
                },
            },
        }
        validate_message(final)
        yield json.dumps(final) + "\n"
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "assistant_stream_latency_ms",
            extra={
                "event": "assistant_stream_latency",
                "stream_id": state.stream_id,
                "latency_ms": round(latency_ms, 2),
            },
        )
        manager.cleanup(state.stream_id)


async def _enumerate_provider_stream(
    generator: AsyncGenerator[str, None], cancel_event: asyncio.Event
) -> AsyncGenerator[tuple[int, str], None]:
    index = 0
    async for token in generator:
        yield index, token
        index += 1
        if cancel_event.is_set():
            break


def _ensure_provider_ready(health: ProviderHealth, audit_log: AuditLog, trace_id: str | None) -> None:
    if health.status != "ok":
        event = "ap_offline" if health.status == "down" else "model_degraded"
        severity = "error" if health.status == "down" else "warning"
        logger.info(
            "ap_event",
            extra={
                "event": event,
                "severity": severity,
                "trace_id": trace_id,
                "reason": health.reason,
            },
        )
        audit_log.append(
            event,
            severity=severity,
            trace_id=trace_id,
            details={"status": health.status, "reason": health.reason},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "model_unavailable", "reason": health.reason or "model unavailable"},
        )


def _compact_context(entries: list[MemoryEntry]) -> str:
    if not entries:
        return ""
    snippets = [f"- ({entry.kind}) {entry.content}" for entry in entries]
    return "Context:\n" + "\n".join(snippets) + "\n"


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def _confidence_level(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"


async def _build_confidence_and_health(provider: ModelProvider) -> tuple[dict[str, Any], dict[str, Any]]:
    health = await provider.health_check()
    latency_ms = health.latency_ms or 0.0
    base_score = 0.9 if health.status == "ok" else 0.3
    adjusted = base_score - min(latency_ms, 1500) / 3000
    score = _clamp_score(adjusted)
    confidence = {"score": score, "level": _confidence_level(score)}
    model_health = {
        "provider": provider.__class__.__name__,
        "status": health.status,
        "metrics": health.metrics or {"latency_ms": latency_ms},
    }
    return confidence, model_health


def build_streaming_router(
    provider: ModelProvider,
    memory_store: MemoryStore,
    friend_brain: FriendBrain,
    audit_log: AuditLog,
) -> APIRouter:
    """Build and configure the streaming ingress router."""
    router = APIRouter(prefix="/stream/v1")
    manager = StreamManager(provider)

    @router.post("/user-utterance")
    async def user_utterance(message: Dict[str, Any] = Body(...)) -> StreamingResponse:
        """Handle incoming user speech/text and stream back assistant response.
        
        Process:
        1. Validate schema and payload.
        2. Check model provider health.
        3. Retrieve relevant memory context.
        4. Store user input in short-term memory.
        5. Stream response via Server-Sent Events (SSE) logic over JSON-lines.
        """
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "user_utterance":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected user_utterance"},
            )

        args = payload.get("args", {}) or {}
        text = args.get("text") or ""
        trace_id = args.get("trace_id") or message.get("id")
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_text", "reason": "text is required"},
            )
        if len(text) > MAX_UTTERANCE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "utterance_too_long", "reason": "utterance exceeds limit"},
            )

        _ensure_provider_ready(await provider.health_check(), audit_log, trace_id)

        retrieved = memory_store.retrieve_relevant(text, limit=5)
        context = _compact_context(retrieved)
        prompt_text = f"{context}User: {text}" if context else text
        memory_store.store_open_loop(text)

        audit_log.append(
            "assistant_stream_start",
            severity="info",
            trace_id=trace_id,
            details={"stream_id": message["id"]},
        )

        state = StreamState(stream_id=message["id"], trace_id=trace_id, text=prompt_text)
        cancel_event = manager.register(state.stream_id)
        generator = _assistant_stream(state, cancel_event, manager, provider, friend_brain, audit_log)
        return StreamingResponse(generator, media_type="application/json")

    @router.post("/interrupt")
    async def interrupt(message: Dict[str, Any] = Body(...)) -> Dict[str, str]:
        """Interrupt an active stream by ID."""
        try:
            validate_message(message)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "schema_validation_failed", "reason": exc.message},
            ) from exc

        payload = message.get("payload", {})
        if payload.get("name") != "interrupt":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "reason": "expected interrupt"},
            )

        args = payload.get("args", {}) or {}
        stream_id = args.get("stream_id") or message.get("id")
        trace_id = args.get("trace_id") or stream_id
        if not stream_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "missing_stream", "reason": "stream_id is required"},
            )

        cancelled = await manager.cancel(stream_id)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "stream_not_found", "reason": "unknown stream"},
            )

        logger.info(
            "ap_event",
            extra={"event": "assistant_stream_interrupt", "severity": "info", "stream_id": stream_id},
        )

        audit_log.append(
            "assistant_stream_interrupt",
            severity="info",
            trace_id=trace_id,
            details={"stream_id": stream_id},
        )

        return {"status": "cancelled", "id": stream_id}

    return router


__all__ = ["build_streaming_router"]
