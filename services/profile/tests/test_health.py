from fastapi.testclient import TestClient
import psycopg
from services.profile.src import main


def test_liveness_and_unavailable_storage(monkeypatch):
    def unavailable(*args):
        raise psycopg.OperationalError()

    monkeypatch.setattr(main.store, "one", unavailable)
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "profile"}
        assert client.get("/ready").status_code == 503
