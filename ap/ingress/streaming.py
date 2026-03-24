"""Streaming ingress for user utterances backed by the model provider."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from jsonschema import ValidationError

from ..protocol.validator import validate_message
from ..models import ModelProvider, ProviderHealth
from ..memory import MemoryStore
from ..persistence.chat import ChatStore
from ..agent.graph import build_agent_graph, StreamManager
from ..personal_brain import PersonalBrain
from ..persistence.audit import AuditLog
from ..models.users import User as UserRecord
from .auth import get_current_user
from ..database import get_session_maker

MAX_UTTERANCE_LENGTH = 2048

logger = logging.getLogger("arthur.ap.streaming")


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


def build_streaming_router(
    provider: ModelProvider,
    memory_store: MemoryStore,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
) -> APIRouter:
    """Build and configure the streaming ingress router."""
    router = APIRouter(prefix="/stream/v1")
    manager = StreamManager(provider)
    
    session_factory = get_session_maker()
    chat_store = ChatStore(session_factory)
    
    agent_graph = build_agent_graph(
        memory_store, 
        chat_store,
        provider,
        personal_brain,
        audit_log,
        manager
    )

    @router.post("/user-utterance")
    async def user_utterance(
        message: Dict[str, Any] = Body(...),
        current_user: UserRecord = Depends(get_current_user),
    ) -> StreamingResponse:
        """Handle incoming user speech/text and stream back assistant response.
        
        Process:
        1. Validate schema and payload.
        2. Check model provider health.
        3. Store user input in Chat History (Closed Loop).
        4. Use LangGraph agent to retrieve memory & chat history context.
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

        # 1. Get/Create Session & Save User Message (Closed Loop)
        session_id = None
        try:
            session_id = await chat_store.get_or_create_recent_session(
                current_user.user_id, 
                title_hint=text
            )
            # Save User Message with Embedding
            await chat_store.save_message(
                session_id=session_id,
                user_id=current_user.user_id,
                role="user",
                content=text
            )
        except Exception as e:
            logger.error(f"Failed to save user message/session: {e}")
            # Proceeding without session linkage if DB fails, but logging it.

        # Execute LangGraph for Context Retrieval and Generation Setup
        initial_state = {
            "user_input": text,
            "user_id": current_user.user_id,
            "session_id": session_id,
            "trace_id": trace_id,
            "stream_id": message["id"],
            "memories": [],
            "chat_history": [],
            "current_session_history": [],
            "agents": [],
            "final_prompt": "",
            "response_generator": None
        }
        
        final_state = await agent_graph.ainvoke(initial_state)

        audit_log.append(
            "assistant_stream_start",
            severity="info",
            trace_id=trace_id,
            details={"stream_id": message["id"], "user_id": current_user.user_id},
        )

        generator = final_state.get("response_generator")
        if not generator:
             logger.error("Graph did not return a response generator")
             raise HTTPException(status_code=500, detail="Internal processing error")

        return StreamingResponse(generator, media_type="application/json")

    @router.post("/interrupt")
    async def interrupt(
        message: Dict[str, Any] = Body(...),
        current_user: UserRecord = Depends(get_current_user),
    ) -> Dict[str, str]:
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
            details={"stream_id": stream_id, "user_id": current_user.user_id},
        )

        return {"status": "cancelled", "id": stream_id}

    return router


__all__ = ["build_streaming_router"]
