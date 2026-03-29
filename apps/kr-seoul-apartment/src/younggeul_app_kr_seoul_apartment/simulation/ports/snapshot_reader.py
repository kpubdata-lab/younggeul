from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict

from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import SnapshotRef


class SnapshotCoverage(BaseModel):
    model_config = ConfigDict(frozen=True)

    available_gu_codes: list[str]
    available_gu_names: dict[str, str]
    min_period: str
    max_period: str
    record_count: int


@runtime_checkable
class SnapshotReader(Protocol):
    def get_coverage(self, snapshot: SnapshotRef) -> SnapshotCoverage: ...

    def get_latest_metrics(
        self,
        snapshot: SnapshotRef,
        gu_codes: Sequence[str] | None = None,
    ) -> list[GoldDistrictMonthlyMetrics]: ...

    def get_baseline_forecasts(
        self,
        snapshot: SnapshotRef,
        gu_codes: Sequence[str] | None = None,
    ) -> list[BaselineForecast]: ...
