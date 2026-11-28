import hashlib
import json
from ..repositories.cache import client


def cache_key(key):
    parts = key.model_dump()
    kind = parts.pop("kind")
    return (
        kind
        + ":"
        + ":".join(hashlib.sha256(str(v).encode()).hexdigest() for v in parts.values())
    )


def write(key, value):
    client().setex(cache_key(key), 3600, json.dumps(value))


def read(key, run_id):
    raw = client().get(cache_key(key))
    hit = raw is not None
    print(
        json.dumps(
            {
                "run_id": run_id,
                "agent": "profile",
                "step": "cache_read",
                "cache_hit": hit,
            }
        )
    )
    return {"cache_hit": hit, "value": json.loads(raw) if hit else None}
