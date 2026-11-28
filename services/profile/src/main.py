import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import psycopg
from redis import Redis, RedisError
from .routes.api import router
from .routes.cache import router as cache_router
from .repositories import store

app = FastAPI(title="Profile, sessions and cache")
app.include_router(router)
app.include_router(cache_router)


@app.exception_handler(psycopg.IntegrityError)
def conflict(request, exc):
    return JSONResponse(
        {"detail": "Record conflicts with stored data"}, status_code=409
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "profile"}


@app.get("/ready")
def ready():
    try:
        store.one("SELECT 1 FROM profiles LIMIT 1")
        Redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379"),
            socket_connect_timeout=2,
            socket_timeout=2,
        ).ping()
    except (psycopg.Error, RedisError, KeyError) as exc:
        raise HTTPException(503, "Profile storage unavailable") from exc
    return {"status": "ready", "service": "profile"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
