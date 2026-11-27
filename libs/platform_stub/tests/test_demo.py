from pathlib import Path

import httpx
import pytest

from platform_stub.app import create_app


ROOT = Path(__file__).resolve().parents[3]
PYTHON_SERVICES = (
    "gateway",
    "profile",
    "orchestrator",
    "scouts",
    "tools",
    "kb",
    "analyst",
    "ideation",
    "validators",
    "scorer",
    "verdict",
    "critic",
    "agentops",
)


@pytest.mark.parametrize("name", PYTHON_SERVICES)
@pytest.mark.asyncio
async def test_every_service_has_health_and_ready(name):
    app = create_app(name)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/health")).json() == {"status": "ok", "service": name}
        assert (await client.get("/ready")).status_code == 200
        assert (await client.get("/metrics")).status_code == 200


@pytest.mark.parametrize("name", PYTHON_SERVICES)
def test_service_has_own_entry_point(name):
    entry = ROOT / "services" / name / "src" / "main.py"
    assert entry.is_file()
    assert (entry.parents[1] / "Dockerfile").is_file()


@pytest.mark.asyncio
async def test_demo_request_reaches_verdict_through_gateway_and_orchestrator(
    monkeypatch,
):
    calls = []
    verdict = create_app("verdict")
    orchestrator = create_app("orchestrator")
    gateway = create_app("gateway")

    async def route(request):
        calls.append(request.url.path)
        target = orchestrator if request.url.host == "orchestrator" else verdict
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target), base_url="http://test"
        ) as client:
            response = await client.request(
                request.method,
                request.url.path,
                content=request.content,
                headers={"content-type": "application/json"},
            )
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )

    monkeypatch.setattr(
        "platform_stub.app.downstream_transport", lambda: httpx.MockTransport(route)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gateway), base_url="http://test"
    ) as client:
        response = await client.post("/demo/validate", json={"idea": "A study planner"})
    assert response.status_code == 200
    assert calls == ["/demo/validate", "/demo/verdict"]
    assert response.json()["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert response.json()["demo"] is True


@pytest.mark.asyncio
async def test_empty_idea_is_rejected():
    app = create_app("gateway")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/demo/validate", json={"idea": "  "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_downstream_failure_is_not_a_verdict(monkeypatch):
    async def fail(request):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(
        "platform_stub.app.downstream_transport", lambda: httpx.MockTransport(fail)
    )
    app = create_app("gateway")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/demo/validate", json={"idea": "A study planner"})
    assert response.status_code == 503
    assert "verdict" not in response.json()


@pytest.mark.asyncio
async def test_scout_endpoint_explicitly_declines_collection_in_phase_2():
    app = create_app("scouts")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/scout",
            json={"source": "github", "query": "student tools", "run_id": "run-1"},
        )
    assert response.status_code == 501
    assert "Phase 2" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scout_endpoint_validates_request():
    app = create_app("scouts")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/scout", json={"source": "github", "query": ""})
    assert response.status_code == 422
