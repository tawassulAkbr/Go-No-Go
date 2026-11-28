"""Canonical idea cards and deterministic, offline feature-hashing embeddings."""

import html
import hashlib
import math
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

import httpx
from contracts import Card

DIMENSIONS = 512


def canonical(url):
    u = urlsplit(url.strip())
    if (
        u.scheme.lower() not in ("http", "https")
        or not u.hostname
        or u.username
        or u.password
    ):
        raise ValueError("Invalid public card URL")
    host = u.hostname.lower().removeprefix("www.")
    if ":" in host:
        host = f"[{host}]"
    if u.port and (u.scheme, u.port) not in (("https", 443), ("http", 80)):
        host += f":{u.port}"
    params = sorted(
        (k, v)
        for k, v in parse_qsl(u.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
    )
    return urlunsplit(
        (u.scheme.lower(), host, u.path.rstrip("/"), urlencode(params), "")
    )


def card_id(url):
    return "card_" + hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()[:8]


def name_key(name):
    return " ".join(re.findall(r"\w+", name.casefold())) or name.casefold()


def extract(item, run_id):
    url = canonical(item["url"])
    name = (
        re.sub(r"^(?:Show|Ask) HN:\s*", "", item["name"], flags=re.I).strip()
        or item["name"]
    )
    summary = item.get("summary") or name
    tags = item.get("niche_tags") or []
    customer = re.search(r"\bfor ([^.;!?]{3,80})", summary, re.I)
    fields = {
        "problem": summary,
        "customer": customer[1].strip() if customer else "Unspecified",
        "niche_tags": tags,
    }
    if os.getenv("INGEST_ENRICH") == "1" and (not customer or not tags):
        response = httpx.post(
            os.environ["TOOLS_URL"] + "/llm",
            json={
                "run_id": run_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract problem, customer and niche_tags from the supplied data. Return JSON. Use Unspecified for missing text and [] for missing tags.",
                    },
                    {
                        "role": "user",
                        "content": "<untrusted_data>"
                        + html.escape(summary[:8000])
                        + "</untrusted_data>",
                    },
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        import json

        result = json.loads(response.json()["content"])
        for key in fields:
            if fields[key] in ([], "Unspecified") and result.get(key):
                fields[key] = result[key]
    return Card(
        id=card_id(url),
        url=url,
        name=name,
        summary=summary,
        **fields,
        stage="unknown",
        funding_usd=None,
        source=item["source"],
        published_at=item.get("published_at"),
        fetched_at=item["fetched_at"],
        text=f"{name}. {summary}",
    )


def chunks(text):
    words = text.split()
    return [" ".join(words[i : i + 240]) for i in range(0, len(words), 240)]


def vector(text):
    values = [0.0] * DIMENSIONS
    for token in re.findall(r"\w+", text.casefold()):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        values[int.from_bytes(digest, "big") % DIMENSIONS] += 1 if digest[0] & 1 else -1
    norm = math.sqrt(sum(v * v for v in values)) or 1
    return [v / norm for v in values]


def point_id(chunk_id):
    return str(uuid5(NAMESPACE_URL, chunk_id))
