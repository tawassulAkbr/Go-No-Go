from typing import Self

from pydantic import ConfigDict, Field, model_validator

from .common import Confidence, Dimension, EvidenceId, Record, Score, Text


class DimensionScore(Record):
    # Mirror the citation rule for consumers that validate the exported JSON Schema.
    model_config = ConfigDict(
        json_schema_extra={
            "if": {
                "required": ["abstained"],
                "properties": {"abstained": {"const": True}},
            },
            "then": {"properties": {"score": {"const": 0}, "confidence": {"const": 0}}},
            "else": {
                "required": ["evidence_ids"],
                "properties": {"evidence_ids": {"minItems": 1}},
            },
        }
    )
    dimension: Dimension
    score: Score
    confidence: Confidence
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    features: dict[str, float] = Field(default_factory=dict)
    reason: Text
    rubric_version: Text
    model: Text
    abstained: bool = False

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.abstained:
            if self.score != 0 or self.confidence != 0:
                raise ValueError("abstention requires zero score and confidence")
        elif not self.evidence_ids:
            raise ValueError("a score must cite evidence or abstain")
        return self
