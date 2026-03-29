"""Intake planning schema for simulation query interpretation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IntakePlan(BaseModel, frozen=True):
    """Structured intake output produced from user simulation intent.

    Attributes:
        user_query: Original user query text.
        objective: Primary simulation objective summary.
        analysis_mode: Requested analysis mode.
        geography_hint: Optional district hint from the query.
        segment_hint: Optional property segment hint.
        horizon_months: Requested simulation horizon in months.
        requested_shocks: Requested shock labels from the query.
        participant_focus: Participant groups to emphasize.
        constraints: Explicit user constraints.
        assumptions: User-provided assumptions.
        ambiguities: Unresolved ambiguities from intake parsing.
    """

    user_query: str
    objective: str
    analysis_mode: Literal["baseline", "stress", "compare"]
    geography_hint: str | None = None
    segment_hint: str | None = None
    horizon_months: int = Field(ge=1, le=120)
    requested_shocks: list[str] = Field(default_factory=list)
    participant_focus: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
