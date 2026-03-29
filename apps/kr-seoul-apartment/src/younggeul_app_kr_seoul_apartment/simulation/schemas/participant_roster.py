from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoleBucketSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["buyer", "investor", "tenant", "landlord", "broker"]
    count: int = Field(ge=1, le=50)
    capital_min_multiplier: float = Field(ge=0.0, le=10.0)
    capital_max_multiplier: float = Field(ge=0.0, le=10.0)
    holdings_min: int = Field(ge=0, le=20)
    holdings_max: int = Field(ge=0, le=20)
    risk_min: float = Field(ge=0.0, le=1.0)
    risk_max: float = Field(ge=0.0, le=1.0)
    sentiment_bias: Literal["bearish", "neutral", "bullish"]


class ParticipantRosterSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: str
    buckets: list[RoleBucketSpec] = Field(min_length=1)
