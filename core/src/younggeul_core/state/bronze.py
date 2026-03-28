from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BronzeIngestMeta(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    ingest_timestamp: datetime
    source_id: str
    raw_response_hash: str | None = None


class BronzeAptTransaction(BronzeIngestMeta):
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
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    date: str | None = None
    rate_type: str | None = None
    rate_value: str | None = None
    unit: str | None = None


class BronzeMigration(BronzeIngestMeta):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    year: str | None = None
    month: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    in_count: str | None = None
    out_count: str | None = None
    net_count: str | None = None


class BronzeLegalDistrictCode(BronzeIngestMeta):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    code: str | None = None
    name: str | None = None
    is_active: str | None = None


class BronzeIngestManifest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    manifest_id: str
    source_id: str
    api_endpoint: str
    request_params: dict[str, str]
    response_count: int
    ingested_at: datetime
    status: Literal["success", "partial", "failed"]
    error_message: str | None = None
