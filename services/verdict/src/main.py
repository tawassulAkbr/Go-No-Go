"""Verdict service: real M11 API plus the labelled Phase 2 demo route."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from platform_stub.app import DemoRequest, DemoResult
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import ValidationError
from tracing import trace_step

from contracts.verdict import Verdict, WhatIf

from services.verdict.src.engine import (
    EvaluationInput,
    VerdictConfig,
    decide,
    load_config,
    what_would_make_go,
)

app = FastAPI(title="M11 Verdict Engine")


def current_config() -> VerdictConfig:
    try:
        return load_config()
    except (OSError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=503, detail="Verdict configuration unavailable") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "verdict"}


@app.get("/ready")
def ready() -> dict[str, str]:
    current_config()
    return {"status": "ready", "service": "verdict"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/verdict", response_model=Verdict)
def verdict(request: EvaluationInput) -> Verdict:
    config = current_config()
    with trace_step(request.run_id, "verdict", "decide"):
        return decide(request, config)


@app.post("/whatif", response_model=WhatIf | None)
def whatif(request: EvaluationInput) -> WhatIf | None:
    config = current_config()
    with trace_step(request.run_id, "verdict", "whatif"):
        return what_would_make_go(request, config)


@app.post("/demo/verdict", response_model=DemoResult)
def demo_verdict(request: DemoRequest) -> DemoResult:
    with trace_step(request.run_id or "unknown", "verdict", "demo_verdict"):
        return DemoResult(
            demo=True,
            verdict="INSUFFICIENT_EVIDENCE",
            reason="Phase 2 demo only: no evidence has been collected or scored.",
            idea=request.idea,
            run_id=request.run_id or "unknown",
        )
