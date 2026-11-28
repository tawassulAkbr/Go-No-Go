import httpx
from fastapi.testclient import TestClient
from foundation import connect
import scouts
from services.scouts.src.main import app


def test_on_demand_keeps_partial_result_and_budget_status(migrated_db, monkeypatch):
    calls = []

    def route(r):
        calls.append(r.url)
        if len(calls) > 1:
            return httpx.Response(402, json={"detail": "Run budget exceeded"})
        return httpx.Response(
            200,
            json=dict(
                items=[dict(name="tool", url="https://example.org/t")],
                fetched_at="2026-11-28",
                cursor=None,
            ),
        )

    client = httpx.Client(base_url="http://tools", transport=httpx.MockTransport(route))
    with TestClient(app) as api:
        monkeypatch.setattr(scouts.httpx, "Client", lambda **_: client)
        r = api.post("/scout", json=dict(source="hn", run_id="partial", limit=100))
    assert r.status_code == 402 and r.json()["detail"]["collected"] == 1
    assert all(r.host == "tools" and r.path == "/fetch" for r in calls)
    with connect() as db:
        assert db.execute("SELECT pending FROM raw_items").fetchone()["pending"]
        assert db.execute("SELECT error FROM ingestion_runs").fetchone()["error"]
