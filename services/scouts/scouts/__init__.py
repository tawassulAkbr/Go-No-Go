import json
import os
import time
from typing import Literal

import httpx
from fastapi import HTTPException
from foundation import connect
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field
from tracing import trace_step


class Plan(BaseModel):
    source: Literal[
        "hn", "hackernews", "github", "producthunt", "reddit", "crates", "rubygems"
    ]
    query: str = Field(default="", max_length=256)
    run_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=100, ge=1, le=1500)


def collect(plan: Plan):
    source = "hn" if plan.source == "hackernews" else plan.source
    start = time.monotonic()
    count = 0
    cursor = None
    error = None
    status = 502
    size = min(
        plan.limit,
        20 if source == "producthunt" else 30 if source == "rubygems" else 50,
    )
    with trace_step(plan.run_id, "scouts", "collect"):
        try:
            with httpx.Client(
                base_url=os.getenv("TOOLS_URL", "http://tools:8000"), timeout=60
            ) as client:
                for page in range((plan.limit + size - 1) // size):
                    params = {
                        "query": plan.query,
                        "page": page,
                        "size": size,
                        "cursor": cursor,
                    }
                    for attempt in range(3):
                        r = client.post(
                            "/fetch",
                            json={
                                "connector": source,
                                "params": params,
                                "purpose": "scout",
                                "run_id": plan.run_id,
                            },
                        )
                        if r.status_code not in (429, 502, 503) or attempt == 2:
                            break
                        time.sleep(2**attempt)
                    r.raise_for_status()
                    result = r.json()
                    rows = result["items"][: plan.limit - count]
                    with connect() as db:
                        for item in rows:
                            item.update(source=source, fetched_at=result["fetched_at"])
                            db.execute(
                                """INSERT INTO raw_items(source,url,item) VALUES(%s,%s,%s)
                                ON CONFLICT(source,url) DO UPDATE SET item=excluded.item,pending=true
                                WHERE (raw_items.item-'fetched_at')<>(excluded.item-'fetched_at')""",
                                (source, item["url"], Jsonb(item)),
                            )
                    count += len(rows)
                    cursor = result["cursor"]
                    if not rows or (source in ("reddit", "producthunt") and not cursor):
                        break
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
            error = str(exc)
        with connect() as db:
            db.execute(
                """INSERT INTO ingestion_runs(run_id,source,added,dropped,counts,duration_s,error)
                VALUES(%s,%s,0,0,%s,%s,%s)""",
                (
                    plan.run_id,
                    source,
                    Jsonb({"collected": count}),
                    time.monotonic() - start,
                    error,
                ),
            )
        if error:
            print(
                json.dumps(
                    {
                        "run_id": plan.run_id,
                        "source": source,
                        "error": error,
                        "collected": count,
                    }
                )
            )
            raise HTTPException(status, {"collected": count, "error": error})
    return {"run_id": plan.run_id, "source": source, "collected": count}
