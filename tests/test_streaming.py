import asyncio
import json
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.models import ModelProvider, ProviderHealth
from ap.memory import MemoryStore
from ap.protocol.validator import validate_message


class FakeProvider(ModelProvider):
    def __init__(self, *, latency_ms: float | None = None) -> None:
        self.events: dict[str, asyncio.Event] = {}
        self.latency_ms = latency_ms
        self.last_text: str | None = None

    async def stream(self, stream_id: str, text: str, cancel_event: asyncio.Event):
        self.events[stream_id] = cancel_event
        self.last_text = text
        for token in text.split():
            if cancel_event.is_set():
                break
            yield token + " "
            await asyncio.sleep(0)

    async def cancel(self, stream_id: str) -> None:
        event = self.events.get(stream_id)
        if event:
            event.set()

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="ok", latency_ms=self.latency_ms, metrics={"latency_ms": self.latency_ms})


def _user_utterance_message(text: str):
    return {
        "id": "utterance-1",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "user_utterance",
            "args": {"text": text, "trace_id": "trace-123"},
        },
    }


@pytest.mark.asyncio
async def test_memory_context_injected_into_provider(tmp_path):
    provider = FakeProvider()
    memory = MemoryStore(tmp_path / "memory.db")
    memory.store_fact("remember this detail")
    app = create_app(model_provider=provider, memory_store=memory)
    message = _user_utterance_message("please recall detail")

    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/stream/v1/user-utterance", json=message) as response:
            assert response.status_code == 200
            await response.aread()

    assert provider.last_text is not None
    assert "Context" in provider.last_text
    assert "remember this detail" in provider.last_text


@pytest.mark.asyncio
async def test_streaming_emits_delta_and_final(tmp_path):
    memory = MemoryStore(tmp_path / "memory.db")
    app = create_app(model_provider=FakeProvider(), memory_store=memory)
    message = _user_utterance_message("hello world")

    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/stream/v1/user-utterance", json=message) as response:
            assert response.status_code == 200
            lines = [json.loads(line) for line in (await response.aread()).decode().splitlines() if line]

    assert len(lines) >= 2
    for payload in lines:
        validate_message(payload)

    delta_messages = [p for p in lines if p["payload"]["name"] == "assistant_delta"]
    final_messages = [p for p in lines if p["payload"]["name"] == "assistant_final"]

    assert len(delta_messages) >= 1
    assert len(final_messages) == 1
    assert final_messages[0].get("complete") is True
    for payload in delta_messages + final_messages:
        assert payload["payload"]["args"].get("trace_id") == "trace-123"
    final_args = final_messages[0]["payload"]["args"]
    assert "confidence" in final_args
    assert 0.0 <= final_args["confidence"]["score"] <= 1.0
    assert final_args["confidence"]["level"] in {"high", "medium", "low"}
    assert final_args["model_health"]["provider"] == "FakeProvider"
    assert final_args["model_health"]["status"] == "ok"


@pytest.mark.asyncio
async def test_streaming_rejects_overlong_utterance(tmp_path):
    memory = MemoryStore(tmp_path / "memory.db")
    app = create_app(model_provider=FakeProvider(), memory_store=memory)
    long_text = "x" * 3000
    message = _user_utterance_message(long_text)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/stream/v1/user-utterance", json=message)

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "utterance_too_long"


@pytest.mark.asyncio
async def test_confidence_score_clamped_with_latency(tmp_path):
    provider = FakeProvider(latency_ms=5000)
    memory = MemoryStore(tmp_path / "memory.db")
    app = create_app(model_provider=provider, memory_store=memory)
    message = _user_utterance_message("short")

    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/stream/v1/user-utterance", json=message) as response:
            lines = [json.loads(line) for line in (await response.aread()).decode().splitlines() if line]

    final_messages = [p for p in lines if p["payload"]["name"] == "assistant_final"]
    assert final_messages
    confidence = final_messages[0]["payload"]["args"]["confidence"]
    assert 0.0 <= confidence["score"] <= 1.0


@pytest.mark.asyncio
async def test_interrupt_stops_stream_and_logs(tmp_path, caplog):
    provider = FakeProvider()
    memory = MemoryStore(tmp_path / "memory.db")
    app = create_app(model_provider=provider, memory_store=memory)
    message = _user_utterance_message("one two three four")

    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/stream/v1/user-utterance", json=message) as response:
            iterator = response.aiter_lines()
            first_line = await iterator.__anext__()
            first_payload = json.loads(first_line)

            interrupt_message = {
                "id": "interrupt-1",
                "type": "tool",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"name": "interrupt", "args": {"stream_id": message["id"]}},
            }

            with caplog.at_level("INFO"):
                interrupt_response = await client.post(
                    "/stream/v1/interrupt", json=interrupt_message
                )

            remaining = [line async for line in iterator if line]

    assert interrupt_response.status_code == 200
    assert first_payload["payload"]["name"] == "assistant_delta"
    assert remaining == []
    assert any(getattr(record, "event", None) == "assistant_stream_interrupt" for record in caplog.records)


@pytest.mark.asyncio
async def test_interrupt_requires_stream_id(tmp_path):
    memory = MemoryStore(tmp_path / "memory.db")
    app = create_app(model_provider=FakeProvider(), memory_store=memory)
    interrupt_message = {
        "id": "interrupt-missing",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"name": "interrupt", "args": {}},
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/stream/v1/interrupt", json=interrupt_message)

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "missing_stream"
