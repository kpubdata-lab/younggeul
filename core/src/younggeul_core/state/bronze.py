"""Bronze-layer schemas for raw ingested housing-related source data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BronzeIngestMeta(BaseModel):
    """Capture shared metadata for bronze ingestion records.

    Attributes:
        ingest_timestamp: Timestamp when the record was ingested.
        source_id: Identifier of the ingestion source.
        raw_response_hash: Optional hash of the raw upstream response.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    ingest_timestamp: datetime
    source_id: str
    raw_response_hash: str | None = None


class BronzeAptTransaction(BronzeIngestMeta):
    """Represent a raw apartment transaction payload from source systems.

    Attributes:
        deal_amount: Raw deal amount string value.
        build_year: Raw building completion year.
        deal_year: Raw deal year value.
        deal_month: Raw deal month value.
        deal_day: Raw deal day value.
        dong: Raw legal-dong name.
        apt_name: Raw apartment complex name.
        floor: Raw floor value.
        area_exclusive: Raw exclusive area value.
        jibun: Raw lot-based address.
        regional_code: Raw regional code.
        apt_dong: Raw apartment building-dong descriptor.
        road_name: Raw road-name address text.
        road_name_bonbun: Raw road-name main number.
        road_name_bubun: Raw road-name sub number.
        road_name_code: Raw road-name code.
        road_name_seq: Raw road-name sequence value.
        road_name_basement: Raw basement flag.
        bonbun: Raw lot main number.
        bubun: Raw lot sub number.
        land_code: Raw land category code.
        serial_number: Raw source serial number.
        cancel_deal_type: Raw cancellation type flag.
        cancel_deal_day: Raw cancellation date string.
        req_gbn: Raw request category code.
        rdealer_lawdnm: Raw registered dealer legal-dong name.
        dealer_type: Raw dealer type value.
        buyer_gbn: Raw buyer category value.
        seller_gbn: Raw seller category value.
        registration_date: Raw registration date string.
        sgg_code: Raw sigungu code.
        umd_code: Raw eupmyeondong code.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    deal_amount: str | None = None
    build_year: str | None = None
    deal_year: str | None = None
    deal_month: str | None = None
    deal_day: str | None = None
    dong: str | None = None
    apt_name: str | None = None
    floor: str | None = None
    area_exclusive: str | None = None
    jibun: str | None = None
    regional_code: str | None = None
    apt_dong: str | None = None
    road_name: str | None = None
    road_name_bonbun: str | None = None
    road_name_bubun: str | None = None
    road_name_code: str | None = None
    road_name_seq: str | None = None
    road_name_basement: str | None = None
    bonbun: str | None = None
    bubun: str | None = None
    land_code: str | None = None
    serial_number: str | None = None
    cancel_deal_type: str | None = None
    cancel_deal_day: str | None = None
    req_gbn: str | None = None
    rdealer_lawdnm: str | None = None
    dealer_type: str | None = None
    buyer_gbn: str | None = None
    seller_gbn: str | None = None
    registration_date: str | None = None
    sgg_code: str | None = None
    umd_code: str | None = None


class BronzeInterestRate(BronzeIngestMeta):
    """Represent a raw interest rate observation from ingest sources.

    Attributes:
        date: Raw date string for the rate observation.
        rate_type: Raw rate type label.
        rate_value: Raw rate value string.
        unit: Raw unit text for the rate value.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    date: str | None = None
    rate_type: str | None = None
    rate_value: str | None = None
    unit: str | None = None


class BronzeMigration(BronzeIngestMeta):
    """Represent a raw migration record from a source feed.

    Attributes:
        year: Raw year value.
        month: Raw month value.
        region_code: Raw region code.
        region_name: Raw region name.
        in_count: Raw inbound migration count.
        out_count: Raw outbound migration count.
        net_count: Raw net migration count.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    year: str | None = None
    month: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    in_count: str | None = None
    out_count: str | None = None
    net_count: str | None = None


class BronzeLegalDistrictCode(BronzeIngestMeta):
    """Represent a raw legal district code row from source data.

    Attributes:
        code: Raw district code.
        name: Raw district name.
        is_active: Raw active-status flag.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    code: str | None = None
    name: str | None = None
    is_active: str | None = None


class BronzeIngestManifest(BaseModel):
    """Summarize metadata for a single bronze ingestion batch.

    Attributes:
        manifest_id: Unique identifier for the manifest record.
        source_id: Identifier of the ingested source.
        api_endpoint: Endpoint used for ingestion.
        request_params: Request parameters used for the ingestion call.
        response_count: Number of records returned by the source.
        ingested_at: Timestamp when ingestion completed.
        status: Final ingestion status.
        error_message: Optional ingestion error details.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    manifest_id: str
    source_id: str
    api_endpoint: str
    request_params: dict[str, str]
    response_count: int
    ingested_at: datetime
    status: Literal["success", "partial", "failed"]
    error_message: str | None = None
