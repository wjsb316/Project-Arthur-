from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from ap import create_app
from ap.config import Settings
from ap.persistence.pairing import PairingRepository


def _settings(tmp_path):
    return Settings(
        pairing_db_path=tmp_path / "pairing-complete.db",
        tls_spki_pin_primary="sha256/primarypin",
        tls_spki_pin_backup="sha256/secondarypin",
    )


@pytest.mark.asyncio
async def test_pair_complete_requires_approval(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        start_resp = await client.post("/pair/v1/start", json={"device_id": "android-device"})
    start_body = start_resp.json()

    repository = PairingRepository(settings.pairing_db_path)
    repository.approve(start_body["pair_request_id"])

    async with AsyncClient(app=app, base_url="http://test") as client:
        complete_resp = await client.post(
            "/pair/v1/complete",
            json={
                "pair_request_id": start_body["pair_request_id"],
                "pair_code": start_body["pair_code"],
                "client_label": "Pixel 8",
                "role": "client",
            },
        )

    assert complete_resp.status_code == 200
    body = complete_resp.json()
    assert body["device_record"]["device_id"] == "android-device"
    assert body["device_record"]["client_label"] == "Pixel 8"
    assert body["device_record"]["role"] == "client"
    assert body["session_bootstrap_token"]
    assert body["session_id"]

    with repository._connect() as conn:  # noqa: SLF001 - test-level verification
        row = conn.execute(
            "SELECT client_label, role, session_id FROM device_registry WHERE device_id=?",
            ("android-device",),
        ).fetchone()
    assert row == ("Pixel 8", "client", body["session_id"])


@pytest.mark.asyncio
async def test_pair_complete_rejects_expired(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        start_resp = await client.post("/pair/v1/start", json={"device_id": "android-device"})
    start_body = start_resp.json()

    repository = PairingRepository(settings.pairing_db_path)
    repository.approve(start_body["pair_request_id"])

    expired_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    with repository._connect() as conn:  # noqa: SLF001 - test-level adjustment
        conn.execute(
            "UPDATE pending_pairs SET expires_at=? WHERE pair_request_id=?",
            (int(expired_at.timestamp()), start_body["pair_request_id"]),
        )
        conn.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        complete_resp = await client.post(
            "/pair/v1/complete",
            json={
                "pair_request_id": start_body["pair_request_id"],
                "pair_code": start_body["pair_code"],
                "client_label": "Pixel 8",
                "role": "client",
            },
        )

    assert complete_resp.status_code == 410
    assert complete_resp.json()["detail"]["error"] == "expired"


@pytest.mark.asyncio
async def test_pair_complete_rejects_unapproved(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)

    async with AsyncClient(app=app, base_url="http://test") as client:
        start_resp = await client.post("/pair/v1/start", json={"device_id": "android-device"})
        complete_resp = await client.post(
            "/pair/v1/complete",
            json={
                "pair_request_id": start_resp.json()["pair_request_id"],
                "pair_code": start_resp.json()["pair_code"],
                "client_label": "Pixel 8",
                "role": "client",
            },
        )

    assert complete_resp.status_code == 403
    assert complete_resp.json()["detail"]["error"] == "not_approved"

