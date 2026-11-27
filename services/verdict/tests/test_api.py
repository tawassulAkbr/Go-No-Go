import httpx
import pytest

from services.verdict.src.main import app
from services.verdict.tests.test_engine import case


@pytest.mark.asyncio
async def test_real_verdict_and_whatif_endpoints():
    payload = case().model_dump(mode="json")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as client:
        verdict = await client.post("/verdict", json=payload)
        whatif = await client.post("/whatif", json=payload)
    assert verdict.status_code == 200
    result = verdict.json()
    assert result["verdict"] == "GO"
    assert result["score"] == pytest.approx(70.5)
    assert result["versions"]["config"] == "w2"
    assert result["sensitivity"]["runs"] == 14
    assert whatif.status_code == 200
    assert whatif.json()["new_verdict"] == "GO"


@pytest.mark.asyncio
async def test_bad_score_record_is_rejected():
    payload = case().model_dump(mode="json")
    payload["scores"][0]["evidence_ids"] = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as client:
        response = await client.post("/verdict", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_config_is_not_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("VERDICT_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as client:
        ready = await client.get("/ready")
        verdict = await client.post("/verdict", json=case().model_dump(mode="json"))
    assert ready.status_code == 503
    assert verdict.status_code == 503
