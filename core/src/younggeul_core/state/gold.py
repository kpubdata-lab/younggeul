"""Gold-layer schemas for aggregated district and complex metrics."""

from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GoldDistrictMonthlyMetrics(BaseModel):
    """Represent monthly district-level aggregate housing metrics.

    Attributes:
        gu_code: District code.
        gu_name: District name.
        period: Target year-month period.
        sale_count: Number of sales in the period.
        avg_price: Average transaction price.
        median_price: Median transaction price.
        min_price: Minimum transaction price.
        max_price: Maximum transaction price.
        price_per_pyeong_avg: Average price per pyeong.
        yoy_price_change: Year-over-year price change ratio.
        mom_price_change: Month-over-month price change ratio.
        yoy_volume_change: Year-over-year sales volume change ratio.
        mom_volume_change: Month-over-month sales volume change ratio.
        avg_area_m2: Average exclusive area in square meters.
        base_interest_rate: Base interest rate for the period.
        net_migration: Net migration count for the district.
        dataset_snapshot_id: Optional source snapshot identifier.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    gu_code: str
    gu_name: str
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    sale_count: int
    avg_price: int
    median_price: int
    min_price: int
    max_price: int
    price_per_pyeong_avg: int
    yoy_price_change: float | None = None
    mom_price_change: float | None = None
    yoy_volume_change: float | None = None
    mom_volume_change: float | None = None
    avg_area_m2: Decimal | None = None
    base_interest_rate: Decimal | None = Field(default=None, decimal_places=2)
    net_migration: int | None = None
    dataset_snapshot_id: str | None = None


class GoldComplexMonthlyMetrics(BaseModel):
    """Represent monthly aggregate transaction metrics per apartment complex.

    Attributes:
        complex_id: Unique complex identifier.
        gu_code: District code where the complex is located.
        period: Target year-month period.
        sale_count: Number of complex-level sales in the period.
        avg_price: Average transaction price.
        median_price: Median transaction price.
        min_price: Minimum transaction price.
        max_price: Maximum transaction price.
        price_per_pyeong_avg: Average price per pyeong.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    complex_id: str
    gu_code: str
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    sale_count: int
    avg_price: int
    median_price: int
    min_price: int
    max_price: int
    price_per_pyeong_avg: int


class BaselineForecast(BaseModel):
    """Represent baseline directional forecasts for district housing markets.

    Attributes:
        gu_code: District code.
        gu_name: District name.
        target_period: Forecast target year-month period.
        direction: Predicted direction of price movement.
        direction_confidence: Confidence score for the direction prediction.
        predicted_volume: Optional predicted transaction volume.
        predicted_median_price: Optional predicted median transaction price.
        model_name: Name of the model producing the forecast.
        features_used: Feature names used by the model.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    gu_code: str
    gu_name: str
    target_period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    direction: Literal["up", "down", "flat"]
    direction_confidence: float
    predicted_volume: int | None = None
    predicted_median_price: int | None = None
    model_name: str
    features_used: list[str] = Field(default_factory=list)

    @field_validator("direction_confidence")
    @classmethod
    def validate_direction_confidence(cls, value: float) -> float:
        """Validate that direction_confidence is between 0.0 and 1.0.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if not 0.0 <= value <= 1.0:
            raise ValueError("direction_confidence must be between 0.0 and 1.0")
        return value
