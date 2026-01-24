"""Model provider interfaces and LLM streaming implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Protocol

import httpx


logger = logging.getLogger("arthur.ap.model_provider")


@dataclass
class ProviderHealth:
    """Health status of a model provider."""
    status: str  # "ok", "degraded", "down"
    reason: str | None = None
    latency_ms: float | None = None
    metrics: dict[str, Any] | None = None


class ModelProvider(Protocol):
    """Interface for LLM providers supporting streaming responses."""
    
    async def stream(
        self, stream_id: str, text: str, cancel_event: asyncio.Event
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens from the provider.
        
        Args:
            stream_id: Unique identifier for this stream request.
            text: Input text prompt.
            cancel_event: Event to signal cancellation.
            
        Yields:
            str: Text tokens as they are generated.
        """
        ...

    async def cancel(self, stream_id: str) -> None:  # pragma: no cover - interface hook
        """Cancel an active stream.
        
        Args:
            stream_id: The ID of the stream to cancel.
        """
        ...

    async def health_check(self) -> ProviderHealth:  # pragma: no cover - interface hook
        """Check provider connectivity and health.
        
        Returns:
            ProviderHealth: Current status.
        """
        ...


class OpenAIModelProvider:
    """Streams completions from Chosen LLM provider."""

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://api.x.ai/v1",
        model: str = "grok-4-1-fast-reasoning",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = client or httpx.AsyncClient()
        self._stream_events: dict[str, asyncio.Event] = {}

    async def stream(
        self, stream_id: str, text: str, cancel_event: asyncio.Event
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens from model provider."""
        if not self._api_key:
            raise RuntimeError("model provider unavailable: missing api key")

        self._stream_events[stream_id] = cancel_event
        start = time.perf_counter()
        is_xai = "x.ai" in self._base_url
        if is_xai:
            url = f"{self._base_url}/responses"
            payload = {
                "model": self._model,
                "stream": True,
                "input": text,  # xAI responses endpoint uses "input" not "messages"
                "tools": [{"type": "web_search"}],
            }
        else:
            url = f"{self._base_url}/chat/completions"
            payload = {
                "model": self._model,
                "stream": True,
                "messages": [{"role": "user", "content": text}],
            }
        
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with self._client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancel_event.is_set():
                        break
                    
                    if not line:
                        continue
                    
                    # Debug: log raw line from Grok
                    logger.info(
                        "provider_raw_line",
                        extra={"event": "provider_raw_line", "stream_id": stream_id, "line": line[:500]},
                    )
                        
                    # Handle concatenated SSE events
                    parts = line.split("data: ")
                    for part in parts:
                        if cancel_event.is_set():
                            break

                        part = part.strip()
                        if not part:
                            continue
                        
                        if part == "[DONE]":
                            break
                        
                        try:
                            parsed = json.loads(part)
                            # Debug: log parsed structure
                            logger.info(
                                "provider_parsed_chunk",
                                extra={"event": "provider_parsed", "stream_id": stream_id, "keys": list(parsed.keys())},
                            )
                            
                            # Handle xAI responses endpoint streaming format
                            if is_xai:
                                # xAI uses event-based streaming with "type" field
                                event_type = parsed.get("type", "")
                                if event_type == "response.output_text.delta":
                                    delta = parsed.get("delta", "")
                                    if delta:
                                        yield delta
                                elif event_type in ("response.completed", "response.done"):
                                    break
                                # Other event types (response.created, etc.) are ignored
                            else:
                                # OpenAI chat completions format
                                delta = parsed["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                        except json.JSONDecodeError:
                             logger.warning(
                                "provider_stream_parse_warning",
                                extra={"event": "provider_parse_warning", "provider": "openai", "stream_id": stream_id, "part": part[:200]},
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.error(
                                "provider_stream_error",
                                extra={"event": "provider_error", "provider": "openai", "stream_id": stream_id},
                                exc_info=exc,
                            )
                            break
        except httpx.HTTPStatusError as exc:
            # Try to read the response content for more details
            error_body = "unknown"
            try:
                error_body = await exc.response.aread()
                error_body = error_body.decode("utf-8")
            except Exception:
                pass
                
            logger.error(
                "provider_http_error",
                extra={
                    "event": "provider_error", 
                    "provider": "openai", 
                    "stream_id": stream_id,
                    "status_code": exc.response.status_code,
                    "error_body": error_body
                },
                exc_info=exc,
            )
            raise RuntimeError(f"Model provider error (HTTP {exc.response.status_code}): {error_body[:200]}")
        except httpx.HTTPError as exc:
            logger.error(
                "provider_http_error",
                extra={"event": "provider_error", "provider": "openai", "stream_id": stream_id},
                exc_info=exc,
            )
            raise RuntimeError(f"Model provider unavailable: {exc}")
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "provider_latency_ms",
                extra={
                    "event": "provider_latency",
                    "provider": "openai",
                    "stream_id": stream_id,
                    "latency_ms": round(latency_ms, 2),
                },
            )
            self._stream_events.pop(stream_id, None)

    async def cancel(self, stream_id: str) -> None:
        """Signal cancellation for the given stream ID."""
        event = self._stream_events.get(stream_id)
        if event:
            event.set()

    async def health_check(self) -> ProviderHealth:
        """Verify API key presence (connectivity check omitted for speed)."""
        if not self._api_key:
            return ProviderHealth(status="down", reason="missing_api_key")
        return ProviderHealth(status="ok")


__all__ = ["ModelProvider", "OpenAIModelProvider", "ProviderHealth"]
