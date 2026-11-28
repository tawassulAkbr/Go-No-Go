from typing import Literal
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from ..services import cache

router = APIRouter()


class VerdictKey(BaseModel):
    kind: Literal["verdict"]
    user_id: str
    idea_hash: str
    profile_version: int = Field(gt=0)
    rubric_version: str
    engine_version: str


class RetrievalKey(BaseModel):
    kind: Literal["retrieve"]
    query_hash: str
    filters_hash: str
    kb_version: str


class Lookup(BaseModel):
    key: VerdictKey | RetrievalKey
    run_id: str


class Write(Lookup):
    value: dict


@router.post("/cache/write")
def write(body: Write):
    cache.write(body.key, body.value)
    return {"stored": True}


@router.post("/cache/read")
def read(body: Lookup, response: Response):
    result = cache.read(body.key, body.run_id)
    response.headers["X-Cache"] = "HIT" if result["cache_hit"] else "MISS"
    return result
