"""Heuristic participant policies for simulation action selection."""

from __future__ import annotations

# pyright: reportMissingImports=false

from typing import Literal

from younggeul_core.state.simulation import ActionProposal, ParticipantState

from ..schemas.round import DecisionContext, validate_v01_action
from .protocol import ParticipantPolicy


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _proposal(
    *,
    participant: ParticipantState,
    context: DecisionContext,
    action_type: Literal["buy", "sell", "hold"],
    confidence: float,
    reasoning_summary: str,
    proposed_value: dict[str, object] | None = None,
) -> ActionProposal:
    action = ActionProposal(
        agent_id=participant.participant_id,
        round_no=context.round_no,
        action_type=action_type,
        target_segment=context.segment.gu_code,
        confidence=_clamp_confidence(confidence),
        reasoning_summary=reasoning_summary,
        proposed_value=proposed_value,
    )
    validate_v01_action(action)
    return action


class BuyerPolicy(ParticipantPolicy):
    """Policy for primary buyers reacting to sentiment and trend."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Choose a buyer action for the current round.

        Args:
            participant: Buyer participant state.
            context: Decision context for this round.

        Returns:
            Action proposal for the buyer.
        """
        segment = context.segment
        should_buy = segment.sentiment_index > 0.5 and segment.price_trend != "down" and participant.capital > 0
        intensity = participant.risk_tolerance * segment.sentiment_index

        if should_buy:
            return _proposal(
                participant=participant,
                context=context,
                action_type="buy",
                confidence=intensity,
                reasoning_summary="Buyer entering due to positive sentiment and non-downtrend.",
                proposed_value={"max_budget": participant.capital},
            )

        return _proposal(
            participant=participant,
            context=context,
            action_type="hold",
            confidence=0.0,
            reasoning_summary="Buyer holding due to weak setup or no available capital.",
        )


class InvestorPolicy(ParticipantPolicy):
    """Policy for investors balancing momentum and downside risk."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Choose an investor action for the current round.

        Args:
            participant: Investor participant state.
            context: Decision context for this round.

        Returns:
            Action proposal for the investor.
        """
        segment = context.segment

        if segment.price_trend == "up" and segment.sentiment_index > 0.6:
            intensity = participant.risk_tolerance * segment.sentiment_index
            return _proposal(
                participant=participant,
                context=context,
                action_type="buy",
                confidence=intensity,
                reasoning_summary="Investor buying into sustained uptrend and strong sentiment.",
                proposed_value={"max_budget": participant.capital},
            )

        if segment.price_trend == "down" and participant.holdings > 0:
            intensity = participant.risk_tolerance * (1.0 - segment.sentiment_index)
            return _proposal(
                participant=participant,
                context=context,
                action_type="sell",
                confidence=intensity,
                reasoning_summary="Investor reducing exposure on downtrend with inventory available.",
            )

        return _proposal(
            participant=participant,
            context=context,
            action_type="hold",
            confidence=0.0,
            reasoning_summary="Investor holding due to non-actionable trend/sentiment mix.",
        )


class TenantPolicy(ParticipantPolicy):
    """Policy for tenants in v0.1, currently non-trading."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Choose a tenant action for the current round.

        Args:
            participant: Tenant participant state.
            context: Decision context for this round.

        Returns:
            Action proposal for the tenant.
        """
        return _proposal(
            participant=participant,
            context=context,
            action_type="hold",
            confidence=0.0,
            reasoning_summary="Tenant holding — no buy/sell in v0.1",
        )


class LandlordPolicy(ParticipantPolicy):
    """Policy for landlords focusing on risk-off selling signals."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Choose a landlord action for the current round.

        Args:
            participant: Landlord participant state.
            context: Decision context for this round.

        Returns:
            Action proposal for the landlord.
        """
        sentiment_index = context.segment.sentiment_index
        intensity = (1.0 - sentiment_index) * participant.risk_tolerance

        if sentiment_index < 0.3 and participant.holdings > 0:
            return _proposal(
                participant=participant,
                context=context,
                action_type="sell",
                confidence=intensity,
                reasoning_summary="Landlord selling into low sentiment to reduce downside risk.",
            )

        return _proposal(
            participant=participant,
            context=context,
            action_type="hold",
            confidence=0.0,
            reasoning_summary="Landlord holding while sentiment/holdings do not justify selling.",
        )


class BrokerPolicy(ParticipantPolicy):
    """Policy for brokers in v0.1, currently non-trading."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Choose a broker action for the current round.

        Args:
            participant: Broker participant state.
            context: Decision context for this round.

        Returns:
            Action proposal for the broker.
        """
        return _proposal(
            participant=participant,
            context=context,
            action_type="hold",
            confidence=0.0,
            reasoning_summary="Broker holding — facilitator role in v0.1",
        )
