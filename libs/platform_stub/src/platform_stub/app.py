"""Phase 2 service stubs. Demo verdicts are deliberately non-production data."""

import os
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field, field_validator
from tracing import trace_step


class DemoRequest(BaseModel):
    idea: str = Field(min_length=1, max_length=500)
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("idea")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("idea cannot be blank")
        return value


class DemoResult(BaseModel):
    demo: Literal[True]
    verdict: Literal["INSUFFICIENT_EVIDENCE"]
    reason: str
    idea: str
    run_id: str


class ScoutRequest(BaseModel):
    source: Literal["hackernews", "github", "producthunt"]
    query: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be blank")
        return value


def downstream_transport() -> httpx.AsyncBaseTransport | None:
    """Tests replace this to route requests into other ASGI apps."""
    return None


async def forward(url: str, request: DemoRequest) -> DemoResult:
    try:
        async with httpx.AsyncClient(
            transport=downstream_transport(), timeout=5.0
        ) as client:
            response = await client.post(url, json=request.model_dump())
            response.raise_for_status()
        return DemoResult.model_validate(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Demo service unavailable") from exc


def create_app(service: str) -> FastAPI:
    app = FastAPI(title=f"{service} Phase 2 stub")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": service}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        return {"status": "ready", "service": service}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    if service == "gateway":

        @app.post("/demo/validate", response_model=DemoResult)
        async def gateway_demo(request: DemoRequest) -> DemoResult:
            request.run_id = request.run_id or str(uuid4())
            base = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000").rstrip("/")
            with trace_step(request.run_id, service, "demo_forward"):
                return await forward(f"{base}/demo/validate", request)

    elif service == "orchestrator":

        @app.post("/demo/validate", response_model=DemoResult)
        async def orchestrator_demo(request: DemoRequest) -> DemoResult:
            base = os.getenv("VERDICT_URL", "http://verdict:8000").rstrip("/")
            with trace_step(request.run_id or "unknown", service, "demo_forward"):
                return await forward(f"{base}/demo/verdict", request)

    elif service == "scouts":

        @app.post("/scout")
        def scout_stub(request: ScoutRequest) -> None:
            with trace_step(request.run_id, service, "scout_not_implemented"):
                raise HTTPException(
                    status_code=501,
                    detail="Phase 2 scout stub: collection is implemented in P4.",
                )

    elif service == "verdict":

        @app.post("/demo/verdict", response_model=DemoResult)
        def verdict_demo(request: DemoRequest) -> DemoResult:
            with trace_step(request.run_id or "unknown", service, "demo_verdict"):
                return DemoResult(
                    demo=True,
                    verdict="INSUFFICIENT_EVIDENCE",
                    reason="Phase 2 demo only: no evidence has been collected or scored.",
                    idea=request.idea,
                    run_id=request.run_id or "unknown",
                )

    return app
