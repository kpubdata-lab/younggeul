"""Participant roster schemas for deterministic agent generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoleBucketSpec(BaseModel):
    """Role bucket definition used when creating participants.

    Attributes:
        role: Participant role represented by the bucket.
        count: Number of participants to generate for the role.
        capital_min_multiplier: Minimum capital multiplier vs reference price.
        capital_max_multiplier: Maximum capital multiplier vs reference price.
        holdings_min: Minimum initial holdings.
        holdings_max: Maximum initial holdings.
        risk_min: Minimum risk tolerance.
        risk_max: Maximum risk tolerance.
        sentiment_bias: Initial sentiment bias for generated participants.
    """

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
    """Roster specification describing participant generation inputs.

    Attributes:
        seed: Deterministic seed component for roster generation.
        buckets: Role buckets to materialize into participants.
    """

    model_config = ConfigDict(frozen=True)

    seed: str
    buckets: list[RoleBucketSpec] = Field(min_length=1)
