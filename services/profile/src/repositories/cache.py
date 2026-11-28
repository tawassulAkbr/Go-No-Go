import os
from functools import lru_cache
from redis import Redis


@lru_cache(maxsize=1)
def client():
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379"), socket_timeout=3
    )
