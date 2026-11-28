import gzip
import json
import os
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4
from contracts import Card
from foundation import connect
from psycopg.types.json import Jsonb
from qdrant_client import QdrantClient, models
from . import (
    DIMENSIONS,
    canonical,
    card_id,
    chunks,
    extract,
    name_key,
    point_id,
    vector,
)

COLLECTION = "idea_cards_v1"
SNAPSHOT = Path("data/snapshot/cards.jsonl.gz")


def index_client():
    return QdrantClient(url=os.environ["QDRANT_URL"], timeout=15)


def index(client, card, old_chunks):
    texts = chunks(card.text)
    points = []
    for number, text in enumerate(texts):
        cid = f"{card.id}#c{number}"
        embedding = vector(text)
        near = client.query_points(
            COLLECTION,
            query=embedding,
            limit=1,
            score_threshold=0.92,
            query_filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="card_id", match=models.MatchValue(value=card.id)
                    )
                ]
            ),
        ).points
        points.append(
            models.PointStruct(
                id=point_id(cid),
                vector=embedding,
                payload={
                    "chunk_id": cid,
                    "card_id": card.id,
                    "text": text,
                    "source": card.source,
                    "niche": card.niche_tags,
                    "published_at": card.published_at.isoformat()
                    if card.published_at
                    else None,
                    "near_duplicate": near[0].payload["card_id"] if near else None,
                },
            )
        )
    client.upsert(COLLECTION, points, wait=True)
    stale = [point_id(f"{card.id}#c{i}") for i in range(len(texts), old_chunks)]
    if stale:
        client.delete(COLLECTION, models.PointIdsList(points=stale), wait=True)


def persist(db, client, card):
    url = canonical(str(card.url))
    if card.id != card_id(url):
        raise ValueError("Card ID does not match canonical URL")
    key = name_key(card.name)
    row = db.execute(
        "SELECT card FROM cards WHERE url=%s OR name_key=%s ORDER BY (url=%s) DESC LIMIT 1",
        (url, key, url),
    ).fetchone()
    previous = Card.model_validate(row["card"]) if row else None
    stored = (
        previous
        if previous and (previous.id != card.id or previous.source != card.source)
        else card
    )
    if previous is None:
        db.execute(
            "INSERT INTO cards VALUES (%s,%s,%s,%s,%s)",
            (card.id, url, key, card.source, Jsonb(card.model_dump(mode="json"))),
        )
    elif stored is card:
        db.execute(
            "UPDATE cards SET card=%s,name_key=%s WHERE id=%s",
            (Jsonb(card.model_dump(mode="json")), key, card.id),
        )
    db.execute(
        "INSERT INTO card_sources VALUES(%s,%s,%s) ON CONFLICT(source,url) DO UPDATE SET card_id=excluded.card_id",
        (card.source, url, stored.id),
    )
    index(client, stored, len(chunks(previous.text)) if previous else 0)
    return previous is None


def export(path=SNAPSHOT):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + str(uuid4()))
    try:
        with (
            connect() as db,
            tmp.open("wb") as out,
            gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as z,
        ):
            for row in db.execute("SELECT card FROM cards ORDER BY id"):
                z.write(
                    (
                        json.dumps(row["card"], sort_keys=True, ensure_ascii=False)
                        + "\n"
                    ).encode()
                )
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def ingest(snapshot=None, client=None):
    run = str(uuid4())
    counts = Counter()
    added = dropped = 0
    start = time.monotonic()
    error = None
    client = client or index_client()
    try:
        with connect() as db:
            # Serialize across workers while committing each indexed row separately.
            db.autocommit = True
            db.execute("SELECT pg_advisory_lock(616041)")
            if not client.collection_exists(COLLECTION):
                client.create_collection(
                    COLLECTION,
                    vectors_config=models.VectorParams(
                        size=DIMENSIONS, distance=models.Distance.COSINE
                    ),
                )

            def process(card, raw_key=None):
                nonlocal added, dropped
                with db.transaction():
                    fresh = persist(db, client, card)
                    if raw_key:
                        db.execute(
                            "UPDATE raw_items SET pending=false WHERE source=%s AND url=%s AND item=%s",
                            raw_key,
                        )
                added += int(fresh)
                dropped += int(not fresh)
                counts[card.source] += 1

            if snapshot:
                with gzip.open(snapshot, "rt", encoding="utf-8") as f:
                    for line in f:
                        process(Card.model_validate_json(line))
            else:
                for row in db.execute(
                    "SELECT source,url,item FROM raw_items WHERE pending ORDER BY source,url"
                ):
                    process(
                        extract(row["item"], run),
                        (row["source"], row["url"], Jsonb(row["item"])),
                    )
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        with connect() as db:
            db.execute(
                """INSERT INTO ingestion_runs(run_id,source,added,dropped,counts,duration_s,error)
                VALUES(%s,'ingestion',%s,%s,%s,%s,%s)""",
                (
                    run,
                    added,
                    dropped,
                    Jsonb(dict(counts)),
                    time.monotonic() - start,
                    error,
                ),
            )
    return {"run_id": run, "added": added, "dropped": dropped, "counts": dict(counts)}
