from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from statistics import median
from typing import Any, Literal
from uuid import uuid4

from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import ParticipantState, ScenarioSpec, SegmentState, SnapshotRef

from ..events import EventStore, SimulationEvent
from ..graph_state import SimulationGraphState
from ..ports.snapshot_reader import SnapshotReader
from ..schemas.participant_roster import ParticipantRosterSpec

_FALLBACK_MEDIAN_PRICE = 500_000
_FALLBACK_VOLUME = 50


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _previous_month(period_start: date) -> str:
    if period_start.month == 1:
        return f"{period_start.year - 1}-12"
    return f"{period_start.year}-{period_start.month - 1:02d}"


def _derive_trend(
    metric: GoldDistrictMonthlyMetrics,
    forecast: BaselineForecast | None,
) -> Literal["up", "down", "flat"]:
    if forecast is not None:
        if forecast.direction == "up":
            return "up"
        if forecast.direction == "down":
            return "down"
        return "flat"
    if metric.mom_price_change is None:
        return "flat"
    if metric.mom_price_change > 0:
        return "up"
    if metric.mom_price_change < 0:
        return "down"
    return "flat"


def _build_segment(metric: GoldDistrictMonthlyMetrics, forecast: BaselineForecast | None) -> SegmentState:
    sentiment = 0.5
    if forecast is not None:
        direction_sign = 0.0
        if forecast.direction == "up":
            direction_sign = 1.0
        elif forecast.direction == "down":
            direction_sign = -1.0
        sentiment += direction_sign * 0.15 * forecast.direction_confidence

    if metric.net_migration is not None:
        if metric.net_migration > 0:
            sentiment += 0.1
        elif metric.net_migration < 0:
            sentiment -= 0.1

    supply_pressure = 0.0
    if metric.mom_volume_change is not None:
        supply_pressure = _clamp(metric.mom_volume_change, -1.0, 1.0)

    return SegmentState(
        gu_code=metric.gu_code,
        gu_name=metric.gu_name,
        current_median_price=metric.median_price,
        current_volume=metric.sale_count,
        price_trend=_derive_trend(metric, forecast),
        sentiment_index=_clamp(sentiment, 0.0, 1.0),
        supply_pressure=supply_pressure,
    )


def _build_fallback_segment(gu_code: str) -> SegmentState:
    return SegmentState(
        gu_code=gu_code,
        gu_name=gu_code,
        current_median_price=_FALLBACK_MEDIAN_PRICE,
        current_volume=_FALLBACK_VOLUME,
        price_trend="flat",
        sentiment_index=0.5,
        supply_pressure=0.0,
    )


def _deterministic_float(seed_bytes: bytes, index: int) -> float:
    hash_bytes = hashlib.sha256(seed_bytes + index.to_bytes(4, "big")).digest()
    return int.from_bytes(hash_bytes[:4], "big") / (2**32)


def _deterministic_int(seed_bytes: bytes, index: int, min_value: int, max_value: int) -> int:
    if min_value == max_value:
        return min_value
    value = _deterministic_float(seed_bytes, index)
    span = max_value - min_value + 1
    return min_value + int(value * span)


def _deterministic_interpolate(seed_bytes: bytes, index: int, min_value: float, max_value: float) -> float:
    if min_value == max_value:
        return min_value
    value = _deterministic_float(seed_bytes, index)
    return min_value + (max_value - min_value) * value


def _build_participants(
    roster: ParticipantRosterSpec,
    snapshot: SnapshotRef,
    scenario: ScenarioSpec,
    world: dict[str, SegmentState],
) -> dict[str, ParticipantState]:
    reference_price = int(median(segment.current_median_price for segment in world.values()))
    seed_bytes = (snapshot.dataset_snapshot_id + roster.seed + scenario.scenario_name).encode("utf-8")

    participants: dict[str, ParticipantState] = {}
    role_counters: dict[str, int] = {}
    rng_index = 0

    for bucket in roster.buckets:
        role_count = role_counters.get(bucket.role, 0)
        for _ in range(bucket.count):
            role_count += 1
            participant_id = f"{bucket.role}-{role_count:04d}"

            capital_min = int(reference_price * bucket.capital_min_multiplier)
            capital_max = int(reference_price * bucket.capital_max_multiplier)
            capital_low = min(capital_min, capital_max)
            capital_high = max(capital_min, capital_max)

            capital_float = _deterministic_interpolate(seed_bytes, rng_index, float(capital_low), float(capital_high))
            rng_index += 1
            holdings = _deterministic_int(seed_bytes, rng_index, bucket.holdings_min, bucket.holdings_max)
            rng_index += 1
            risk_tolerance = _deterministic_interpolate(seed_bytes, rng_index, bucket.risk_min, bucket.risk_max)
            rng_index += 1

            participants[participant_id] = ParticipantState(
                participant_id=participant_id,
                role=bucket.role,
                capital=int(capital_float),
                holdings=holdings,
                sentiment=bucket.sentiment_bias,
                risk_tolerance=risk_tolerance,
            )

        role_counters[bucket.role] = role_count

    return participants


def make_world_initializer_node(
    event_store: EventStore,
    snapshot_reader: SnapshotReader,
) -> Any:
    def node(state: SimulationGraphState) -> dict[str, Any]:
        scenario = state.get("scenario")
        if scenario is None:
            raise ValueError("scenario is required before world_initializer")

        participant_roster_raw = state.get("participant_roster")
        if participant_roster_raw is None:
            raise ValueError("participant_roster is required before world_initializer")

        snapshot = state.get("snapshot")
        if snapshot is None:
            raise ValueError("snapshot is required before world_initializer")

        run_meta = state.get("run_meta")
        if run_meta is None:
            raise ValueError("run_meta is required before emitting simulation events")

        roster = ParticipantRosterSpec.model_validate(participant_roster_raw)
        metrics = snapshot_reader.get_latest_metrics(snapshot, scenario.target_gus)
        forecasts = snapshot_reader.get_baseline_forecasts(snapshot, scenario.target_gus)

        metrics_by_gu = {metric.gu_code: metric for metric in metrics}
        forecast_by_gu = {forecast.gu_code: forecast for forecast in forecasts}

        warnings: list[str] = []
        world: dict[str, SegmentState] = {}
        for gu_code in scenario.target_gus:
            metric = metrics_by_gu.get(gu_code)
            if metric is None:
                warnings.append(f"No gold metrics found for gu_code={gu_code}; using fallback defaults.")
                world[gu_code] = _build_fallback_segment(gu_code)
                continue

            world[gu_code] = _build_segment(metric, forecast_by_gu.get(gu_code))

        participants = _build_participants(roster, snapshot, scenario, world)

        anchor_period = _previous_month(scenario.target_period_start)
        event_id = str(uuid4())
        event_store.append(
            SimulationEvent(
                event_id=event_id,
                run_id=run_meta.run_id,
                round_no=0,
                event_type="WORLD_INITIALIZED",
                timestamp=datetime.now(timezone.utc),
                payload={
                    "world_summary": {
                        gu_code: {
                            "median_price": segment.current_median_price,
                            "volume": segment.current_volume,
                        }
                        for gu_code, segment in world.items()
                    },
                    "participant_count": len(participants),
                    "anchor_period": anchor_period,
                    "warnings": warnings,
                },
            )
        )

        return {
            "world": world,
            "participants": participants,
            "round_no": 0,
            "governance_actions": {},
            "market_actions": {},
            "last_outcome": None,
            "event_refs": [event_id],
            "evidence_refs": [],
            "warnings": warnings,
        }

    return node
