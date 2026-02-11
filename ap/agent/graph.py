"""LangGraph agent for orchestrating context retrieval, agent bundling, and response generation."""

from __future__ import annotations

import logging
import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TypedDict, List, Annotated, Any, AsyncGenerator, Dict, Optional, NotRequired
import operator

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import select

from ..memory.store import MemoryEntry, MemoryStore
from ..persistence.chat import ChatStore
from ..persistence.retrieval import VectorRetriever
from ..models.chat import ChatMessage
from ..models.agents import Agent
from ..models.guardrails import Guardrail
from ..database import get_session_maker
from ..models import ModelProvider, ProviderHealth
from ..personal_brain import PersonalBrain
from ..persistence.audit import AuditLog
from ..protocol.validator import validate_message

logger = logging.getLogger("arthur.ap.agent.graph")


# --- Streaming Utilities (Moved from streaming.py) ---

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
    user_id: str | None = None
    session_id: int | None = None
    chat_store: ChatStore | None = None


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


async def _enumerate_provider_stream(
    generator: AsyncGenerator[str, None], cancel_event: asyncio.Event
) -> AsyncGenerator[tuple[int, str], None]:
    index = 0
    async for token in generator:
        yield index, token
        index += 1
        if cancel_event.is_set():
            break


async def _assistant_stream(
    state: StreamState,
    cancel_event: asyncio.Event,
    manager: StreamManager,
    provider: ModelProvider,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
) -> AsyncGenerator[str, None]:
    """Orchestrates the streaming response generation."""
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
        # toned_text = personal_brain.apply_tone(final_text)
        toned_text = final_text

        # Closed Loop: Save response to ChatStore
        if state.chat_store and state.session_id and state.user_id:
            try:
                await state.chat_store.save_message(
                    session_id=state.session_id,
                    user_id=state.user_id,
                    role="Arthur",
                    content=toned_text
                )
                logger.info(f"Saved assistant response for session {state.session_id}")
            except Exception as e:
                logger.error(f"Failed to save assistant message: {e}")

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


# --- Graph Logic ---

# Default system prompt for voice/TTS mode when none is configured.
DEFAULT_VOICE_SYSTEM_PROMPT = (
    "You are in a voice conversation. Your reply will be read aloud by text-to-speech. "
    "Keep responses concise and natural for speaking; avoid long lists, markdown formatting, "
    "or content that does not translate well to speech."
    "You will optimize all responses to be formatted for text to speech." 
    "This means no Emojis, and no characters that would need to be read to understood." 
    "Keep all characters to those that provide tangible meaning when spoken." 
    "All numbers should be converted to word representation (i.e. 9,100 = nine thousand one hundred) before being returned."
)


class AgentState(TypedDict):
    """State of the agent workflow."""
    user_input: str
    user_id: str
    session_id: int | None
    trace_id: str
    stream_id: str
    is_voice: NotRequired[bool]  # True when input was voice and output will be TTS

    # Retrieved context
    memories: List[MemoryEntry]
    chat_history: List[dict]  # Vector-similar messages from any session
    current_session_history: List[dict]  # Full conversation in current session
    agents: List[dict]
    guardrails: List[dict]

    # Final output
    final_prompt: str
    response_generator: Optional[AsyncGenerator[str, None]]


async def retrieve_memories(state: AgentState, memory_store: MemoryStore) -> dict:
    """Node: Retrieve relevant long-term memories."""
    try:
        memories = await memory_store.retrieve_relevant(
            state["user_input"], 
            state["user_id"], 
            limit=5
        )
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        return {"memories": []}


async def retrieve_history(state: AgentState, chat_store: ChatStore) -> dict:
    """Node: Retrieve (1) full current session history and (2) relevant past context via vector search."""
    out: dict = {"chat_history": [], "current_session_history": []}
    try:
        # 1. Vector-similar messages from other sessions only (exclude current to avoid duplication)
        history = await chat_store.retrieve_relevant_history(
            state["user_input"],
            state["user_id"],
            limit=5,
            exclude_session_id=state.get("session_id"),
        )
        out["chat_history"] = history

        # 2. Full conversation in current session
        session_id = state.get("session_id")
        if session_id:
            session_messages = await chat_store.get_session_messages(
                session_id, state["user_id"]
            )
            out["current_session_history"] = session_messages
    except Exception as e:
        logger.error(f"Chat history retrieval failed: {e}")
    return out


async def retrieve_agents(state: AgentState) -> dict:
    """Node: Retrieve all agents for the user."""
    try:
        session_factory = get_session_maker()
        async with session_factory() as session:
            stmt = select(Agent).where(Agent.user_id == state["user_id"])
            result = await session.execute(stmt)
            agents = result.scalars().all()
            # Convert to dicts for state
            agents_data = [
                {"name": a.name, "prompt": a.prompt} for a in agents
            ]
            return {"agents": agents_data}
    except Exception as e:
        logger.error(f"Agent retrieval failed: {e}")
        return {"agents": []}


async def retrieve_guardrails(state: AgentState) -> dict:
    """Node: Retrieve all guardrails for the user. All guardrails go to the LLM with every query; no similarity filtering."""
    try:
        session_factory = get_session_maker()
        async with session_factory() as session:
            stmt = select(Guardrail).where(Guardrail.user_id == state["user_id"])
            result = await session.execute(stmt)
            guardrails = result.scalars().all()
            guardrails_data = [{"name": g.name, "prompt": g.prompt} for g in guardrails]
            return {"guardrails": guardrails_data}
    except Exception as e:
        logger.error(f"Guardrail retrieval failed: {e}")
        return {"guardrails": []}


def _get_voice_system_prompt(voice_system_prompt: str | None) -> str:
    return (voice_system_prompt or DEFAULT_VOICE_SYSTEM_PROMPT).strip()


def bundle_context(state: AgentState, voice_system_prompt: str | None = None) -> dict:
    """Node: Format all context into a final prompt string."""
    parts = []

    # 0. Voice/TTS mode: prepend system instruction for the LLM
    if state.get("is_voice"):
        voice_instruction = _get_voice_system_prompt(voice_system_prompt)
        parts.append(f"System (voice/TTS): {voice_instruction}")

    # 1. Format Guardrails (these are constraints/rules that guide behavior)
    if state.get("guardrails"):
        guardrail_text = "\n".join([f"- {g['name']}: {g['prompt']}" for g in state["guardrails"]])
        parts.append(f"Active Guardrails (IMPORTANT - Follow these rules):\n{guardrail_text}")

    # 2. Format Agents
    if state.get("agents"):
        agent_text = "\n".join([f"Agent {a['name']}: {a['prompt']}" for a in state["agents"]])
        parts.append(f"Available Agents:\n{agent_text}")

    # 3. Format Memories
    if state.get("memories"):
        mem_text = "\n".join([f"- ({m.kind}) {m.content}" for m in state["memories"]])
        parts.append(f"Relevant Memories:\n{mem_text}")

    # 4. Current session conversation (full chat history for this session, including current user message)
    if state.get("current_session_history"):
        session_lines = [
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in state["current_session_history"]
        ]
        parts.append(f"Current conversation:\n" + "\n".join(session_lines))
    else:
        # No session (e.g. streaming without session) – add user input
        parts.append(f"User: {state['user_input']}")

    # 5. Relevant past context from vector similarity (other sessions)
    if state.get("chat_history"):
        contents = [m.get("content", "").strip() for m in state["chat_history"] if m.get("content")]
        if contents:
            hist_text = "\n".join(contents)
            parts.append(f"Relevant past context (from other conversations):\n{hist_text}")

    final_prompt = "\n\n".join(parts)
    return {"final_prompt": final_prompt}


def generate_response(
    state: AgentState,
    manager: StreamManager,
    provider: ModelProvider,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
    chat_store: ChatStore
) -> dict:
    """Node: Prepare the response generator."""
    # Register the stream
    cancel_event = manager.register(state["stream_id"])
    
    stream_state = StreamState(
        stream_id=state["stream_id"],
        trace_id=state["trace_id"],
        text=state["final_prompt"],
        user_id=state["user_id"],
        session_id=state.get("session_id"),
        chat_store=chat_store
    )
    
    # Create the generator
    generator = _assistant_stream(
        stream_state,
        cancel_event,
        manager,
        provider,
        personal_brain,
        audit_log
    )
    
    return {"response_generator": generator}


def build_agent_graph(
    memory_store: MemoryStore,
    chat_store: ChatStore,
    provider: ModelProvider,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
    stream_manager: StreamManager,
    voice_system_prompt: str | None = None,
) -> StateGraph:
    """Construct the LangGraph workflow."""

    async def _retrieve_memories_node(state: AgentState):
        return await retrieve_memories(state, memory_store)

    async def _retrieve_history_node(state: AgentState):
        return await retrieve_history(state, chat_store)

    async def _retrieve_agents_node(state: AgentState):
        return await retrieve_agents(state)

    async def _retrieve_guardrails_node(state: AgentState):
        return await retrieve_guardrails(state)

    def _bundle_node(state: AgentState):
        return bundle_context(state, voice_system_prompt=voice_system_prompt)

    def _generate_response_node(state: AgentState):
        return generate_response(
            state,
            stream_manager,
            provider,
            personal_brain,
            audit_log,
            chat_store
        )

    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve_memories", _retrieve_memories_node)
    workflow.add_node("retrieve_history", _retrieve_history_node)
    workflow.add_node("retrieve_agents", _retrieve_agents_node)
    workflow.add_node("retrieve_guardrails", _retrieve_guardrails_node)
    workflow.add_node("bundle", _bundle_node)
    workflow.add_node("generate", _generate_response_node)
    
    # Start -> Parallel Retrieval
    workflow.set_entry_point("retrieve_memories")
    
    # Sequential Chain (retrieval nodes -> bundle -> generate)
    workflow.add_edge("retrieve_memories", "retrieve_history")
    workflow.add_edge("retrieve_history", "retrieve_agents")
    workflow.add_edge("retrieve_agents", "retrieve_guardrails")
    workflow.add_edge("retrieve_guardrails", "bundle")
    workflow.add_edge("bundle", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
