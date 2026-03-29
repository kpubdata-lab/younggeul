"""Participant decision node for producing market action proposals."""

from __future__ import annotations

# pyright: reportMissingImports=false

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from younggeul_core.state.simulation import (
    ActionProposal,
    RoundOutcome,
    ScenarioSpec,
    SegmentState,
    Shock,
)

from ..events import EventStore, SimulationEvent
from ..graph_state import SimulationGraphState
from ..policies.protocol import ParticipantPolicy
from ..policies.registry import get_default_policy
from ..schemas.round import DecisionContext

_SHOCK_MODIFIER_KEYS: dict[str, str] = {
    "interest_rate": "interest_rate_delta",
    "regulation": "regulation_severity",
    "supply": "supply_delta",
    "demand": "demand_delta",
}


def _derive_governance_modifiers(shocks: list[Shock]) -> dict[str, float]:
    modifiers: dict[str, float] = {}
    for shock in shocks:
        modifier_key = _SHOCK_MODIFIER_KEYS.get(shock.shock_type)
        if modifier_key is None:
            continue
        modifiers[modifier_key] = modifiers.get(modifier_key, 0.0) + shock.magnitude
    return modifiers


def _resolve_target_segment(world: dict[str, SegmentState], scenario: ScenarioSpec) -> SegmentState:
    if not world:
        raise ValueError("world must contain at least one segment")

    target_gu = scenario.target_gus[0] if scenario.target_gus else None
    if target_gu is not None and target_gu in world:
        return world[target_gu]

    return next(iter(world.values()))


def _build_decision_context(
    *,
    round_no: int,
    segment: SegmentState,
    scenario: ScenarioSpec,
    last_outcome: RoundOutcome | None,
    active_shocks: list[Shock],
    governance_modifiers: dict[str, float],
) -> DecisionContext:
    return DecisionContext(
        round_no=round_no,
        segment=segment,
        scenario=scenario,
        last_outcome=last_outcome,
        active_shocks=active_shocks,
        governance_modifiers=governance_modifiers,
    )


def make_participant_decider_node(
    event_store: EventStore,
    *,
    policy_registry: Callable[[str], ParticipantPolicy] | None = None,
) -> Any:
    """Create the participant decider node for the simulation graph.

    The participant decider node applies role policies to generate per-
    participant market actions for the current round.

    Args:
        event_store: Event store used to publish decision events.
        policy_registry: Optional role-to-policy resolver.

    Returns:
        A LangGraph-compatible node function.
    """
    policy_lookup = policy_registry or get_default_policy

    def node(state: SimulationGraphState) -> dict[str, Any]:
        run_meta = state.get("run_meta")
        if run_meta is None:
            raise ValueError("run_meta is required")

        world = state.get("world")
        if world is None:
            raise ValueError("world is required")

        scenario = state.get("scenario")
        if scenario is None:
            raise ValueError("scenario is required")

        participants = state.get("participants", {})
        new_round_no = state.get("round_no", 0) + 1
        last_outcome = state.get("last_outcome")

        active_shocks = list(scenario.shocks)
        governance_modifiers = _derive_governance_modifiers(active_shocks)

        market_actions: dict[str, ActionProposal] = {}
        if participants:
            target_segment = _resolve_target_segment(world, scenario)
            for participant_id, participant in participants.items():
                context = _build_decision_context(
                    round_no=new_round_no,
                    segment=target_segment,
                    scenario=scenario,
                    last_outcome=last_outcome,
                    active_shocks=active_shocks,
                    governance_modifiers=governance_modifiers,
                )
                policy = policy_lookup(participant.role)
                market_actions[participant_id] = policy.decide(participant, context)

        event_id = str(uuid4())
        event_store.append(
            SimulationEvent(
                event_id=event_id,
                run_id=run_meta.run_id,
                round_no=new_round_no,
                event_type="DECISIONS_MADE",
                timestamp=datetime.now(timezone.utc),
                payload={
                    "round_no": new_round_no,
                    "action_summary": {
                        participant_id: {
                            "action_type": action.action_type,
                            "target": action.target_segment,
                        }
                        for participant_id, action in market_actions.items()
                    },
                    "total_actions": len(market_actions),
                },
            )
        )

        return {
            "round_no": new_round_no,
            "market_actions": market_actions,
            "event_refs": [event_id],
        }

    return node
