from fastapi.testclient import TestClient
from services.profile.src.main import app
from services.profile.src.repositories.store import user


def test_user_profile_versions_and_cache(migrated_db):
    c = TestClient(app)
    assert c.get("/ready").status_code == 200
    credentials = {"email": "student@example.org", "password": "a-long-password"}
    uid = c.post("/users", json=credentials).json()["id"]
    assert user(credentials["email"])["hash"].startswith("scrypt:")
    assert credentials["password"] not in user(credentials["email"])["hash"]
    assert c.post("/users/authenticate", json=credentials).json()["id"] == uid
    profile = dict(
        user_id=uid,
        skills=["python"],
        hours_per_week=8,
        weeks_available=6,
        team_size=2,
        compute="laptop",
        goal="portfolio",
        interests=[],
    )
    url = f"/users/{uid}/profile"
    assert c.put(url, json=profile).json()["version"] == 1
    assert c.put(url, json=profile).json()["version"] == 1
    key = dict(
        kind="verdict",
        user_id=uid,
        idea_hash=uid,
        profile_version=1,
        rubric_version="r1",
        engine_version="e1",
    )
    lookup = dict(run_id=uid, key=key)
    assert c.post("/cache/write", json={**lookup, "value": {"score": 65}}).is_success
    assert c.post("/cache/read", json=lookup).headers["X-Cache"] == "HIT"
    profile["hours_per_week"] = 9
    key["profile_version"] = c.put(url, json=profile).json()["version"]
    assert key["profile_version"] == 2
    assert c.post("/cache/read", json=lookup).headers["X-Cache"] == "MISS"
    idea = c.post(f"/users/{uid}/ideas", json={"title": "Example"}).json()["idea_id"]
    versions = f"/users/{uid}/ideas/{idea}/versions"
    assert c.post(versions, json={"title": "Updated"}).json()["version"] == 2
    assert [v["version"] for v in c.get(versions).json()] == [2, 1]
