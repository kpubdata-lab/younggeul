from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, TypeVar, cast

import pytest
from pydantic import BaseModel, ValidationError

from younggeul_app_kr_seoul_apartment.simulation.domain.gu_resolver import resolve_gu_codes
from younggeul_app_kr_seoul_apartment.simulation.domain.shock_catalog import (
    SUPPORTED_SHOCK_KEYS,
    expand_shock,
    normalize_shock_key,
)
from younggeul_app_kr_seoul_apartment.simulation.event_store import InMemoryEventStore
from younggeul_app_kr_seoul_apartment.simulation.graph import build_simulation_graph
from younggeul_app_kr_seoul_apartment.simulation.graph_state import seed_graph_state
from younggeul_app_kr_seoul_apartment.simulation.llm.ports import LLMMessage
from younggeul_app_kr_seoul_apartment.simulation.nodes.scenario_builder import (
    ScenarioSelection,
    compute_max_rounds,
    make_scenario_builder_node,
)
from younggeul_app_kr_seoul_apartment.simulation.ports.snapshot_reader import SnapshotCoverage
from younggeul_app_kr_seoul_apartment.simulation.schemas.intake import IntakePlan
from younggeul_app_kr_seoul_apartment.simulation.schemas.participant_roster import (
    ParticipantRosterSpec,
    RoleBucketSpec,
)
from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import ScenarioSpec, SnapshotRef

T = TypeVar("T", bound=BaseModel)


def _make_snapshot_ref() -> SnapshotRef:
    return SnapshotRef(
        dataset_snapshot_id="a" * 64,
        created_at=datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc),
        table_count=2,
    )


def _make_coverage(**overrides: Any) -> SnapshotCoverage:
    payload: dict[str, Any] = {
        "available_gu_codes": ["11680", "11650", "11710"],
        "available_gu_names": {
            "11680": "강남구",
            "11650": "서초구",
            "11710": "송파구",
        },
        "min_period": "2024-01",
        "max_period": "2025-12",
        "record_count": 999,
    }
    payload.update(overrides)
    return SnapshotCoverage(**payload)


def _make_intake_plan(**overrides: Any) -> IntakePlan:
    payload: dict[str, Any] = {
        "user_query": "강남구 스트레스 테스트",
        "objective": "충격 하에서 가격·거래량 변화를 점검한다.",
        "analysis_mode": "stress",
        "geography_hint": "강남구",
        "segment_hint": "아파트",
        "horizon_months": 6,
        "requested_shocks": ["금리인상", "규제강화"],
        "participant_focus": ["실수요자", "투자자"],
        "constraints": [],
        "assumptions": [],
        "ambiguities": [],
    }
    payload.update(overrides)
    return IntakePlan(**payload)


def _make_role_bucket(**overrides: Any) -> RoleBucketSpec:
    payload: dict[str, Any] = {
        "role": "buyer",
        "count": 10,
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


def _make_selection(**overrides: Any) -> ScenarioSelection:
    payload: dict[str, Any] = {
        "scenario_name": "Stress Case Alpha",
        "selected_shock_keys": ["rate_up", "regulation_tighten"],
        "roster_buckets": [_make_role_bucket(), _make_role_bucket(role="investor", count=6)],
    }
    payload.update(overrides)
    return ScenarioSelection(**payload)


class FakeStructuredLLM:
    def __init__(self, response: BaseModel, *, bypass_validation: bool = False) -> None:
        self._response = response
        self._bypass_validation = bypass_validation
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        messages: list[LLMMessage],
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        self.calls.append(
            {
                "messages": list(messages),
                "response_model": response_model,
                "temperature": temperature,
            }
        )
        if self._bypass_validation:
            return cast(T, self._response)
        return response_model.model_validate(self._response.model_dump())


class FakeMultiplexStructuredLLM:
    def __init__(self, intake_plan: IntakePlan, selection: ScenarioSelection) -> None:
        self._intake_plan = intake_plan
        self._selection = selection
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        messages: list[LLMMessage],
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        self.calls.append(
            {
                "messages": list(messages),
                "response_model": response_model,
                "temperature": temperature,
            }
        )
        if response_model is IntakePlan:
            return cast(T, response_model.model_validate(self._intake_plan.model_dump()))
        return cast(T, response_model.model_validate(self._selection.model_dump()))


class FakeSnapshotReader:
    def __init__(
        self,
        coverage: SnapshotCoverage,
        metrics: list[GoldDistrictMonthlyMetrics] | None = None,
        forecasts: list[BaselineForecast] | None = None,
    ) -> None:
        self.coverage = coverage
        self.metrics = metrics or []
        self.forecasts = forecasts or []

    def get_coverage(self, snapshot: SnapshotRef) -> SnapshotCoverage:
        _ = snapshot
        return self.coverage

    def get_latest_metrics(
        self,
        snapshot: SnapshotRef,
        gu_codes: list[str] | None = None,
    ) -> list[GoldDistrictMonthlyMetrics]:
        _ = snapshot
        _ = gu_codes
        return self.metrics

    def get_baseline_forecasts(
        self,
        snapshot: SnapshotRef,
        gu_codes: list[str] | None = None,
    ) -> list[BaselineForecast]:
        _ = snapshot
        _ = gu_codes
        return self.forecasts


class TestSnapshotCoverageSchema:
    def test_constructs_with_valid_fields(self) -> None:
        coverage = _make_coverage()

        assert coverage.min_period == "2024-01"
        assert coverage.max_period == "2025-12"
        assert coverage.available_gu_names["11680"] == "강남구"

    def test_is_frozen(self) -> None:
        coverage = _make_coverage()

        with pytest.raises(ValidationError):
            coverage.max_period = "2026-01"


class TestParticipantRosterSpecSchema:
    def test_role_bucket_valid_construction(self) -> None:
        bucket = _make_role_bucket(role="landlord", count=3)

        assert bucket.role == "landlord"
        assert bucket.count == 3

    def test_role_bucket_rejects_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            _make_role_bucket(role="developer")

    @pytest.mark.parametrize("count", [1, 50])
    def test_role_bucket_accepts_count_boundaries(self, count: int) -> None:
        bucket = _make_role_bucket(count=count)

        assert bucket.count == count

    @pytest.mark.parametrize("count", [0, 51])
    def test_role_bucket_rejects_count_out_of_range(self, count: int) -> None:
        with pytest.raises(ValidationError):
            _make_role_bucket(count=count)

    @pytest.mark.parametrize("field,value", [("risk_min", -0.01), ("risk_max", 1.01)])
    def test_role_bucket_rejects_risk_bounds(self, field: str, value: float) -> None:
        with pytest.raises(ValidationError):
            _make_role_bucket(**{field: value})

    def test_roster_requires_non_empty_buckets(self) -> None:
        with pytest.raises(ValidationError):
            ParticipantRosterSpec(seed="abc", buckets=[])

    def test_roster_is_frozen(self) -> None:
        roster = ParticipantRosterSpec(seed="seed-1", buckets=[_make_role_bucket()])

        with pytest.raises(ValidationError):
            roster.seed = "changed"

    def test_roster_valid_construction(self) -> None:
        roster = ParticipantRosterSpec(seed="seed-1", buckets=[_make_role_bucket(), _make_role_bucket(role="tenant")])

        assert len(roster.buckets) == 2


class TestShockCatalog:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("rate_up", "rate_up"),
            ("  rate_down  ", "rate_down"),
            ("DEMAND_SURGE", "demand_surge"),
        ],
    )
    def test_normalize_shock_key_for_english(self, raw: str, expected: str) -> None:
        assert normalize_shock_key(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("금리인상", "rate_up"),
            ("금리 인하", "rate_down"),
            ("수요증가", "demand_surge"),
            ("공급 확대", "supply_increase"),
            ("규제완화", "regulation_loosen"),
            ("심리위축", "sentiment_drop"),
        ],
    )
    def test_normalize_shock_key_for_korean_aliases(self, raw: str, expected: str) -> None:
        assert normalize_shock_key(raw) == expected

    @pytest.mark.parametrize("raw", ["", "unknown", "가격상승", "sentiment_up"])
    def test_normalize_shock_key_unknown_returns_none(self, raw: str) -> None:
        assert normalize_shock_key(raw) is None

    def test_expand_shock_returns_valid_shock(self) -> None:
        shock = expand_shock("rate_up", ["11680", "11650"], "2026-01", "2026-06")

        assert shock.shock_type == "interest_rate"
        assert shock.description == "Interest rate hike"
        assert shock.magnitude == 0.3
        assert shock.target_segments == ["11680", "11650"]

    def test_expand_shock_raises_on_unknown_key(self) -> None:
        with pytest.raises(KeyError):
            expand_shock("unknown_key", ["11680"], "2026-01", None)

    def test_supported_shock_keys_exposes_catalog(self) -> None:
        assert "rate_up" in SUPPORTED_SHOCK_KEYS
        assert SUPPORTED_SHOCK_KEYS["rate_up"]["description"] == "Interest rate hike"


class TestGuResolver:
    def test_none_hint_returns_all_available(self) -> None:
        resolved, warnings = resolve_gu_codes(None, ["11680", "11710"])

        assert resolved == ["11680", "11710"]
        assert warnings == []

    def test_exact_code_match(self) -> None:
        resolved, warnings = resolve_gu_codes("11680", ["11680", "11710"])

        assert resolved == ["11680"]
        assert warnings == []

    def test_exact_name_match(self) -> None:
        resolved, warnings = resolve_gu_codes("서초구", ["11650", "11710"])

        assert resolved == ["11650"]
        assert warnings == []

    def test_substring_name_match(self) -> None:
        resolved, warnings = resolve_gu_codes("강남구와 송파구를 보고 싶다", ["11680", "11710", "11650"])

        assert resolved == ["11680", "11710"]
        assert warnings == []

    def test_unresolved_hint_returns_all_plus_warning(self) -> None:
        resolved, warnings = resolve_gu_codes("부산 해운대", ["11680", "11710"])

        assert resolved == ["11680", "11710"]
        assert len(warnings) == 1
        assert "Could not resolve geography hint" in warnings[0]

    def test_exact_code_unavailable_returns_warning(self) -> None:
        resolved, warnings = resolve_gu_codes("11680", ["11710"])

        assert resolved == ["11710"]
        assert len(warnings) == 1
        assert "unavailable" in warnings[0]


class TestMaxRoundsFormula:
    @pytest.mark.parametrize(
        "horizon,shock_count,mode,expected",
        [
            (1, 0, "baseline", 1),
            (3, 0, "baseline", 1),
            (6, 1, "baseline", 2),
            (6, 2, "baseline", 3),
            (6, 2, "stress", 4),
            (12, 0, "compare", 5),
            (60, 5, "stress", 8),
        ],
    )
    def test_compute_max_rounds(self, horizon: int, shock_count: int, mode: str, expected: int) -> None:
        assert compute_max_rounds(horizon, shock_count, mode) == expected


def _make_state_for_builder(
    run_id: str,
    *,
    intake_plan: IntakePlan | None = None,
    snapshot: SnapshotRef | None = None,
) -> dict[str, Any]:
    plan = intake_plan or _make_intake_plan()
    state = seed_graph_state(plan.user_query, run_id, f"run-{run_id}", "gpt-test")
    state["intake_plan"] = plan.model_dump()
    state["snapshot"] = snapshot or _make_snapshot_ref()
    return state


class TestScenarioBuilderNode:
    def test_returns_state_update_with_expected_keys(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))

        result = node(_make_state_for_builder("scenario-node-001"))

        assert set(result.keys()) == {"scenario", "participant_roster", "max_rounds", "warnings", "event_refs"}
        assert isinstance(result["scenario"], ScenarioSpec)
        assert isinstance(result["participant_roster"], dict)
        assert isinstance(result["max_rounds"], int)

    def test_emits_scenario_built_event(self) -> None:
        run_id = "scenario-node-002"
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))

        result = node(_make_state_for_builder(run_id))
        events = store.get_events_by_type(run_id, "SCENARIO_BUILT")

        assert len(events) == 1
        assert events[0].event_id == result["event_refs"][0]
        assert events[0].payload["scenario"]["scenario_name"] == "Stress Case Alpha"

    def test_resolves_geography_using_hint(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))
        state = _make_state_for_builder("scenario-node-003", intake_plan=_make_intake_plan(geography_hint="서초구"))

        result = node(state)

        assert result["scenario"].target_gus == ["11650"]

    def test_computes_period_from_coverage_and_horizon(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        coverage = _make_coverage(max_period="2025-11")
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(coverage))
        state = _make_state_for_builder("scenario-node-004", intake_plan=_make_intake_plan(horizon_months=4))

        result = node(state)

        assert result["scenario"].target_period_start == date(2025, 12, 1)
        assert result["scenario"].target_period_end == date(2026, 3, 1)

    def test_filters_invalid_shock_keys(self) -> None:
        store = InMemoryEventStore()
        selection = _make_selection(selected_shock_keys=["rate_up", "does_not_exist", "금리인하"])
        llm = FakeStructuredLLM(selection)
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))

        result = node(_make_state_for_builder("scenario-node-005"))

        shocks = result["scenario"].shocks
        assert len(shocks) == 2
        assert shocks[0].description == "Interest rate hike"
        assert shocks[1].description == "Interest rate cut"

    def test_post_validates_roster_buckets_and_clamps_counts(self) -> None:
        store = InMemoryEventStore()
        unsafe = ScenarioSelection.model_construct(
            scenario_name="Unsafe",
            selected_shock_keys=["rate_up"],
            roster_buckets=[
                RoleBucketSpec.model_construct(
                    role="buyer",
                    count=999,
                    capital_min_multiplier=-1,
                    capital_max_multiplier=20,
                    holdings_min=-3,
                    holdings_max=99,
                    risk_min=-2,
                    risk_max=3,
                    sentiment_bias="rocket",
                ),
                RoleBucketSpec.model_construct(
                    role="ghost",
                    count=5,
                    capital_min_multiplier=1,
                    capital_max_multiplier=2,
                    holdings_min=0,
                    holdings_max=1,
                    risk_min=0.1,
                    risk_max=0.2,
                    sentiment_bias="neutral",
                ),
            ],
        )
        llm = FakeStructuredLLM(unsafe, bypass_validation=True)
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))

        result = node(_make_state_for_builder("scenario-node-006"))
        buckets = result["participant_roster"]["buckets"]

        assert len(buckets) == 1
        assert buckets[0]["role"] == "buyer"
        assert buckets[0]["count"] == 50
        assert buckets[0]["capital_min_multiplier"] == 0.0
        assert buckets[0]["capital_max_multiplier"] == 10.0
        assert buckets[0]["holdings_min"] == 0
        assert buckets[0]["holdings_max"] == 20
        assert buckets[0]["risk_min"] == 0.0
        assert buckets[0]["risk_max"] == 1.0
        assert buckets[0]["sentiment_bias"] == "neutral"

    def test_compare_mode_adds_warning(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))
        state = _make_state_for_builder("scenario-node-007", intake_plan=_make_intake_plan(analysis_mode="compare"))

        result = node(state)

        assert any("Compare mode" in warning for warning in result["warnings"])

    def test_stress_mode_adds_default_shock_if_none_selected(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection(selected_shock_keys=[]))
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))
        state = _make_state_for_builder("scenario-node-008", intake_plan=_make_intake_plan(analysis_mode="stress"))

        result = node(state)

        assert len(result["scenario"].shocks) == 1
        assert result["scenario"].shocks[0].description == "Market sentiment deterioration"
        assert any("Stress mode requires at least one shock" in warning for warning in result["warnings"])

    def test_calls_llm_with_scenario_selection_response_model(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))

        node(_make_state_for_builder("scenario-node-009"))

        assert len(llm.calls) == 1
        assert llm.calls[0]["response_model"] is ScenarioSelection
        assert llm.calls[0]["temperature"] == 0.0
        assert llm.calls[0]["messages"][0]["role"] == "system"

    def test_raises_if_snapshot_missing(self) -> None:
        store = InMemoryEventStore()
        llm = FakeStructuredLLM(_make_selection())
        node = make_scenario_builder_node(store, llm, FakeSnapshotReader(_make_coverage()))
        state = seed_graph_state("질문", "scenario-node-010", "run", "gpt-test")
        state["intake_plan"] = _make_intake_plan().model_dump()

        with pytest.raises(ValueError, match="snapshot is required"):
            node(state)


class TestGraphWiringForScenarioBuilder:
    def test_uses_real_scenario_builder_when_llm_and_snapshot_reader_provided(self) -> None:
        run_id = "graph-real-scenario"
        store = InMemoryEventStore()
        plan = _make_intake_plan(analysis_mode="baseline")
        llm = FakeMultiplexStructuredLLM(plan, _make_selection(scenario_name="Real Scenario"))
        reader = FakeSnapshotReader(_make_coverage())
        graph = build_simulation_graph(store, structured_llm=llm, snapshot_reader=reader)
        state = _make_state_for_builder(run_id, intake_plan=plan)
        state["max_rounds"] = 0

        final = graph.invoke(state)

        assert final["scenario"].scenario_name == "Real Scenario"
        assert "participant_roster" in final
        assert (
            store.get_events_by_type(run_id, "SCENARIO_BUILT")[0].payload["scenario"]["scenario_name"]
            == "Real Scenario"
        )

    def test_uses_stub_scenario_builder_when_snapshot_reader_missing(self) -> None:
        run_id = "graph-stub-scenario"
        store = InMemoryEventStore()
        llm = FakeMultiplexStructuredLLM(
            _make_intake_plan(analysis_mode="baseline"), _make_selection(scenario_name="Should Not Appear")
        )
        graph = build_simulation_graph(store, structured_llm=llm)
        seed = seed_graph_state("기본 시나리오", run_id, "run-stub", "gpt-test")
        seed["max_rounds"] = 0

        final = graph.invoke(seed)

        assert final["scenario"].scenario_name == "Stub Scenario"


def test_fake_snapshot_reader_signature_smoke() -> None:
    coverage = _make_coverage()
    metrics = [
        GoldDistrictMonthlyMetrics(
            gu_code="11680",
            gu_name="강남구",
            period="2025-12",
            sale_count=10,
            avg_price=100,
            median_price=90,
            min_price=50,
            max_price=150,
            price_per_pyeong_avg=80,
            yoy_price_change=0.1,
            mom_price_change=0.01,
            yoy_volume_change=0.2,
            mom_volume_change=0.03,
            avg_area_m2=Decimal("84.5"),
            base_interest_rate=Decimal("3.25"),
            net_migration=20,
            dataset_snapshot_id="a" * 64,
        )
    ]
    forecasts = [
        BaselineForecast(
            gu_code="11680",
            gu_name="강남구",
            target_period="2026-01",
            direction="up",
            direction_confidence=0.7,
            predicted_volume=12,
            predicted_median_price=95,
            model_name="baseline-v1",
            features_used=["mom_price_change"],
        )
    ]
    reader = FakeSnapshotReader(coverage, metrics=metrics, forecasts=forecasts)
    snapshot = _make_snapshot_ref()

    assert reader.get_coverage(snapshot) == coverage
    assert reader.get_latest_metrics(snapshot) == metrics
    assert reader.get_baseline_forecasts(snapshot) == forecasts
