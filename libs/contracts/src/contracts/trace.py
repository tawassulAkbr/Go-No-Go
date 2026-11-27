from datetime import datetime
from typing import Literal

from pydantic import JsonValue, NonNegativeFloat, NonNegativeInt

from .common import Record, Text


class Trace(Record):
    run_id: Text
    step_id: NonNegativeInt
    parent_step: NonNegativeInt | None
    agent: Text
    kind: Literal["tool_call", "llm_call", "decision"]
    tool: Text | None
    input: JsonValue
    output: JsonValue
    tokens_in: NonNegativeInt
    tokens_out: NonNegativeInt
    cost_usd: NonNegativeFloat
    latency_ms: NonNegativeInt
    retries: NonNegativeInt
    model: Text | None
    cache_hit: bool
    error: str | None
    ts: datetime
