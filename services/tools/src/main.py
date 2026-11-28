import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from fastapi import HTTPException, Response
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from redis.exceptions import RedisError
from prometheus_client import Counter
from pydantic import BaseModel, Field, model_validator
from redis import Redis

from .connectors import CONNECTORS, Params, Request, bearer
from .sanitize import clean, wrapped

app = FastAPI(title="Tool layer")
config = Path(os.getenv("CONFIG_DIR", "config"))
limits = json.loads((config / "budgets.yaml").read_text())
domains = set(json.loads((config / "tool_domains.json").read_text()))
UA = "GoNoGoResearch/1.0 (+https://github.com/tawassulAkbr/Go-No-Go)"
blocked = Counter("blocked_injections", "Fetched fields with instruction-like content")
tokens = Counter("hosted_llm_tokens", "Hosted model token usage", ["kind"])
cost = Counter("hosted_llm_cost_usd", "Estimated hosted model cost in USD")
storage = Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379"),
    decode_responses=True,
    socket_timeout=3,
)
client = httpx.Client(timeout=15, headers={"User-Agent": UA}, follow_redirects=False)
BUCKET = """
local t=redis.call('TIME')
local now=tonumber(t[1])+tonumber(t[2])/1000000
local prev=redis.call('HMGET',KEYS[1],'balance','last')
local balance=math.min(ARGV[1],tonumber(prev[1] or ARGV[1])+(now-tonumber(prev[2] or now))*ARGV[2])
if balance<1 then return 0 end
redis.call('HSET',KEYS[1],'balance',balance-1,'last',now)
redis.call('EXPIRE',KEYS[1],60)
return 1
"""
RESERVE = """
local used=tonumber(redis.call('GET',KEYS[1]) or '0')
if used+tonumber(ARGV[1])>tonumber(ARGV[2]) then return 0 end
redis.call('INCRBY',KEYS[1],ARGV[1])
redis.call('EXPIRE',KEYS[1],86400)
return 1
"""


def reserve(key, amount, limit):
    if not storage.eval(RESERVE, 1, key, amount, limit):
        raise HTTPException(402, "Run budget exceeded")


def domain(url):
    try:
        u = urlsplit(url)
        if (
            u.scheme == "https"
            and u.hostname in domains
            and u.port in (None, 443)
            and not u.username
            and not u.password
        ):
            return u.hostname
    except ValueError:
        pass
    raise HTTPException(403, "Domain unavailable")


def rate(host):
    if not storage.eval(
        BUCKET, 1, "rate:" + host, limits["burst"], limits["requests_per_second"]
    ):
        raise HTTPException(429, "Domain rate limit", headers={"Retry-After": "1"})


def read_remote(req, cap):
    try:
        with client.stream(
            "POST" if req.body is not None else "GET",
            req.url,
            headers=req.headers,
            json=req.body,
        ) as r:
            buf = bytearray()
            for chunk in r.iter_bytes(chunk_size=16384):
                remaining = cap - len(buf)
                buf.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    return r.status_code, bytes(buf), True, r.headers
            return r.status_code, bytes(buf), False, r.headers
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Source connection failed") from exc


def robots(url, host):
    key = "robots:" + host
    rules = storage.get(key)
    if rules is None:
        rate(host)
        status, body, cut, _ = read_remote(
            Request(f"https://{host}/robots.txt"), 512000
        )
        if status in (404, 410):
            rules = ""
        elif status == 200 and not cut:
            rules = body.decode(errors="replace")
        elif status in (401, 403):
            rules = "User-agent: *\nDisallow: /"
        else:
            raise HTTPException(503, "Robots policy unavailable")
        storage.setex(key, 3600, rules)
    parser = RobotFileParser()
    parser.parse(rules.splitlines())
    if not parser.can_fetch(UA, url):
        raise HTTPException(403, "Robots policy disallows resource")


class Fetch(BaseModel):
    url: str | None = None
    connector: (
        Literal[
            "hn", "hackernews", "github", "producthunt", "reddit", "crates", "rubygems"
        ]
        | None
    ) = None
    params: Params = Field(default_factory=Params)
    run_id: str = Field(min_length=1, max_length=128)
    purpose: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def selection(self):
        if bool(self.url) == bool(self.connector):
            raise ValueError("Supply one URL or connector")
        return self


def source_response(req, run_id, host):
    for attempt in range(3):
        if attempt:
            rate(host)
        reserve("pages:" + run_id, 1, limits["pages_per_run"])
        status, body, cut, headers = read_remote(req, limits["max_bytes"])
        if status == 200:
            return body, cut
        if status != 429 and status < 500:
            break
        if attempt < 2:
            delay = headers.get("Retry-After", "")
            if delay and (not delay.isdigit() or int(delay) > 8):
                break
            time.sleep(max(2**attempt, int(delay or 0)))
    raise HTTPException(429 if status == 429 else 502, "Upstream resource unavailable")


@app.post("/fetch")
def fetch(body: Fetch, response: Response):
    source = "hn" if body.connector == "hackernews" else body.connector
    connector = CONNECTORS.get(source)
    search = body.params.operation == "search"
    req = (
        (connector.search(body.params) if search else connector.get(body.params))
        if connector
        else Request(body.url)
    )
    host = domain(req.url)
    robots(req.url, host)
    rate(host)
    key = (
        "fetch:"
        + hashlib.sha256(
            json.dumps(
                [source, body.params.operation, req.url, req.body], sort_keys=True
            ).encode()
        ).hexdigest()
    )
    if cached := storage.get(key):
        response.headers["X-Cache"] = "HIT"
        return json.loads(cached)
    raw, cut = source_response(req, body.run_id, host)
    label = source or host
    result = {
        "source": label,
        "url": req.url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    suspected = False
    if connector and search:
        try:
            rows, cursor = connector.results(json.loads(raw))
        except (KeyError, ValueError, TypeError) as exc:
            raise HTTPException(502, "Incomplete connector response") from exc
        items = []
        for row in rows:
            url = row.get("url") or ""
            if not url.startswith(("https://", "http://")):
                continue
            for field in ("name", "summary"):
                row[field], flag = clean(row[field] or "")
                suspected |= flag
            tags = [clean(tag) for tag in row["niche_tags"]]
            row["niche_tags"] = [tag for tag, flag in tags if not flag and tag]
            suspected |= any(flag for _, flag in tags)
            items.append(row)
        result.update(
            items=items,
            cursor=cursor,
            content=wrapped(json.dumps(items, ensure_ascii=False), label),
        )
    else:
        text, suspected = clean(raw.decode(errors="replace"))
        result["content"] = wrapped(text, label)
    if suspected:
        blocked.inc()
    result["flags"] = {"injection_suspected": suspected, "truncated": cut}
    storage.setex(key, 900, json.dumps(result))
    response.headers["X-Cache"] = "MISS"
    return result


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=16000)


class LLM(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    messages: list[Message] = Field(min_length=1, max_length=20)
    output_schema: dict | None = None
    max_tokens: int = Field(default=256, ge=1, le=2048)


@app.post("/llm")
def llm(body: LLM):
    headers = bearer("LLM_API_KEY")
    url = "https://api.openai.com/v1/chat/completions"
    host = domain(url)
    rate(host)
    if not all(
        os.getenv(k)
        for k in ("LLM_INPUT_USD_PER_MILLION", "LLM_OUTPUT_USD_PER_MILLION")
    ):
        raise HTTPException(503, "Model pricing unavailable")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in body.messages],
        "max_tokens": body.max_tokens,
    }
    if body.output_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "result", "schema": body.output_schema},
        }
    upper = len(json.dumps(payload).encode()) + body.max_tokens + 128
    key = "llm-budget:" + body.run_id
    reserve(key, upper, limits["llm_tokens_per_run"])
    status, raw, cut, _ = read_remote(
        Request(url, headers, payload), limits["max_bytes"]
    )
    if status != 200 or cut:
        raise HTTPException(502, "Hosted model unavailable")
    result = json.loads(raw)
    usage = result["usage"]
    actual = usage["total_tokens"]
    storage.incrby(key, actual - upper)
    for kind in ("prompt_tokens", "completion_tokens"):
        tokens.labels(kind).inc(usage[kind])
    estimate = (
        usage["prompt_tokens"] * float(os.environ["LLM_INPUT_USD_PER_MILLION"])
        + usage["completion_tokens"] * float(os.environ["LLM_OUTPUT_USD_PER_MILLION"])
    ) / 1e6
    cost.inc(estimate)
    return {
        "content": result["choices"][0]["message"]["content"],
        "model": result["model"],
        "usage": usage,
        "estimated_cost_usd": estimate,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "tools"}


@app.get("/ready")
def ready():
    try:
        storage.ping()
    except RedisError as exc:
        raise HTTPException(503, "Tool cache unavailable") from exc
    return {"status": "ready", "service": "tools"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
