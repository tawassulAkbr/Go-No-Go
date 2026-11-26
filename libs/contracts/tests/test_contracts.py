import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import Card, DimensionScore, Evidence, Profile, Trace, Verdict
from contracts.export import export

PROFILE = dict(
    user_id="u1",
    skills=["python"],
    hours_per_week=10,
    weeks_available=12,
    team_size=2,
    compute="laptop",
    goal="portfolio",
    interests=[],
)
CARD = dict(
    id="card_1",
    name="Exporter",
    summary="Fast exports",
    problem="Slow exports",
    customer="Students",
    niche_tags=["tools"],
    stage="unknown",
    funding_usd=None,
    source="hackernews",
    url="https://example.org/item",
    published_at=None,
    fetched_at="2026-11-26",
    text="Export is slow.",
)
EVIDENCE = dict(
    evidence_id="card_1#c0",
    card_id="card_1",
    quote=CARD["text"],
    source=CARD["source"],
    url=CARD["url"],
    retrieved_at="2026-11-26T04:00:00Z",
)
SCORE = dict(
    dimension="competition",
    score=3,
    confidence=0.8,
    evidence_ids=["card_1#c0"],
    reason="Export is slow [card_1#c0]",
    rubric_version="competition@v1",
    model="test",
)
TRACE = dict(
    run_id="r1",
    step_id=1,
    parent_step=None,
    agent="validator",
    kind="decision",
    tool=None,
    input={"id": "card_1"},
    output="ok",
    tokens_in=0,
    tokens_out=0,
    cost_usd=0,
    latency_ms=1,
    retries=0,
    model=None,
    cache_hit=False,
    error=None,
    ts=EVIDENCE["retrieved_at"],
)
WEIGHTS = dict(
    demand_pain=15,
    competition=15,
    differentiation=15,
    feasibility=25,
    risk=10,
    learning=20,
)
VERDICT = dict(
    idea_id="idea_1",
    version=1,
    run_id="r1",
    verdict="PIVOT",
    stability="STABLE",
    score=60,
    confidence=0.8,
    gates={
        key: dict(status="pass", reason="Checked", detail={})
        for key in ("evidence", "feasibility", "risk", "duplicate")
    },
    weights=WEIGHTS,
    thresholds=dict(T_go=70, T_no=50, floor=1.5),
    scores=[dict(SCORE, dimension=d, rubric_version=f"{d}@v1") for d in WEIGHTS],
    weakest_dimension="competition",
    what_would_make_go=[],
    sensitivity=dict(runs=0, flipped=0, flips=[]),
    versions=dict(engine="m11@v1", rubrics="r1", profile_weights="w1", config="c1"),
    missing_evidence=[],
)


@pytest.mark.parametrize(
    "model,data",
    [
        (Profile, PROFILE),
        (Card, CARD),
        (Evidence, EVIDENCE),
        (DimensionScore, SCORE),
        (Trace, TRACE),
        (Verdict, VERDICT),
    ],
)
def test_wire_round_trip(model, data):
    record = model.model_validate_json(json.dumps(data))
    assert model.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize(
    "model,data,changes",
    [
        (Profile, PROFILE, {"team_size": 0}),
        (Card, CARD, {"url": "file:///tmp/item"}),
        (Evidence, EVIDENCE, {"card_id": "card_2"}),
        (Evidence, EVIDENCE, {"evidence_id": "card_1#cx"}),
        (Trace, TRACE, {"cost_usd": -0.1}),
        (DimensionScore, SCORE, {"evidence_ids": []}),
        (DimensionScore, SCORE, {"score": 5.1}),
        (DimensionScore, SCORE, {"confidence": -0.01}),
        (DimensionScore, SCORE, {"abstained": True, "score": 0}),
        (DimensionScore, SCORE, {"abstained": True, "confidence": 0}),
        (Verdict, VERDICT, {"scores": [SCORE] * 6}),
        (Verdict, VERDICT, {"weights": dict(WEIGHTS, risk=0)}),
        (Verdict, VERDICT, {"weakest_dimension": None}),
        (Verdict, VERDICT, {"gates": {"risk": VERDICT["gates"]["risk"]}}),
        (
            Verdict,
            VERDICT,
            {
                "gates": VERDICT["gates"]
                | {
                    "duplicate": dict(
                        status="fail",
                        reason="Existing product",
                        detail={"name": "Exporter"},
                    )
                }
            },
        ),
        (Verdict, VERDICT, {"verdict": "INSUFFICIENT_EVIDENCE"}),
        (Verdict, VERDICT, {"sensitivity": dict(runs=14, flipped=1, flips=[])}),
    ],
)
def test_invalid_records(model, data, changes):
    with pytest.raises(ValidationError):
        model.model_validate(data | changes)


def test_abstention_without_citation():
    record = DimensionScore.model_validate(
        SCORE | dict(score=0, confidence=0, abstained=True, evidence_ids=[])
    )
    assert record.abstained


def test_early_evidence_gate_exit():
    record = Verdict.model_validate(
        VERDICT
        | dict(
            verdict="INSUFFICIENT_EVIDENCE",
            score=None,
            gates={
                "evidence": dict(
                    status="fail", reason="Only one source", detail={"sources": 1}
                )
            },
            weakest_dimension=None,
            missing_evidence=["Two more independent sources"],
        )
    )
    assert record.score is None


def test_export_matches_checked_in_schemas(tmp_path):
    export(tmp_path)
    checked_in = Path(__file__).resolve().parents[1] / "schemas"
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.json")} == {
        p.name: p.read_bytes() for p in checked_in.glob("*.json")
    }
