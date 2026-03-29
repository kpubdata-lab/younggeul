from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from younggeul_app_kr_seoul_apartment.forecaster import forecast_baseline
from younggeul_app_kr_seoul_apartment.pipeline import BronzeInput, PipelineResult, run_pipeline
from younggeul_app_kr_seoul_apartment.simulation.events import EventStore
from younggeul_app_kr_seoul_apartment.simulation.graph import build_simulation_graph
from younggeul_app_kr_seoul_apartment.simulation.graph_state import SimulationGraphState, seed_graph_state
from younggeul_app_kr_seoul_apartment.snapshot import publish_snapshot, resolve_snapshot
from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import SnapshotRef
from younggeul_core.storage.snapshot import SnapshotManifest


def run_pipeline_service(bronze: BronzeInput) -> PipelineResult:
    return run_pipeline(bronze)


def publish_snapshot_service(gold_rows: list[GoldDistrictMonthlyMetrics], base_dir: Path) -> SnapshotRef:
    return publish_snapshot(gold_rows, base_dir)


def resolve_snapshot_service(
    snapshot_id: str, base_dir: Path
) -> tuple[SnapshotManifest, list[GoldDistrictMonthlyMetrics]]:
    return resolve_snapshot(snapshot_id, base_dir)


def forecast_baseline_service(metrics: list[GoldDistrictMonthlyMetrics]) -> list[BaselineForecast]:
    return forecast_baseline(metrics)


def build_simulation_graph_service(event_store: EventStore) -> CompiledStateGraph[Any, Any, Any, Any]:
    return build_simulation_graph(event_store)


def seed_graph_state_service(user_query: str, run_id: str, run_name: str, model_id: str) -> SimulationGraphState:
    return seed_graph_state(user_query, run_id=run_id, run_name=run_name, model_id=model_id)
