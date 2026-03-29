from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, TypeVar, cast

import pytest
from pydantic import BaseModel

from younggeul_app_kr_seoul_apartment.simulation.event_store import InMemoryEventStore
from younggeul_app_kr_seoul_apartment.simulation.graph import build_simulation_graph
from younggeul_app_kr_seoul_apartment.simulation.graph_state import seed_graph_state
from younggeul_app_kr_seoul_apartment.simulation.llm.ports import LLMMessage
from younggeul_app_kr_seoul_apartment.simulation.nodes.scenario_builder import ScenarioSelection
from younggeul_app_kr_seoul_apartment.simulation.nodes.world_initializer import make_world_initializer_node
from younggeul_app_kr_seoul_apartment.simulation.ports.snapshot_reader import SnapshotCoverage
from younggeul_app_kr_seoul_apartment.simulation.schemas.intake import IntakePlan
from younggeul_app_kr_seoul_apartment.simulation.schemas.participant_roster import (
    ParticipantRosterSpec,
    RoleBucketSpec,
)
from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import ScenarioSpec, SnapshotRef

T = TypeVar("T", bound=BaseModel)


def _make_snapshot_ref(seed: str = "a") -> SnapshotRef:
    return SnapshotRef(
        dataset_snapshot_id=seed * 64,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        table_count=3,
    )


def _make_scenario(**overrides: Any) -> ScenarioSpec:
    payload: dict[str, Any] = {
        "scenario_name": "World Init Test",
        "target_gus": ["11680"],
        "target_period_start": date(2026, 1, 1),
        "target_period_end": date(2026, 6, 1),
        "shocks": [],
    }
    payload.update(overrides)
    return ScenarioSpec(**payload)


def _make_bucket(**overrides: Any) -> RoleBucketSpec:
    payload: dict[str, Any] = {
        "role": "buyer",
        "count": 4,
        "capital_min_multiplier": 0.8,
        "capital_max_multiplier": 1.2,
        "holdings_min": 0,
        "holdings_max": 2,
        "risk_min": 0.2,
        "risk_max": 0.8,
        "sentiment_bias": "neutral",
    }
    payload.update(overrides)
    return RoleBucketSpec(**payload)


def _make_roster(seed: str = "seed-01", buckets: list[RoleBucketSpec] | None = None) -> ParticipantRosterSpec:
    return ParticipantRosterSpec(seed=seed, buckets=buckets or [_make_bucket()])


def _make_metric(**overrides: Any) -> GoldDistrictMonthlyMetrics:
    payload: dict[str, Any] = {
        "gu_code": "11680",
        "gu_name": "강남구",
        "period": "2025-12",
        "sale_count": 140,
        "avg_price": 1_950_000,
        "median_price": 1_900_000,
        "min_price": 1_100_000,
        "max_price": 2_500_000,
        "price_per_pyeong_avg": 5_900,
        "yoy_price_change": 0.08,
        "mom_price_change": 0.02,
        "yoy_volume_change": 0.15,
        "mom_volume_change": 0.1,
        "avg_area_m2": Decimal("84.7"),
        "base_interest_rate": Decimal("3.25"),
        "net_migration": 220,
        "dataset_snapshot_id": "a" * 64,
    }
    payload.update(overrides)
    return GoldDistrictMonthlyMetrics(**payload)


def _make_forecast(**overrides: Any) -> BaselineForecast:
    payload: dict[str, Any] = {
        "gu_code": "11680",
        "gu_name": "강남구",
        "target_period": "2026-01",
        "direction": "up",
        "direction_confidence": 0.7,
        "predicted_volume": 130,
        "predicted_median_price": 1_920_000,
        "model_name": "baseline-v1",
        "features_used": ["mom_price_change", "net_migration"],
    }
    payload.update(overrides)
    return BaselineForecast(**payload)


def _make_coverage() -> SnapshotCoverage:
    return SnapshotCoverage(
        available_gu_codes=["11680", "11650"],
        available_gu_names={"11680": "강남구", "11650": "서초구"},
        min_period="2024-01",
        max_period="2025-12",
        record_count=200,
    )


def _make_intake_plan() -> IntakePlan:
    return IntakePlan(
        user_query="강남구 시뮬레이션",
        objective="가격 및 거래량 가정 검증",
        analysis_mode="baseline",
        geography_hint="강남구",
        segment_hint="아파트",
        horizon_months=6,
        requested_shocks=["금리인상"],
        participant_focus=["실수요자", "투자자"],
        constraints=[],
        assumptions=[],
        ambiguities=[],
    )


class FakeSnapshotReader:
    def __init__(
        self,
        *,
        coverage: SnapshotCoverage | None = None,
        metrics: list[GoldDistrictMonthlyMetrics] | None = None,
        forecasts: list[BaselineForecast] | None = None,
    ) -> None:
        self._coverage = coverage or _make_coverage()
        self._metrics = metrics or []
        self._forecasts = forecasts or []

    def get_coverage(self, snapshot: SnapshotRef) -> SnapshotCoverage:
        _ = snapshot
        return self._coverage

    def get_latest_metrics(
        self,
        snapshot: SnapshotRef,
        gu_codes: list[str] | None = None,
    ) -> list[GoldDistrictMonthlyMetrics]:
        _ = snapshot
        if gu_codes is None:
            return list(self._metrics)
        selected = set(gu_codes)
        return [metric for metric in self._metrics if metric.gu_code in selected]

    def get_baseline_forecasts(
        self,
        snapshot: SnapshotRef,
        gu_codes: list[str] | None = None,
    ) -> list[BaselineForecast]:
        _ = snapshot
        if gu_codes is None:
            return list(self._forecasts)
        selected = set(gu_codes)
        return [forecast for forecast in self._forecasts if forecast.gu_code in selected]


class FakeMultiplexStructuredLLM:
    def __init__(self, intake_plan: IntakePlan, selection: ScenarioSelection) -> None:
        self._intake_plan = intake_plan
        self._selection = selection

    def generate_structured(
        self,
        *,
        messages: list[LLMMessage],
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        _ = messages
        _ = temperature
        if response_model is IntakePlan:
            return cast(T, response_model.model_validate(self._intake_plan.model_dump()))
        return cast(T, response_model.model_validate(self._selection.model_dump()))


def _base_state(
    run_id: str,
    *,
    scenario: ScenarioSpec | None = None,
    roster: ParticipantRosterSpec | None = None,
    snapshot: SnapshotRef | None = None,
) -> dict[str, Any]:
    state = seed_graph_state("질문", run_id, f"run-{run_id}", "gpt-test")
    state["scenario"] = scenario or _make_scenario()
    state["participant_roster"] = (roster or _make_roster()).model_dump()
    state["snapshot"] = snapshot or _make_snapshot_ref()
    return state


class TestWorldBuilding:
    def test_builds_segment_state_from_gold_metrics(self) -> None:
        store = InMemoryEventStore()
        metric = _make_metric(median_price=2_100_000, sale_count=99)
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[metric], forecasts=[]))

        result = node(_base_state("world-build-01"))

        segment = result["world"]["11680"]
        assert segment.gu_code == "11680"
        assert segment.gu_name == "강남구"
        assert segment.current_median_price == 2_100_000
        assert segment.current_volume == 99

    def test_uses_forecast_direction_for_price_trend_when_available(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store,
            FakeSnapshotReader(
                metrics=[_make_metric(mom_price_change=-0.4)], forecasts=[_make_forecast(direction="up")]
            ),
        )

        result = node(_base_state("world-build-02"))

        assert result["world"]["11680"].price_trend == "up"

    @pytest.mark.parametrize(
        ("mom_price_change", "expected"),
        [(0.03, "up"), (-0.02, "down")],
    )
    def test_derives_price_trend_from_mom_change_without_forecast(self, mom_price_change: float, expected: str) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store,
            FakeSnapshotReader(metrics=[_make_metric(mom_price_change=mom_price_change)], forecasts=[]),
        )

        result = node(_base_state("world-build-03"))

        assert result["world"]["11680"].price_trend == expected

    def test_defaults_flat_trend_when_no_forecast_and_no_mom_data(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store, FakeSnapshotReader(metrics=[_make_metric(mom_price_change=None)], forecasts=[])
        )

        result = node(_base_state("world-build-04"))

        assert result["world"]["11680"].price_trend == "flat"

    def test_sentiment_index_adjusts_from_forecast_direction_and_confidence(self) -> None:
        store = InMemoryEventStore()
        metric = _make_metric(net_migration=0)
        forecast = _make_forecast(direction="down", direction_confidence=0.8)
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[metric], forecasts=[forecast]))

        result = node(_base_state("world-build-05"))

        assert result["world"]["11680"].sentiment_index == pytest.approx(0.38)

    @pytest.mark.parametrize(
        ("migration", "expected"),
        [(30, 0.6), (-25, 0.4), (0, 0.5)],
    )
    def test_sentiment_index_adjusts_from_net_migration(self, migration: int, expected: float) -> None:
        store = InMemoryEventStore()
        metric = _make_metric(net_migration=migration)
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[metric], forecasts=[]))

        result = node(_base_state("world-build-06"))

        assert result["world"]["11680"].sentiment_index == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("direction", "confidence", "migration", "expected"),
        [
            ("up", 1.0, 100, 0.75),
            ("down", 1.0, -100, 0.25),
            ("up", 1.0, 10_000, 0.75),
            ("down", 1.0, -10_000, 0.25),
        ],
    )
    def test_sentiment_index_is_clamped(
        self,
        direction: str,
        confidence: float,
        migration: int,
        expected: float,
    ) -> None:
        store = InMemoryEventStore()
        metric = _make_metric(net_migration=migration)
        forecast = _make_forecast(direction=direction, direction_confidence=confidence)
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[metric], forecasts=[forecast]))

        result = node(_base_state("world-build-07"))

        assert 0.0 <= result["world"]["11680"].sentiment_index <= 1.0
        assert result["world"]["11680"].sentiment_index == pytest.approx(expected)

    def test_supply_pressure_uses_mom_volume_change(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store,
            FakeSnapshotReader(metrics=[_make_metric(mom_volume_change=0.42)], forecasts=[]),
        )

        result = node(_base_state("world-build-08"))

        assert result["world"]["11680"].supply_pressure == pytest.approx(0.42)

    def test_supply_pressure_defaults_to_zero_when_no_data(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store,
            FakeSnapshotReader(metrics=[_make_metric(mom_volume_change=None)], forecasts=[]),
        )

        result = node(_base_state("world-build-09"))

        assert result["world"]["11680"].supply_pressure == 0.0

    @pytest.mark.parametrize(
        ("mom_volume_change", "expected"),
        [(2.5, 1.0), (-3.4, -1.0)],
    )
    def test_supply_pressure_is_clamped(self, mom_volume_change: float, expected: float) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(
            store,
            FakeSnapshotReader(metrics=[_make_metric(mom_volume_change=mom_volume_change)], forecasts=[]),
        )

        result = node(_base_state("world-build-10"))

        assert result["world"]["11680"].supply_pressure == expected

    def test_missing_gu_data_produces_warning_and_fallback_segment(self) -> None:
        store = InMemoryEventStore()
        scenario = _make_scenario(target_gus=["11680", "11650"])
        node = make_world_initializer_node(
            store, FakeSnapshotReader(metrics=[_make_metric(gu_code="11680")], forecasts=[])
        )

        result = node(_base_state("world-build-11", scenario=scenario))

        assert any("gu_code=11650" in warning for warning in result["warnings"])
        fallback = result["world"]["11650"]
        assert fallback.current_median_price == 500_000
        assert fallback.current_volume == 50
        assert fallback.price_trend == "flat"
        assert fallback.sentiment_index == 0.5
        assert fallback.supply_pressure == 0.0


class TestParticipantGeneration:
    def test_generates_correct_number_of_participants(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(buckets=[_make_bucket(count=7), _make_bucket(role="tenant", count=5)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-01", roster=roster))

        assert len(result["participants"]) == 12

    def test_participant_ids_follow_role_nnnn_format(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(buckets=[_make_bucket(role="broker", count=3)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-02", roster=roster))

        assert set(result["participants"].keys()) == {"broker-0001", "broker-0002", "broker-0003"}

    def test_capital_within_bucket_bounds(self) -> None:
        store = InMemoryEventStore()
        metric = _make_metric(median_price=2_000_000)
        roster = _make_roster(buckets=[_make_bucket(count=8, capital_min_multiplier=0.5, capital_max_multiplier=0.7)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[metric], forecasts=[]))

        result = node(_base_state("participants-03", roster=roster))

        capitals = [participant.capital for participant in result["participants"].values()]
        assert all(1_000_000 <= capital <= 1_400_000 for capital in capitals)

    def test_holdings_within_bucket_bounds(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(buckets=[_make_bucket(count=9, holdings_min=3, holdings_max=4)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-04", roster=roster))

        assert all(3 <= participant.holdings <= 4 for participant in result["participants"].values())

    def test_risk_tolerance_within_bucket_bounds(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(buckets=[_make_bucket(count=11, risk_min=0.33, risk_max=0.34)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-05", roster=roster))

        assert all(0.33 <= participant.risk_tolerance <= 0.34 for participant in result["participants"].values())

    @pytest.mark.parametrize("bias", ["bearish", "neutral", "bullish"])
    def test_sentiment_maps_directly_from_bias(self, bias: str) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(buckets=[_make_bucket(sentiment_bias=bias)])
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-06", roster=roster))

        assert {participant.sentiment for participant in result["participants"].values()} == {bias}

    def test_same_inputs_produce_same_participants(self) -> None:
        reader = FakeSnapshotReader(metrics=[_make_metric()], forecasts=[])
        roster = _make_roster(seed="repeatable-seed", buckets=[_make_bucket(count=6)])
        state = _base_state("participants-07", roster=roster, snapshot=_make_snapshot_ref("b"))

        first = make_world_initializer_node(InMemoryEventStore(), reader)(state)
        second = make_world_initializer_node(InMemoryEventStore(), reader)(state)

        assert first["participants"] == second["participants"]

    def test_different_seeds_produce_different_participants(self) -> None:
        reader = FakeSnapshotReader(metrics=[_make_metric()], forecasts=[])
        first = make_world_initializer_node(InMemoryEventStore(), reader)(
            _base_state("participants-08-a", roster=_make_roster(seed="seed-a"))
        )
        second = make_world_initializer_node(InMemoryEventStore(), reader)(
            _base_state("participants-08-b", roster=_make_roster(seed="seed-b"))
        )

        assert first["participants"] != second["participants"]

    def test_multiple_buckets_generate_all_participants(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(
            buckets=[
                _make_bucket(role="buyer", count=2),
                _make_bucket(role="investor", count=3),
                _make_bucket(role="tenant", count=1),
            ]
        )
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-09", roster=roster))

        assert set(result["participants"].keys()) == {
            "buyer-0001",
            "buyer-0002",
            "investor-0001",
            "investor-0002",
            "investor-0003",
            "tenant-0001",
        }

    def test_same_role_across_multiple_buckets_uses_continuous_indexing(self) -> None:
        store = InMemoryEventStore()
        roster = _make_roster(
            buckets=[
                _make_bucket(role="buyer", count=2),
                _make_bucket(role="buyer", count=2, capital_min_multiplier=1.5, capital_max_multiplier=2.0),
            ]
        )
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("participants-10", roster=roster))

        assert set(result["participants"].keys()) == {"buyer-0001", "buyer-0002", "buyer-0003", "buyer-0004"}


class TestWorldInitializerNodeBehavior:
    def test_returns_expected_state_update_keys(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("node-01"))

        assert set(result.keys()) == {
            "world",
            "participants",
            "round_no",
            "governance_actions",
            "market_actions",
            "last_outcome",
            "event_refs",
            "evidence_refs",
            "warnings",
        }

    def test_emits_world_initialized_event(self) -> None:
        run_id = "node-02"
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state(run_id))

        events = store.get_events_by_type(run_id, "WORLD_INITIALIZED")
        assert len(events) == 1
        assert events[0].event_id == result["event_refs"][0]

    def test_event_payload_has_expected_structure(self) -> None:
        run_id = "node-03"
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        node(_base_state(run_id))
        event = store.get_events_by_type(run_id, "WORLD_INITIALIZED")[0]

        assert set(event.payload.keys()) == {"world_summary", "participant_count", "anchor_period", "warnings"}
        assert event.payload["anchor_period"] == "2025-12"
        assert event.payload["world_summary"]["11680"]["median_price"] == 1_900_000
        assert event.payload["world_summary"]["11680"]["volume"] == 140

    def test_round_no_is_set_to_zero(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        result = node(_base_state("node-04"))

        assert result["round_no"] == 0

    def test_raises_when_scenario_missing(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))
        state = seed_graph_state("질문", "node-05", "run-node-05", "gpt-test")
        state["participant_roster"] = _make_roster().model_dump()
        state["snapshot"] = _make_snapshot_ref()

        with pytest.raises(ValueError, match="scenario is required"):
            node(state)

    def test_raises_when_run_meta_missing(self) -> None:
        store = InMemoryEventStore()
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))
        state = _base_state("node-06")
        del state["run_meta"]

        with pytest.raises(ValueError, match="run_meta is required"):
            node(state)

    def test_anchor_period_uses_previous_month_for_non_january_start(self) -> None:
        store = InMemoryEventStore()
        scenario = _make_scenario(target_period_start=date(2026, 7, 1), target_period_end=date(2026, 9, 1))
        node = make_world_initializer_node(store, FakeSnapshotReader(metrics=[_make_metric()], forecasts=[]))

        node(_base_state("node-07", scenario=scenario))
        event = store.get_events_by_type("node-07", "WORLD_INITIALIZED")[0]

        assert event.payload["anchor_period"] == "2026-06"


class TestGraphWiringForWorldInitializer:
    def test_build_graph_with_snapshot_reader_uses_real_world_initializer(self) -> None:
        run_id = "graph-world-real"
        store = InMemoryEventStore()
        reader = FakeSnapshotReader(
            metrics=[_make_metric()],
            forecasts=[_make_forecast(direction="down", direction_confidence=0.9)],
        )
        llm = FakeMultiplexStructuredLLM(
            _make_intake_plan(),
            ScenarioSelection(
                scenario_name="Real Init Scenario",
                selected_shock_keys=["rate_up"],
                roster_buckets=[_make_bucket(role="buyer", count=2)],
            ),
        )
        graph = build_simulation_graph(store, structured_llm=llm, snapshot_reader=reader)
        state = seed_graph_state("강남구 아파트", run_id, "run-real", "gpt-test")
        state["snapshot"] = _make_snapshot_ref()
        state["max_rounds"] = 0

        final = graph.invoke(state)

        world_event = store.get_events_by_type(run_id, "WORLD_INITIALIZED")[0]
        assert "world_summary" in world_event.payload
        assert "max_rounds" not in world_event.payload
        assert final["world"]["11680"].gu_name == "강남구"

    def test_build_graph_without_snapshot_reader_uses_stub_world_initializer(self) -> None:
        run_id = "graph-world-stub"
        store = InMemoryEventStore()
        llm = FakeMultiplexStructuredLLM(
            _make_intake_plan(),
            ScenarioSelection(
                scenario_name="Should Not Be Used",
                selected_shock_keys=["rate_up"],
                roster_buckets=[_make_bucket(role="buyer", count=2)],
            ),
        )
        graph = build_simulation_graph(store, structured_llm=llm)
        state = seed_graph_state("기본 시나리오", run_id, "run-stub", "gpt-test")
        state["max_rounds"] = 0

        final = graph.invoke(state)

        world_event = store.get_events_by_type(run_id, "WORLD_INITIALIZED")[0]
        assert world_event.payload == {"max_rounds": 0}
        assert final["world"]["11680"].gu_name == "강남구"
