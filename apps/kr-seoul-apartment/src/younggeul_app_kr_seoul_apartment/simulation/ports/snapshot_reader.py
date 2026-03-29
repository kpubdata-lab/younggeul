# pyright: reportMissingImports=false

"""Protocols for reading snapshot coverage, metrics, and forecasts."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict

from younggeul_core.state.gold import BaselineForecast, GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import SnapshotRef


class SnapshotCoverage(BaseModel):
    """Coverage metadata describing data available in a snapshot.

    Attributes:
        available_gu_codes: District codes available in the snapshot.
        available_gu_names: Mapping of district code to district name.
        min_period: Earliest available period in YYYY-MM format.
        max_period: Latest available period in YYYY-MM format.
        record_count: Number of source records represented.
    """

    model_config = ConfigDict(frozen=True)

    available_gu_codes: list[str]
    available_gu_names: dict[str, str]
    min_period: str
    max_period: str
    record_count: int


@runtime_checkable
class SnapshotReader(Protocol):
    """Interface for reading simulation input data from snapshots."""

    def get_coverage(self, snapshot: SnapshotRef) -> SnapshotCoverage:
        """Return available geography and period coverage for a snapshot.

        Args:
            snapshot: Snapshot reference to inspect.

        Returns:
            Snapshot coverage metadata.
        """

        ...

    def get_latest_metrics(
        self,
        snapshot: SnapshotRef,
        gu_codes: Sequence[str] | None = None,
    ) -> list[GoldDistrictMonthlyMetrics]:
        """Return latest district metrics for selected districts.

        Args:
            snapshot: Snapshot reference to read from.
            gu_codes: Optional district codes to filter by.

        Returns:
            Latest district metrics from the snapshot.
        """

        ...

    def get_baseline_forecasts(
        self,
        snapshot: SnapshotRef,
        gu_codes: Sequence[str] | None = None,
    ) -> list[BaselineForecast]:
        """Return baseline forecasts for selected districts.

        Args:
            snapshot: Snapshot reference to read from.
            gu_codes: Optional district codes to filter by.

        Returns:
            Baseline forecasts from the snapshot.
        """

        ...
