from fastapi import FastAPI, HTTPException
from foundation import connect
from psycopg import Error
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from scouts import collect

app = FastAPI(title="Scout agents")
app.post("/scout")(collect)


@app.get("/health")
def health():
    return {"status": "ok", "service": "scouts"}


@app.get("/ready")
def ready():
    try:
        with connect() as db:
            db.execute("SELECT 1 FROM raw_items LIMIT 1")
    except (Error, KeyError) as exc:
        raise HTTPException(503, "Scout storage unavailable") from exc
    return {"status": "ready", "service": "scouts"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
