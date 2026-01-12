from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.config import Settings
from ap.persistence.permissions import PermissionRepository
from ap.protocol.validator import validate_message


def _settings(tmp_path):
    return Settings(
        ops_db_path=tmp_path / "ops.db",
        memory_db_path=tmp_path / "memory.db",
        tls_spki_pin_primary="sha256/primarypin",
        tls_spki_pin_backup="sha256/secondarypin",
    )


def _send_note_message(note: str, client_label: str, timeout_sec: int = 15):
    return {
        "id": "request-1",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "send_note",
            "args": {"note": note, "client_label": client_label, "timeout_sec": timeout_sec},
        },
    }


def _permission_response(request_id: str, decision: str):
    return {
        "id": "response-1",
        "type": "tool",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "name": "permission_response",
            "args": {"request_id": request_id, "decision": decision},
        },
    }


@pytest.mark.asyncio
async def test_permission_request_emitted_for_side_effect(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    message = _send_note_message("hello", "device-a")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/ops/v1/side-effect", json=message)

    assert response.status_code == 200
    body = response.json()
    validate_message(body)
    assert body["payload"]["name"] == "permission_request"
    assert body["payload"]["args"]["risk_tier"] == "high"


@pytest.mark.asyncio
async def test_permission_timeout_denies(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    message = _send_note_message("hello", "device-a", timeout_sec=0)
    async with AsyncClient(app=app, base_url="http://test") as client:
        start_response = await client.post("/ops/v1/side-effect", json=message)
        request_id = start_response.json()["payload"]["args"]["request_id"]
        response = await client.post(
            "/ops/v1/permission-response", json=_permission_response(request_id, "yes")
        )

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "permission_expired"


@pytest.mark.asyncio
async def test_permission_yes_delivers_note(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)
    repo = PermissionRepository(settings.ops_db_path)

    message = _send_note_message("hello", "device-a")
    async with AsyncClient(app=app, base_url="http://test") as client:
        start_response = await client.post("/ops/v1/side-effect", json=message)
        request_id = start_response.json()["payload"]["args"]["request_id"]
        response = await client.post(
            "/ops/v1/permission-response", json=_permission_response(request_id, "yes")
        )

    assert response.status_code == 200
    assert repo.was_delivered(request_id) is True


@pytest.mark.asyncio
async def test_permission_response_unknown_request(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/ops/v1/permission-response", json=_permission_response("missing", "yes")
        )

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "unknown_request"
