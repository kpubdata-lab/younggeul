"""Silver-layer schemas for cleaned and typed intermediate datasets."""

from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SilverDataQualityScore(BaseModel):
    """Represent quality scoring dimensions for cleaned records.

    Attributes:
        completeness: Completeness score.
        consistency: Consistency score.
        overall: Overall quality score.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    completeness: float
    consistency: float
    overall: float

    @field_validator("completeness", "consistency", "overall")
    @classmethod
    def validate_score_range(cls, value: float) -> float:
        """Validate that quality scores are within 0.0 to 100.0.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if not 0.0 <= value <= 100.0:
            raise ValueError("score must be between 0.0 and 100.0")
        return value


class SilverAptTransaction(BaseModel):
    """Represent a normalized apartment transaction record.

    Attributes:
        transaction_id: Unique transaction identifier.
        deal_amount: Final transaction amount.
        deal_date: Transaction date.
        build_year: Building completion year.
        dong_code: Legal-dong code.
        dong_name: Legal-dong name.
        gu_code: District code.
        gu_name: District name.
        apt_name: Apartment complex name.
        floor: Floor number.
        area_exclusive_m2: Exclusive area in square meters.
        jibun: Optional lot-based address.
        road_name: Optional road-name address.
        is_cancelled: Whether the transaction was cancelled.
        cancel_date: Optional cancellation date.
        deal_type: Optional transaction type label.
        source_id: Source identifier for the ingestion feed.
        ingest_timestamp: Timestamp when data was ingested.
        quality_score: Optional quality assessment for the record.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    transaction_id: str
    deal_amount: int
    deal_date: date
    build_year: int
    dong_code: str
    dong_name: str
    gu_code: str
    gu_name: str
    apt_name: str
    floor: int
    area_exclusive_m2: Decimal = Field(decimal_places=2)
    jibun: str | None = None
    road_name: str | None = None
    is_cancelled: bool = False
    cancel_date: date | None = None
    deal_type: str | None = None
    source_id: str
    ingest_timestamp: datetime
    quality_score: SilverDataQualityScore | None = None


class SilverInterestRate(BaseModel):
    """Represent a normalized interest rate observation.

    Attributes:
        rate_date: Observation date.
        rate_type: Interest rate type label.
        rate_value: Interest rate value.
        source_id: Source identifier for the observation.
        ingest_timestamp: Timestamp when data was ingested.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    rate_date: date
    rate_type: str
    rate_value: Decimal = Field(decimal_places=2)
    source_id: str
    ingest_timestamp: datetime


class SilverMigration(BaseModel):
    """Represent normalized migration statistics for a period and region.

    Attributes:
        period: Target year-month period.
        region_code: Region code.
        region_name: Region name.
        in_count: Inbound migration count.
        out_count: Outbound migration count.
        net_count: Net migration count.
        source_id: Source identifier for the data.
        ingest_timestamp: Timestamp when data was ingested.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    region_code: str
    region_name: str
    in_count: int
    out_count: int
    net_count: int
    source_id: str
    ingest_timestamp: datetime


class SilverComplexBridge(BaseModel):
    """Map apartment complex identifiers to location reference fields.

    Attributes:
        complex_id: Complex identifier.
        dong_code: Legal-dong code.
        jibun: Optional lot-based address.
        road_name: Optional road-name address.
        apt_name: Apartment complex name.
        build_year: Optional building completion year.
        matched_at: Timestamp when the bridge record was matched.
        match_method: Strategy used to resolve the complex mapping.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    complex_id: str
    dong_code: str
    jibun: str | None = None
    road_name: str | None = None
    apt_name: str
    build_year: int | None = None
    matched_at: datetime
    match_method: Literal["exact_code", "jibun_match", "road_name_match"]
