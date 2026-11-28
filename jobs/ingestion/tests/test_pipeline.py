from pathlib import Path
from contracts import Card
from qdrant_client import QdrantClient
from foundation import connect
from ingestion import extract, canonical
from ingestion.pipeline import ingest, export, COLLECTION
from psycopg.types.json import Jsonb


def test_pipeline_replay_and_snapshot(migrated_db, tmp_path: Path):
    row = dict(
        name="A tool",
        summary="A tool for students",
        url="https://www.example.org/tool/?utm_source=x",
        source="hn",
        published_at=None,
        fetched_at="2026-11-28",
        niche_tags=[],
    )
    assert canonical(row["url"]) == "https://example.org/tool"
    with connect() as db:
        for source in ("hn", "github"):
            db.execute(
                "INSERT INTO raw_items(source,url,item) VALUES(%s,%s,%s)",
                (source, row["url"], Jsonb({**row, "source": source})),
            )
    client = QdrantClient(":memory:")
    assert ingest(client=client)["added"] == 1
    assert ingest(client=client)["added"] == 0
    path = tmp_path / "cards.jsonl.gz"
    export(path)
    assert ingest(path, client)["added"] == 0
    with connect() as db:
        assert db.execute("SELECT count(*) AS n FROM card_sources").fetchone()["n"] == 2
        card = Card.model_validate(
            db.execute("SELECT card FROM cards").fetchone()["card"]
        )
        assert card.id == extract(row, "r").id
    assert client.scroll(COLLECTION)[0][0].payload["chunk_id"] == card.id + "#c0"
