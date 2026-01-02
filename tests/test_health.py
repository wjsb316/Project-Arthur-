import pytest
from httpx import AsyncClient

from ap import create_app


@pytest.mark.asyncio
async def test_health_returns_ok():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_rejects_unsupported_method():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/health")
    assert response.status_code == 405
