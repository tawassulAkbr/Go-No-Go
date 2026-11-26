from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EvidenceId = Annotated[str, Field(pattern=r"^[^#\s]+#c[0-9]+$")]
Dimension = Literal[
    "demand_pain", "competition", "differentiation", "feasibility", "risk", "learning"
]
Score = Annotated[float, Field(ge=0, le=5)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Percentage = Annotated[float, Field(ge=0, le=100)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
