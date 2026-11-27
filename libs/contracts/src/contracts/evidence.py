from datetime import datetime
from typing import Self

from pydantic import HttpUrl, model_validator

from .common import EvidenceId, Record, Text


class Evidence(Record):
    evidence_id: EvidenceId
    card_id: Text
    quote: Text
    source: Text
    url: HttpUrl
    retrieved_at: datetime

    @model_validator(mode="after")
    def validate_card_reference(self) -> Self:
        if self.evidence_id.split("#")[0] != self.card_id:
            raise ValueError("evidence_id must reference card_id")
        return self
