from __future__ import annotations

# pyright: reportMissingImports=false

from datetime import date, datetime, timezone
from typing import Any

import pytest

from younggeul_app_kr_seoul_apartment.simulation.event_store import InMemoryEventStore
from younggeul_app_kr_seoul_apartment.simulation.graph_state import seed_graph_state
from younggeul_app_kr_seoul_apartment.simulation.nodes.participant_decider import make_participant_decider_node
from younggeul_app_kr_seoul_apartment.simulation.policies.protocol import ParticipantPolicy
from younggeul_app_kr_seoul_apartment.simulation.schemas.round import DecisionContext
from younggeul_core.state.simulation import (
    ActionProposal,
    ParticipantState,
    RoundOutcome,
    ScenarioSpec,
    SegmentState,
    Shock,
)


def _make_segment(**overrides: Any) -> SegmentState:
    payload: dict[str, Any] = {
        "gu_code": "11680",
        "gu_name": "강남구",
        "current_median_price": 1_900_000,
        "current_volume": 120,
        "price_trend": "up",
        "sentiment_index": 0.7,
        "supply_pressure": 0.1,
    }
    payload.update(overrides)
    return SegmentState(**payload)


def _make_shock(**overrides: Any) -> Shock:
    payload: dict[str, Any] = {
        "shock_type": "interest_rate",
        "description": "rate up",
        "magnitude": 0.3,
        "target_segments": ["11680"],
    }
    payload.update(overrides)
    return Shock(**payload)


def _make_scenario(**overrides: Any) -> ScenarioSpec:
    payload: dict[str, Any] = {
        "scenario_name": "Decider Test",
        "target_gus": ["11680"],
        "target_period_start": date(2026, 1, 1),
        "target_period_end": date(2026, 6, 1),
        "shocks": [],
    }
    payload.update(overrides)
    return ScenarioSpec(**payload)


def _make_participant(**overrides: Any) -> ParticipantState:
    payload: dict[str, Any] = {
        "participant_id": "buyer-0001",
        "role": "buyer",
        "capital": 500_000,
        "holdings": 1,
        "sentiment": "neutral",
        "risk_tolerance": 0.6,
    }
    payload.update(overrides)
    return ParticipantState(**payload)


def _make_outcome(**overrides: Any) -> RoundOutcome:
    payload: dict[str, Any] = {
        "round_no": 1,
        "cleared_volume": {"11680": 10},
        "price_changes": {"11680": 0.01},
        "governance_applied": ["ltv_tighten"],
        "market_actions_resolved": 4,
    }
    payload.update(overrides)
    return RoundOutcome(**payload)


def _base_state(run_id: str = "decider-run") -> dict[str, Any]:
    state = seed_graph_state("질문", run_id, f"run-{run_id}", "gpt-test")
    state["world"] = {
        "11680": _make_segment(gu_code="11680", gu_name="강남구"),
        "11650": _make_segment(gu_code="11650", gu_name="서초구", sentiment_index=0.4),
    }
    state["scenario"] = _make_scenario()
    state["participants"] = {
        "buyer-0001": _make_participant(participant_id="buyer-0001", role="buyer"),
    }
    state["round_no"] = 2
    state["last_outcome"] = _make_outcome(round_no=2)
    return state


class RecordingPolicy:
    def __init__(self, action_type: str = "hold") -> None:
        self.calls: list[tuple[ParticipantState, DecisionContext]] = []
        self._action_type = action_type

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        self.calls.append((participant, context))
        return ActionProposal(
            agent_id=participant.participant_id,
            round_no=context.round_no,
            action_type=self._action_type,
            target_segment=context.segment.gu_code,
            confidence=0.8,
            reasoning_summary="recorded",
        )


def test_collects_action_proposals_for_three_participants() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy("buy")
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("collect-three")
    state["participants"] = {
        "buyer-0001": _make_participant(participant_id="buyer-0001", role="buyer"),
        "investor-0001": _make_participant(participant_id="investor-0001", role="investor"),
        "tenant-0001": _make_participant(participant_id="tenant-0001", role="tenant"),
    }

    result = node(state)

    assert len(result["market_actions"]) == 3
    assert set(result["market_actions"].keys()) == {"buyer-0001", "investor-0001", "tenant-0001"}


def test_emits_event_with_correct_action_summary() -> None:
    run_id = "event-summary"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy("sell"))

    result = node(_base_state(run_id))
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]

    assert event.event_id == result["event_refs"][0]
    assert event.payload["round_no"] == 3
    assert event.payload["total_actions"] == 1
    assert event.payload["action_summary"] == {"buyer-0001": {"action_type": "sell", "target": "11680"}}


def test_increments_round_no_from_state_value() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())

    result = node(_base_state("round-increment"))

    assert result["round_no"] == 3


def test_round_no_defaults_to_one_when_missing() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state("round-default")
    del state["round_no"]

    result = node(state)

    assert result["round_no"] == 1


def test_custom_policy_registry_is_used_when_provided() -> None:
    store = InMemoryEventStore()
    calls: list[str] = []

    def registry(role: str) -> ParticipantPolicy:
        calls.append(role)
        return RecordingPolicy("buy")

    node = make_participant_decider_node(store, policy_registry=registry)
    state = _base_state("custom-registry")
    state["participants"] = {
        "buyer-0001": _make_participant(participant_id="buyer-0001", role="buyer"),
        "investor-0001": _make_participant(participant_id="investor-0001", role="investor"),
    }

    node(state)

    assert calls == ["buyer", "investor"]


def test_default_registry_is_used_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    import younggeul_app_kr_seoul_apartment.simulation.nodes.participant_decider as decider_module

    store = InMemoryEventStore()
    calls: list[str] = []

    def fake_default_policy(role: str) -> ParticipantPolicy:
        calls.append(role)
        return RecordingPolicy()

    monkeypatch.setattr(decider_module, "get_default_policy", fake_default_policy)
    node = make_participant_decider_node(store)

    node(_base_state("default-registry"))

    assert calls == ["buyer"]


def test_empty_participants_returns_empty_market_actions_and_still_emits_event() -> None:
    run_id = "empty-participants"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state(run_id)
    state["participants"] = {}

    result = node(state)

    assert result["market_actions"] == {}
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]
    assert event.payload["action_summary"] == {}
    assert event.payload["total_actions"] == 0


def test_missing_world_raises_value_error() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state("missing-world")
    del state["world"]

    with pytest.raises(ValueError, match="world is required"):
        node(state)


def test_missing_scenario_raises_value_error() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state("missing-scenario")
    del state["scenario"]

    with pytest.raises(ValueError, match="scenario is required"):
        node(state)


def test_missing_run_meta_raises_value_error() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state("missing-run-meta")
    del state["run_meta"]

    with pytest.raises(ValueError, match="run_meta is required"):
        node(state)


def test_different_roles_receive_different_policies() -> None:
    store = InMemoryEventStore()
    buyer_policy = RecordingPolicy("buy")
    investor_policy = RecordingPolicy("sell")

    def registry(role: str) -> ParticipantPolicy:
        return buyer_policy if role == "buyer" else investor_policy

    node = make_participant_decider_node(store, policy_registry=registry)
    state = _base_state("role-policy")
    state["participants"] = {
        "buyer-0001": _make_participant(participant_id="buyer-0001", role="buyer"),
        "investor-0001": _make_participant(participant_id="investor-0001", role="investor"),
    }

    result = node(state)

    assert result["market_actions"]["buyer-0001"].action_type == "buy"
    assert result["market_actions"]["investor-0001"].action_type == "sell"


def test_governance_modifiers_include_all_supported_shock_types() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("modifiers-all")
    state["scenario"] = _make_scenario(
        shocks=[
            _make_shock(shock_type="interest_rate", magnitude=0.3),
            _make_shock(shock_type="regulation", magnitude=0.4),
            _make_shock(shock_type="supply", magnitude=-0.2),
            _make_shock(shock_type="demand", magnitude=0.1),
        ]
    )

    node(state)
    context = policy.calls[0][1]

    assert context.governance_modifiers == {
        "interest_rate_delta": 0.3,
        "regulation_severity": 0.4,
        "supply_delta": -0.2,
        "demand_delta": 0.1,
    }


def test_governance_modifiers_accumulate_same_shock_type_magnitudes() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("modifiers-sum")
    state["scenario"] = _make_scenario(
        shocks=[
            _make_shock(shock_type="interest_rate", magnitude=0.2),
            _make_shock(shock_type="interest_rate", magnitude=0.1),
        ]
    )

    node(state)
    context = policy.calls[0][1]

    assert context.governance_modifiers == {"interest_rate_delta": pytest.approx(0.3)}


def test_external_shocks_are_ignored_in_governance_modifiers() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("modifiers-ignore-external")
    state["scenario"] = _make_scenario(
        shocks=[
            _make_shock(shock_type="external", magnitude=0.9),
            _make_shock(shock_type="demand", magnitude=-0.2),
        ]
    )

    node(state)
    context = policy.calls[0][1]

    assert context.governance_modifiers == {"demand_delta": -0.2}


def test_context_includes_last_outcome_from_state() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("last-outcome")
    outcome = _make_outcome(round_no=7, market_actions_resolved=9)
    state["last_outcome"] = outcome

    node(state)

    assert policy.calls[0][1].last_outcome == outcome


def test_context_active_shocks_matches_scenario_shocks() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("active-shocks")
    shocks = [_make_shock(magnitude=0.2), _make_shock(shock_type="supply", magnitude=-0.1)]
    state["scenario"] = _make_scenario(shocks=shocks)

    node(state)

    assert policy.calls[0][1].active_shocks == shocks


def test_context_round_no_uses_incremented_round() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("context-round")
    state["round_no"] = 9

    result = node(state)

    assert result["round_no"] == 10
    assert policy.calls[0][1].round_no == 10


def test_targets_first_scenario_gu_when_present_in_world() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("target-present")
    state["scenario"] = _make_scenario(target_gus=["11650", "11680"])

    node(state)

    assert policy.calls[0][1].segment.gu_code == "11650"


def test_falls_back_to_first_world_segment_when_target_gu_missing() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("target-missing")
    state["scenario"] = _make_scenario(target_gus=["99999"])

    node(state)

    assert policy.calls[0][1].segment.gu_code == "11680"


def test_uses_first_world_segment_when_target_gus_empty() -> None:
    store = InMemoryEventStore()
    policy = RecordingPolicy()
    node = make_participant_decider_node(store, policy_registry=lambda role: policy)
    state = _base_state("target-empty")
    state["scenario"] = _make_scenario(target_gus=[])

    node(state)

    assert policy.calls[0][1].segment.gu_code == "11680"


def test_same_state_produces_same_market_actions() -> None:
    state = _base_state("deterministic")
    first_store = InMemoryEventStore()
    second_store = InMemoryEventStore()

    first_result = make_participant_decider_node(first_store)(state)
    second_result = make_participant_decider_node(second_store)(state)

    assert first_result["round_no"] == second_result["round_no"]
    assert first_result["market_actions"] == second_result["market_actions"]


def test_event_round_no_matches_incremented_round() -> None:
    run_id = "event-round-no"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state(run_id)
    state["round_no"] = 4

    result = node(state)
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]

    assert result["round_no"] == 5
    assert event.round_no == 5
    assert event.payload["round_no"] == 5


def test_event_total_actions_matches_market_action_count() -> None:
    run_id = "event-total-actions"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state(run_id)
    state["participants"] = {
        "buyer-0001": _make_participant(participant_id="buyer-0001", role="buyer"),
        "investor-0001": _make_participant(participant_id="investor-0001", role="investor"),
        "tenant-0001": _make_participant(participant_id="tenant-0001", role="tenant"),
    }

    result = node(state)
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]

    assert event.payload["total_actions"] == 3
    assert len(result["market_actions"]) == 3


def test_raises_when_world_is_empty_and_participants_exist() -> None:
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state("empty-world")
    state["world"] = {}

    with pytest.raises(ValueError, match="world must contain at least one segment"):
        node(state)


def test_allows_empty_world_when_participants_are_empty() -> None:
    run_id = "empty-world-empty-participants"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())
    state = _base_state(run_id)
    state["world"] = {}
    state["participants"] = {}

    result = node(state)

    assert result["market_actions"] == {}
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]
    assert event.payload["total_actions"] == 0


def test_policy_errors_propagate_without_swallowing() -> None:
    class FailingPolicy:
        def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
            _ = participant
            _ = context
            raise RuntimeError("policy failed")

    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: FailingPolicy())

    with pytest.raises(RuntimeError, match="policy failed"):
        node(_base_state("policy-failure"))


def test_emitted_event_timestamp_is_timezone_aware() -> None:
    run_id = "event-tz"
    store = InMemoryEventStore()
    node = make_participant_decider_node(store, policy_registry=lambda role: RecordingPolicy())

    node(_base_state(run_id))
    event = store.get_events_by_type(run_id, "DECISIONS_MADE")[0]

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo == timezone.utc
