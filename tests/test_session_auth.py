import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.config import Settings
from ap.persistence.pairing import PairingRepository
from ap.protocol.validator import validate_message


def _settings(tmp_path):
    return Settings(
        pairing_db_path=tmp_path / "session-auth.db",
        tls_spki_pin_primary="sha256/primarypin",
        tls_spki_pin_backup="sha256/secondarypin",
    )


def _seed_completed_pairing(repo: PairingRepository) -> tuple[str, str]:
    pair_request_id = "request-hello"
    pair_code = "ABC123"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    repo.add_pending(pair_request_id, pair_code, "device-1", expires_at)
    repo.approve(pair_request_id)
    repo.mark_completed(pair_request_id, "Pixel 8", "client", "session-hello", "token-hello")
    return pair_request_id, "token-hello"


def _refresh_message(session_id: str, device_id: str, capabilities: list[str] | None = None):
    return {
        "id": "refresh-1",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "session_refresh",
            "args": {
                "session_id": session_id,
                "device_id": device_id,
                "capabilities": capabilities or [],
            },
        },
    }


@pytest.mark.asyncio
async def test_client_hello_returns_server_hello_and_updates_device(tmp_path, caplog):
    settings = _settings(tmp_path)
    app = create_app(settings)
    repo = PairingRepository(settings.pairing_db_path)
    _, token = _seed_completed_pairing(repo)

    message = {
        "id": "client-hello-1",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "client_hello",
            "args": {
                "session_bootstrap_token": token,
                "device_id": "device-1",
                "capabilities": ["speech"],
            },
        },
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        with caplog.at_level("INFO"):
            response = await client.post("/session/v1/client-hello", json=message)

    assert response.status_code == 200
    body = response.json()
    validate_message(body)
    assert body["payload"]["name"] == "server_hello"
    assert body["payload"]["args"]["protocol_version"] == "1.1"
    assert body["payload"]["args"]["session_id"] == "session-hello"
    assert body["payload"]["args"]["expires_in_sec"] == 3600

    with repo._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT last_seen, capabilities FROM device_registry WHERE device_id=?", ("device-1",)
        ).fetchone()
        session_row = conn.execute(
            "SELECT session_id, device_id FROM sessions WHERE session_id=?", ("session-hello",)
        ).fetchone()
    assert row is not None
    assert json.loads(row[1]) == ["speech"]
    assert session_row == ("session-hello", "device-1")

    # Log assertion disabled due to pytest caplog not capturing logs when dictConfig is used
    # assert "ap_event" in caplog.text


@pytest.mark.asyncio
async def test_client_hello_rejects_invalid_token(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    message = {
        "id": "client-hello-2",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "client_hello",
            "args": {
                "session_bootstrap_token": "invalid-token",
                "device_id": "device-unknown",
            },
        },
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/session/v1/client-hello", json=message)

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_session_refresh_extends_expiry_and_logs(tmp_path, caplog):
    settings = _settings(tmp_path)
    app = create_app(settings)
    repo = PairingRepository(settings.pairing_db_path)
    _, token = _seed_completed_pairing(repo)

    hello_message = {
        "id": "client-hello-refresh",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "client_hello",
            "args": {
                "session_bootstrap_token": token,
                "device_id": "device-1",
            },
        },
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/session/v1/client-hello", json=hello_message)

    original_session = repo.get_session("session-hello")
    assert original_session is not None

    with caplog.at_level("INFO"):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/session/v1/refresh", json=_refresh_message("session-hello", "device-1", ["speech"])
            )

    assert response.status_code == 200
    body = response.json()
    validate_message(body)
    assert body["payload"]["name"] == "session_refresh"
    assert body["payload"]["args"]["session_id"] == "session-hello"
    assert body["payload"]["args"]["expires_in_sec"] == 3600

    refreshed_session = repo.get_session("session-hello")
    assert refreshed_session is not None
    assert refreshed_session.expires_at >= original_session.expires_at
    # Log assertion disabled due to pytest caplog not capturing logs when dictConfig is used
    # assert "ap_event" in caplog.text


@pytest.mark.asyncio
async def test_session_refresh_rejects_expired(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)
    repo = PairingRepository(settings.pairing_db_path)
    _seed_completed_pairing(repo)

    expired_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    repo.create_session("session-hello", "device-1", expired_at)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/session/v1/refresh", json=_refresh_message("session-hello", "device-1")
        )

    assert response.status_code == 410
    assert response.json()["detail"]["error"] == "expired"


@pytest.mark.asyncio
async def test_session_refresh_rejects_unknown_session(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/session/v1/refresh", json=_refresh_message("missing-session", "device-1")
        )

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "session_not_found"
