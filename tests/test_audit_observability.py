import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.config import Settings
from ap.models import ModelProvider, ProviderHealth
from ap.persistence.audit import AuditLog
from ap.memory import MemoryStore


class DownProvider(ModelProvider):
    async def stream(self, stream_id: str, text: str, cancel_event: asyncio.Event):  # pragma: no cover - not used
        yield ""

    async def cancel(self, stream_id: str) -> None:  # pragma: no cover - not used
        return None

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="down", reason="missing_api_key", latency_ms=0.0)


class OKProvider(ModelProvider):
    async def stream(self, stream_id: str, text: str, cancel_event: asyncio.Event):
        yield "hi "

    async def cancel(self, stream_id: str) -> None:  # pragma: no cover - not used
        return None

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="ok", latency_ms=5.0)


def _settings(tmp_path):
    return Settings(
        audit_db_path=tmp_path / "audit.db",
        ops_db_path=tmp_path / "ops.db",
        pairing_db_path=tmp_path / "pairing.db",
        memory_db_path=tmp_path / "memory.db",
        tls_spki_pin_primary="sha256/primarypin",
        tls_spki_pin_backup="sha256/secondarypin",
    )


def _user_utterance(trace_id: str = "trace-audit"):
    return {
        "id": "utterance-audit",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"name": "user_utterance", "args": {"text": "hello", "trace_id": trace_id}},
    }


@pytest.mark.asyncio
async def test_audit_export_returns_entries(tmp_path):
    audit_log = AuditLog(tmp_path / "audit.db")
    audit_log.append("manual_entry", severity="info", trace_id="trace-export")
    settings = _settings(tmp_path)
    app = create_app(settings, audit_log=audit_log, memory_store=MemoryStore(settings.memory_db_path))

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/audit/v1/export")

    assert response.status_code == 200
    body = response.json()
    assert any(entry["event"] == "manual_entry" for entry in body["entries"])


@pytest.mark.asyncio
async def test_model_down_emits_ap_offline_event(tmp_path):
    audit_log = AuditLog(tmp_path / "audit.db")
    settings = _settings(tmp_path)
    app = create_app(
        settings,
        model_provider=DownProvider(),
        memory_store=MemoryStore(settings.memory_db_path),
        audit_log=audit_log,
    )

    message = _user_utterance()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/stream/v1/user-utterance", json=message)

    assert response.status_code == 503
    entries = list(audit_log.list_entries())
    assert any(entry.event == "ap_offline" for entry in entries)


@pytest.mark.asyncio
async def test_streaming_creates_audit_entry(tmp_path):
    audit_log = AuditLog(tmp_path / "audit.db")
    settings = _settings(tmp_path)
    app = create_app(
        settings,
        model_provider=OKProvider(),
        memory_store=MemoryStore(settings.memory_db_path),
        audit_log=audit_log,
    )

    message = _user_utterance("trace-audit-stream")
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/stream/v1/user-utterance", json=message) as response:
            await response.aread()

    entries = list(audit_log.list_entries())
    assert any(entry.event == "assistant_stream_start" for entry in entries)

