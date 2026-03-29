# pyright: reportMissingImports=false

"""Scenario builder node for assembling scenario and roster inputs."""

from __future__ import annotations

from datetime import date, datetime, timezone
from math import ceil
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, ValidationError

from younggeul_core.state.simulation import ScenarioSpec

from ..domain.gu_resolver import resolve_gu_codes
from ..domain.shock_catalog import SUPPORTED_SHOCK_KEYS, expand_shock, normalize_shock_key
from ..events import EventStore, SimulationEvent
from ..graph_state import SimulationGraphState
from ..llm.ports import LLMMessage, StructuredLLM
from ..ports.snapshot_reader import SnapshotReader
from ..schemas.intake import IntakePlan
from ..schemas.participant_roster import ParticipantRosterSpec, RoleBucketSpec

_ROLE_SET = {"buyer", "investor", "tenant", "landlord", "broker"}
_SENTIMENT_SET = {"bearish", "neutral", "bullish"}


class ScenarioSelection(BaseModel):
    """Structured LLM output used to select shocks and participant buckets.

    Attributes:
        scenario_name: Human-readable scenario name.
        selected_shock_keys: Shock catalog keys selected for the scenario.
        roster_buckets: Role bucket specifications for participant generation.
    """

    model_config = ConfigDict(frozen=True)

    scenario_name: str
    selected_shock_keys: list[str]
    roster_buckets: list[RoleBucketSpec]


def compute_max_rounds(horizon_months: int, shock_count: int, analysis_mode: str) -> int:
    """Compute the simulation round limit from intake characteristics.

    Args:
        horizon_months: Requested simulation horizon in months.
        shock_count: Number of selected shocks.
        analysis_mode: Intake analysis mode.

    Returns:
        Bounded max round count for the simulation.
    """
    base = ceil(horizon_months / 3)
    if shock_count >= 2:
        base += 1
    if analysis_mode in ("stress", "compare"):
        base += 1
    return min(8, max(1, base))


def _parse_period(period: str) -> tuple[int, int]:
    year_text, month_text = period.split("-", 1)
    return int(year_text), int(month_text)


def _month_start_after(period: str) -> date:
    year, month = _parse_period(period)
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _add_months(month_start: date, months: int) -> date:
    total_month = (month_start.year * 12 + month_start.month - 1) + months
    year = total_month // 12
    month = total_month % 12 + 1
    return date(year, month, 1)


def _clamp_int(value: Any, min_value: int, max_value: int, fallback: int) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(min_value, min(max_value, raw))


def _clamp_float(value: Any, min_value: float, max_value: float, fallback: float) -> float:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(min_value, min(max_value, raw))


def _sanitize_roster_buckets(raw_buckets: list[Any]) -> list[RoleBucketSpec]:
    sanitized: list[RoleBucketSpec] = []
    for raw_bucket in raw_buckets:
        bucket_data = raw_bucket if isinstance(raw_bucket, dict) else {}
        role = bucket_data.get("role")
        if role not in _ROLE_SET:
            continue

        count = _clamp_int(bucket_data.get("count", 1), 1, 50, 1)

        capital_min = _clamp_float(bucket_data.get("capital_min_multiplier", 0.5), 0.0, 10.0, 0.5)
        capital_max = _clamp_float(bucket_data.get("capital_max_multiplier", 1.5), 0.0, 10.0, 1.5)
        if capital_min > capital_max:
            capital_min, capital_max = capital_max, capital_min

        holdings_min = _clamp_int(bucket_data.get("holdings_min", 0), 0, 20, 0)
        holdings_max = _clamp_int(bucket_data.get("holdings_max", 2), 0, 20, 2)
        if holdings_min > holdings_max:
            holdings_min, holdings_max = holdings_max, holdings_min

        risk_min = _clamp_float(bucket_data.get("risk_min", 0.2), 0.0, 1.0, 0.2)
        risk_max = _clamp_float(bucket_data.get("risk_max", 0.8), 0.0, 1.0, 0.8)
        if risk_min > risk_max:
            risk_min, risk_max = risk_max, risk_min

        raw_sentiment = bucket_data.get("sentiment_bias")
        if raw_sentiment in _SENTIMENT_SET:
            sentiment_bias: Literal["bearish", "neutral", "bullish"] = cast(
                Literal["bearish", "neutral", "bullish"],
                raw_sentiment,
            )
        else:
            sentiment_bias = "neutral"

        sanitized.append(
            RoleBucketSpec(
                role=role,
                count=count,
                capital_min_multiplier=capital_min,
                capital_max_multiplier=capital_max,
                holdings_min=holdings_min,
                holdings_max=holdings_max,
                risk_min=risk_min,
                risk_max=risk_max,
                sentiment_bias=sentiment_bias,
            )
        )

    if sanitized:
        return sanitized

    return [
        RoleBucketSpec(
            role="buyer",
            count=10,
            capital_min_multiplier=0.8,
            capital_max_multiplier=1.2,
            holdings_min=0,
            holdings_max=2,
            risk_min=0.2,
            risk_max=0.7,
            sentiment_bias="neutral",
        )
    ]


def _build_system_prompt(plan: IntakePlan) -> str:
    shock_lines = [
        f"- {key}: {value['description']} ({value['shock_type']}, magnitude={value['magnitude']})"
        for key, value in SUPPORTED_SHOCK_KEYS.items()
    ]
    roles = sorted(_ROLE_SET)
    return "\n".join(
        [
            "You are the scenario builder for a Seoul apartment simulation.",
            "Choose only from the supported shock catalog keys and role options.",
            "Return ScenarioSelection JSON only.",
            "",
            "Supported shock keys:",
            *shock_lines,
            "",
            f"Supported roles: {', '.join(roles)}",
            "",
            "User intake context:",
            f"- objective: {plan.objective}",
            f"- analysis_mode: {plan.analysis_mode}",
            f"- requested_shocks: {plan.requested_shocks}",
            f"- participant_focus: {plan.participant_focus}",
            f"- horizon_months: {plan.horizon_months}",
        ]
    )


def _normalize_selected_shocks(raw_keys: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_key in raw_keys:
        normalized_key = normalize_shock_key(raw_key)
        if normalized_key is None:
            continue
        if normalized_key not in normalized:
            normalized.append(normalized_key)
    return normalized


def make_scenario_builder_node(
    event_store: EventStore,
    structured_llm: StructuredLLM,
    snapshot_reader: SnapshotReader,
) -> Any:
    """Create the scenario builder node for the simulation graph.

    The scenario builder node resolves target districts, selects shocks, builds
    a participant roster, and emits a scenario-built event.

    Args:
        event_store: Event store used to publish scenario construction events.
        structured_llm: Structured LLM transport used for scenario selection.
        snapshot_reader: Snapshot reader used to obtain coverage constraints.

    Returns:
        A LangGraph-compatible node function.
    """

    def node(state: SimulationGraphState) -> dict[str, Any]:
        intake_plan_raw = state.get("intake_plan")
        if intake_plan_raw is None:
            raise ValueError("intake_plan is required before scenario_builder")

        snapshot = state.get("snapshot")
        if snapshot is None:
            raise ValueError("snapshot is required before scenario_builder")

        intake_plan = IntakePlan.model_validate(intake_plan_raw)
        coverage = snapshot_reader.get_coverage(snapshot)

        target_gus, warnings = resolve_gu_codes(intake_plan.geography_hint, coverage.available_gu_codes)

        target_period_start = _month_start_after(coverage.max_period)
        target_period_end = _add_months(target_period_start, intake_plan.horizon_months - 1)
        start_period = target_period_start.strftime("%Y-%m")
        end_period = target_period_end.strftime("%Y-%m")

        messages: list[LLMMessage] = [
            {"role": "system", "content": _build_system_prompt(intake_plan)},
            {
                "role": "user",
                "content": (
                    f"objective={intake_plan.objective}\n"
                    f"analysis_mode={intake_plan.analysis_mode}\n"
                    f"requested_shocks={intake_plan.requested_shocks}\n"
                    f"participant_focus={intake_plan.participant_focus}"
                ),
            },
        ]

        llm_selection = structured_llm.generate_structured(
            messages=messages,
            response_model=ScenarioSelection,
            temperature=0.0,
        )

        selected_shocks = _normalize_selected_shocks(llm_selection.selected_shock_keys)
        if intake_plan.analysis_mode == "stress" and not selected_shocks:
            selected_shocks = ["sentiment_drop"]
            warnings.append("Stress mode requires at least one shock; defaulted to sentiment_drop.")
        if intake_plan.analysis_mode == "compare":
            warnings.append("Compare mode currently builds one scenario from combined assumptions.")

        shocks = [expand_shock(key, target_gus, start_period, end_period) for key in selected_shocks]

        scenario = ScenarioSpec(
            scenario_name=llm_selection.scenario_name.strip() or "Scenario",
            target_gus=target_gus,
            target_period_start=target_period_start,
            target_period_end=target_period_end,
            shocks=shocks,
        )

        raw_buckets: list[Any]
        try:
            raw_buckets = llm_selection.model_dump()["roster_buckets"]
            if not isinstance(raw_buckets, list):
                raw_buckets = []
        except (ValidationError, KeyError, TypeError):
            raw_buckets = []

        roster_buckets = _sanitize_roster_buckets(raw_buckets)
        roster = ParticipantRosterSpec(seed=snapshot.dataset_snapshot_id[:12], buckets=roster_buckets)

        max_rounds = compute_max_rounds(intake_plan.horizon_months, len(shocks), intake_plan.analysis_mode)

        run_meta = state.get("run_meta")
        if run_meta is None:
            raise ValueError("run_meta is required before emitting simulation events")

        event_id = str(uuid4())
        event_store.append(
            SimulationEvent(
                event_id=event_id,
                run_id=run_meta.run_id,
                round_no=0,
                event_type="SCENARIO_BUILT",
                timestamp=datetime.now(timezone.utc),
                payload={
                    "scenario": scenario.model_dump(),
                    "participant_roster": roster.model_dump(),
                    "max_rounds": max_rounds,
                    "warnings": warnings,
                },
            )
        )

        return {
            "scenario": scenario,
            "participant_roster": roster.model_dump(),
            "max_rounds": max_rounds,
            "warnings": warnings,
            "event_refs": [event_id],
        }

    return node
