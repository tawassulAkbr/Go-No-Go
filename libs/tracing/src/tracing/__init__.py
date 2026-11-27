"""Minimal stdout tracing for Phase 2 service stubs."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterator


@contextmanager
def trace_step(run_id: str, agent: str, step: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "agent": agent,
                    "step": step,
                    "kind": "decision",
                    "latency_ms": round((perf_counter() - start) * 1000),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
