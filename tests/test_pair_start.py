import sqlite3

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.config import Settings


def _settings_with_pins(db_path):
    return Settings(
        pairing_db_path=db_path,
        tls_spki_pin_primary="sha256/primarypin",
        tls_spki_pin_backup="sha256/secondarypin",
    )


@pytest.mark.asyncio
async def test_pair_start_returns_expected_payload(tmp_path):
    settings = _settings_with_pins(tmp_path / "pairing.db")
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/pair/v1/start", json={"device_id": "android-device"})

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in_sec"] == 300
    assert 6 <= len(body["pair_code"]) <= 10
    assert body["pinset_id"] == settings.tls_pinset_id
    assert body["spki_pins"] == [settings.tls_spki_pin_primary, settings.tls_spki_pin_backup]

    with sqlite3.connect(settings.pairing_db_path) as conn:
        row = conn.execute(
            "SELECT pair_request_id, pair_code, device_id FROM pending_pairs"
        ).fetchone()
    assert row[0] == body["pair_request_id"]
    assert row[1] == body["pair_code"]
    assert row[2] == "android-device"


@pytest.mark.asyncio
async def test_pair_start_rejects_invalid_body(tmp_path):
    settings = _settings_with_pins(tmp_path / "pairing-invalid.db")
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/pair/v1/start", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pair_start_response_structure(tmp_path):
    settings = _settings_with_pins(tmp_path / "pairing-structure.db")
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/pair/v1/start", json={"device_id": "android-device"})

    body = response.json()
    assert set(body.keys()) == {
        "pair_request_id",
        "pair_code",
        "expires_in_sec",
        "pinset_id",
        "spki_pins",
    }
    assert all(pin.startswith("sha256/") for pin in body["spki_pins"])
    assert len(body["spki_pins"]) == 2
