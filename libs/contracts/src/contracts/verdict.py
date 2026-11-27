from math import isclose
from typing import Annotated, Literal, Self, get_args

from pydantic import Field, JsonValue, NonNegativeInt, PositiveInt, model_validator

from .common import Confidence, Dimension, Percentage, Record, Score, Text
from .scores import DimensionScore

Outcome = Literal["GO", "PIVOT", "NO-GO", "INSUFFICIENT_EVIDENCE"]
GateName = Literal["evidence", "feasibility", "risk", "duplicate"]


class Gate(Record):
    status: Literal["pass", "fail"]
    reason: Text
    detail: dict[str, JsonValue]


class Thresholds(Record):
    T_go: Percentage
    T_no: Percentage
    floor: Score
    min_confidence: Confidence = 0.5

    @model_validator(mode="after")
    def ordered_thresholds(self) -> Self:
        if self.T_go <= self.T_no:
            raise ValueError("T_go must exceed T_no")
        return self


class Flip(Record):
    run: PositiveInt
    change: Text
    verdict: Outcome


class Sensitivity(Record):
    runs: NonNegativeInt
    flipped: NonNegativeInt
    flips: list[Flip]

    @model_validator(mode="after")
    def validate_flips(self) -> Self:
        ids = {flip.run for flip in self.flips}
        if (
            self.flipped != len(self.flips)
            or len(ids) != self.flipped
            or any(run > self.runs for run in ids)
        ):
            raise ValueError("each flip must identify a distinct sensitivity run")
        return self


class WhatIf(Record):
    change: Text
    new_score: Percentage
    new_verdict: Outcome


class Versions(Record):
    engine: Text
    rubrics: Text
    profile_weights: Text
    config: Text


class Verdict(Record):
    idea_id: Text
    version: PositiveInt
    run_id: Text
    verdict: Outcome
    stability: Literal["STABLE", "BORDERLINE"]
    score: Percentage | None
    confidence: Confidence
    gates: Annotated[dict[GateName, Gate], Field(min_length=1)]
    weights: dict[Dimension, Percentage]
    thresholds: Thresholds
    scores: Annotated[list[DimensionScore], Field(min_length=6, max_length=6)]
    weakest_dimension: Dimension | None
    what_would_make_go: list[WhatIf]
    sensitivity: Sensitivity
    versions: Versions
    missing_evidence: list[Text]

    @model_validator(mode="after")
    def validate_summary(self) -> Self:
        dimensions = set(get_args(Dimension))
        if {item.dimension for item in self.scores} != dimensions:
            raise ValueError("scores must cover all six dimensions")
        if self.weights.keys() != dimensions or not isclose(
            sum(self.weights.values()), 100
        ):
            raise ValueError("all six weights must be present and sum to 100")
        if self.verdict == "INSUFFICIENT_EVIDENCE" and not self.missing_evidence:
            raise ValueError("describe the missing evidence")
        if self.verdict == "PIVOT" and self.weakest_dimension is None:
            raise ValueError("PIVOT must name its weakest dimension")
        if self.verdict in ("GO", "PIVOT") and self.score is None:
            raise ValueError("GO and PIVOT require a weighted score")
        if self.verdict in ("GO", "PIVOT") and (
            self.gates.keys() != set(get_args(GateName))
            or any(g.status == "fail" for g in self.gates.values())
        ):
            raise ValueError("GO and PIVOT require all four gates to pass")
        if (self.stability == "BORDERLINE") != bool(self.sensitivity.flipped):
            raise ValueError("stability must agree with sensitivity flips")
        return self
