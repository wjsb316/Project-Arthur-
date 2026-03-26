"""Model provider interfaces and LLM streaming implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Protocol

import httpx

from ap.config import is_openai_com_base_url


logger = logging.getLogger("arthur.ap.model_provider")


def _format_provider_http_error(status: int, body: str) -> str:
    """Best-effort message from OpenAI/xAI JSON error body or raw text."""
    body = body.strip()
    if not body:
        return f"HTTP {status} (no response body; check API key and URL)"
    try:
        data = json.loads(body)
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(err, str):
            return err
    except json.JSONDecodeError:
        pass
    return body[:800]


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
        # model: str = "grok-4-1-fast-reasoning",
        model: str = "grok-4-1-fast-non-reasoning",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        # Use a long read timeout for streaming: x.ai can take >5s between chunks (default httpx timeout).
        _timeout = httpx.Timeout(30.0, read=120.0) if client is None else None
        self._client = client or httpx.AsyncClient(timeout=_timeout)
        self._stream_events: dict[str, asyncio.Event] = {}

    async def stream(
        self, stream_id: str, text: str, cancel_event: asyncio.Event
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens from model provider."""
        if not self._api_key:
            raise RuntimeError("model provider unavailable: missing api key")

        self._stream_events[stream_id] = cancel_event
        start = time.perf_counter()

        # Log entire prompt sent to LLM (same style as speech synthesizer input)
        logger.info(
            "LLM request prompt (stream_id=%s, model=%s, length=%d):\n%s",
            stream_id,
            self._model,
            len(text),
            text,
        )
        
        # xAI and OpenAI official API: Responses API + web_search (Chat Completions has no web search).
        use_responses_api = "x.ai" in self._base_url or is_openai_com_base_url(self._base_url)
        if use_responses_api:
            url = f"{self._base_url}/responses"
            payload = {
                "model": self._model,
                "stream": True,
                "input": text,  # Responses API uses string or structured "input"
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
                # For streaming requests, read error bodies here; exc.response.aread() after
                # raise_for_status() often yields nothing ("unknown").
                if response.status_code >= 400:
                    err_raw = await response.aread()
                    err_text = err_raw.decode("utf-8", errors="replace")
                    detail = _format_provider_http_error(response.status_code, err_text)
                    logger.error(
                        "provider_http_error",
                        extra={
                            "event": "provider_error",
                            "provider": "openai",
                            "stream_id": stream_id,
                            "status_code": response.status_code,
                            "error_body": err_text[:2000],
                        },
                    )
                    raise RuntimeError(
                        f"Model provider error (HTTP {response.status_code}): {detail}"
                    )
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
                            
                            # Responses API (xAI or OpenAI): event-based streaming with "type" field
                            if use_responses_api:
                                event_type = parsed.get("type", "")
                                if event_type == "response.output_text.delta":
                                    delta = parsed.get("delta", "")
                                    if delta:
                                        yield delta
                                elif event_type in ("response.completed", "response.done"):
                                    break
                                # Other event types (response.created, web_search_call, etc.) are ignored
                            else:
                                # OpenAI chat completions format (and compatible proxies)
                                if parsed.get("error"):
                                    err = parsed["error"]
                                    msg = (
                                        err.get("message", str(err))
                                        if isinstance(err, dict)
                                        else str(err)
                                    )
                                    logger.error(
                                        "provider_stream_api_error",
                                        extra={
                                            "event": "provider_api_error",
                                            "stream_id": stream_id,
                                            "message": msg[:500],
                                        },
                                    )
                                    raise RuntimeError(f"Model provider API error: {msg}")
                                choices = parsed.get("choices") or []
                                if not choices:
                                    continue
                                delta_obj = choices[0].get("delta") or {}
                                if not isinstance(delta_obj, dict):
                                    continue
                                piece = delta_obj.get("content") or ""
                                if piece:
                                    yield piece
                        except json.JSONDecodeError:
                             logger.warning(
                                "provider_stream_parse_warning",
                                extra={"event": "provider_parse_warning", "provider": "openai", "stream_id": stream_id, "part": part[:200]},  # noqa: E501
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.error(
                                "provider_stream_error",
                                extra={"event": "provider_error", "provider": "openai", "stream_id": stream_id},
                                exc_info=exc,
                            )
                            break
        except httpx.HTTPStatusError as exc:
            error_body = ""
            try:
                error_body = (await exc.response.aread()).decode("utf-8", errors="replace")
            except Exception:
                pass
            detail = _format_provider_http_error(exc.response.status_code, error_body)
            logger.error(
                "provider_http_error",
                extra={
                    "event": "provider_error",
                    "provider": "openai",
                    "stream_id": stream_id,
                    "status_code": exc.response.status_code,
                    "error_body": error_body[:2000] or "(unreadable)",
                },
                exc_info=exc,
            )
            raise RuntimeError(
                f"Model provider error (HTTP {exc.response.status_code}): {detail}"
            ) from exc
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
