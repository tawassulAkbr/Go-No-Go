import httpx
import pytest

from services.analyst.src.main import app


@pytest.mark.asyncio
async def test_entrypoint_health_and_readiness():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        health = await client.get("/health")
        ready = await client.get("/ready")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "analyst"}
    assert ready.status_code == 200
