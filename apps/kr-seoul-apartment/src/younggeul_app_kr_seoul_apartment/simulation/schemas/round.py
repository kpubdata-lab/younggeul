"""Round-resolution schemas and action validation helpers."""

from __future__ import annotations

# pyright: reportMissingImports=false

from pydantic import BaseModel, Field, field_validator

from younggeul_core.state.simulation import ActionProposal, RoundOutcome, ScenarioSpec, SegmentState, Shock

V01_ACTION_TYPES: frozenset[str] = frozenset({"buy", "sell", "hold"})


class DecisionContext(BaseModel, frozen=True):
    """Context provided to participant policies for round decisions.

    Attributes:
        round_no: Current round number.
        segment: Target segment state for decisioning.
        scenario: Active simulation scenario.
        last_outcome: Previous round outcome when available.
        active_shocks: Active shocks affecting the round.
        governance_modifiers: Governance modifiers applied to decisions.
    """

    round_no: int = Field(ge=0)
    segment: SegmentState
    scenario: ScenarioSpec
    last_outcome: RoundOutcome | None = None
    active_shocks: list[Shock] = Field(default_factory=list)
    governance_modifiers: dict[str, float] = Field(default_factory=dict)


class SegmentDelta(BaseModel, frozen=True):
    """Resolved changes applied to a segment during a round.

    Attributes:
        gu_code: Segment district code.
        price_change_pct: Relative median-price change for the segment.
        volume_change: Net volume change for the segment.
        new_median_price: Updated median price after resolution.
        new_volume: Updated volume after resolution.
    """

    gu_code: str
    price_change_pct: float
    volume_change: int
    new_median_price: int = Field(ge=0)
    new_volume: int = Field(ge=0)

    @field_validator("price_change_pct")
    @classmethod
    def validate_price_change_pct(cls, value: float) -> float:
        """Validate price change bounds for v0.1 resolver outputs.

        Args:
            value: Candidate price change percentage.

        Returns:
            Validated price change percentage.

        Raises:
            ValueError: When the percentage is outside allowed bounds.
        """
        if not -0.05 <= value <= 0.05:
            raise ValueError("price_change_pct must be between -0.05 and 0.05")
        return value


class ParticipantDelta(BaseModel, frozen=True):
    """Resolved capital and holdings changes for one participant.

    Attributes:
        participant_id: Participant identifier.
        capital_change: Capital delta applied in this round.
        holdings_change: Holdings delta applied in this round.
        new_capital: Participant capital after applying changes.
        new_holdings: Participant holdings after applying changes.
    """

    participant_id: str
    capital_change: int
    holdings_change: int
    new_capital: int
    new_holdings: int = Field(ge=0)


class RoundResolvedPayload(BaseModel, frozen=True):
    """Event payload describing outcomes of one resolved round.

    Attributes:
        round_no: Resolved round number.
        segment_deltas: Segment-level deltas keyed by district code.
        participant_deltas: Participant-level deltas keyed by participant ID.
        transactions_count: Number of resolved transactions.
        summary: Human-readable round summary.
    """

    round_no: int = Field(ge=0)
    segment_deltas: dict[str, SegmentDelta]
    participant_deltas: dict[str, ParticipantDelta]
    transactions_count: int = Field(ge=0)
    summary: str


def validate_v01_action(action: ActionProposal) -> None:
    """Validate that an action uses one of the supported v0.1 action types.

    Args:
        action: Action proposal to validate.

    Raises:
        ValueError: When the action type is not supported in v0.1.
    """
    if action.action_type not in V01_ACTION_TYPES:
        raise ValueError(f"Unsupported v0.1 action_type: {action.action_type}")
