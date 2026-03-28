from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from younggeul_core.state import (
    BronzeAptTransaction,
    BronzeIngestManifest,
    BronzeIngestMeta,
    BronzeInterestRate,
    BronzeLegalDistrictCode,
    BronzeMigration,
)


def _ingest_timestamp() -> datetime:
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _apt_full_payload() -> dict[str, str | None | datetime]:
    return {
        "ingest_timestamp": _ingest_timestamp(),
        "source_id": "molit_apt_trade_v2",
        "raw_response_hash": "sha256:abc123",
        "deal_amount": "120,000",
        "build_year": "2016",
        "deal_year": "2025",
        "deal_month": "07",
        "deal_day": "15",
        "dong": "역삼동",
        "apt_name": "래미안",
        "floor": "12",
        "area_exclusive": "84.99",
        "jibun": "123-45",
        "regional_code": "11680",
        "apt_dong": "101동",
        "road_name": "테헤란로",
        "road_name_bonbun": "0123",
        "road_name_bubun": "0001",
        "road_name_code": "4100001",
        "road_name_seq": "01",
        "road_name_basement": "0",
        "bonbun": "0123",
        "bubun": "0001",
        "land_code": "680",
        "serial_number": "2025-001",
        "cancel_deal_type": "N",
        "cancel_deal_day": None,
        "req_gbn": "중개거래",
        "rdealer_lawdnm": "서울 강남구",
        "dealer_type": "중개거래",
        "buyer_gbn": "개인",
        "seller_gbn": "개인",
        "registration_date": "20250720",
        "sgg_code": "680",
        "umd_code": "10300",
    }


def test_bronze_apt_transaction_round_trip_all_fields_populated() -> None:
    model = BronzeAptTransaction(**_apt_full_payload())
    dumped = model.model_dump()
    restored = BronzeAptTransaction.model_validate(dumped)
    assert restored == model
    assert restored.deal_amount == "120,000"
    assert restored.road_name == "테헤란로"


def test_bronze_apt_transaction_all_nullable_fields_none() -> None:
    model = BronzeAptTransaction(
        ingest_timestamp=_ingest_timestamp(),
        source_id="molit_apt_trade_v2",
    )
    assert model.raw_response_hash is None
    assert model.deal_amount is None
    assert model.umd_code is None


def test_bronze_interest_rate_round_trip() -> None:
    model = BronzeInterestRate(
        ingest_timestamp=_ingest_timestamp(),
        source_id="bank_of_korea_base_rate",
        raw_response_hash="sha256:rate-1",
        date="2026-01-01",
        rate_type="base_rate",
        rate_value="3.50",
        unit="percent",
    )
    restored = BronzeInterestRate.model_validate(model.model_dump())
    assert restored == model


def test_bronze_migration_round_trip() -> None:
    model = BronzeMigration(
        ingest_timestamp=_ingest_timestamp(),
        source_id="kosis_migration_monthly",
        raw_response_hash="sha256:migration-1",
        year="2026",
        month="01",
        region_code="11680",
        region_name="강남구",
        in_count="4520",
        out_count="3980",
        net_count="540",
    )
    restored = BronzeMigration.model_validate(model.model_dump())
    assert restored == model


def test_bronze_legal_district_code_round_trip() -> None:
    model = BronzeLegalDistrictCode(
        ingest_timestamp=_ingest_timestamp(),
        source_id="molit_legal_district_code",
        raw_response_hash="sha256:district-1",
        code="1168010100",
        name="서울특별시 강남구 역삼동",
        is_active="존재",
    )
    restored = BronzeLegalDistrictCode.model_validate(model.model_dump())
    assert restored == model


@pytest.mark.parametrize("status", ["success", "partial", "failed"])
def test_bronze_ingest_manifest_valid_statuses(status: str) -> None:
    model = BronzeIngestManifest(
        manifest_id="6cbf8dea-f539-4c65-b429-b6b72e95d4a0",
        source_id="molit_apt_trade_v2",
        api_endpoint="https://api.example.com/molit/trades",
        request_params={"LAWD_CD": "11680", "DEAL_YMD": "202601"},
        response_count=25,
        ingested_at=_ingest_timestamp(),
        status=status,
    )
    assert model.status == status


def test_bronze_ingest_manifest_invalid_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        BronzeIngestManifest(
            manifest_id="6cbf8dea-f539-4c65-b429-b6b72e95d4a0",
            source_id="molit_apt_trade_v2",
            api_endpoint="https://api.example.com/molit/trades",
            request_params={"LAWD_CD": "11680", "DEAL_YMD": "202601"},
            response_count=25,
            ingested_at=_ingest_timestamp(),
            status="done",
        )
    message = str(exc_info.value)
    assert "status" in message
    assert "success" in message


def test_validation_error_message_for_bad_datetime_input() -> None:
    with pytest.raises(ValidationError) as exc_info:
        BronzeAptTransaction(
            ingest_timestamp="not-a-datetime",
            source_id="molit_apt_trade_v2",
        )
    message = str(exc_info.value)
    assert "ingest_timestamp" in message
    assert "valid datetime" in message


def test_validation_error_message_for_missing_required_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        BronzeIngestMeta(ingest_timestamp=_ingest_timestamp())
    message = str(exc_info.value)
    assert "source_id" in message
    assert "Field required" in message


@pytest.mark.parametrize(
    ("model_cls", "payload"),
    [
        (
            BronzeIngestMeta,
            {
                "ingest_timestamp": _ingest_timestamp(),
                "source_id": "molit_apt_trade_v2",
                "raw_response_hash": "sha256:meta",
            },
        ),
        (BronzeAptTransaction, _apt_full_payload()),
        (
            BronzeInterestRate,
            {
                "ingest_timestamp": _ingest_timestamp(),
                "source_id": "bank_of_korea_base_rate",
                "raw_response_hash": "sha256:rate-1",
                "date": "2026-01-01",
                "rate_type": "base_rate",
                "rate_value": "3.50",
                "unit": "percent",
            },
        ),
        (
            BronzeMigration,
            {
                "ingest_timestamp": _ingest_timestamp(),
                "source_id": "kosis_migration_monthly",
                "raw_response_hash": "sha256:migration-1",
                "year": "2026",
                "month": "01",
                "region_code": "11680",
                "region_name": "강남구",
                "in_count": "4520",
                "out_count": "3980",
                "net_count": "540",
            },
        ),
        (
            BronzeLegalDistrictCode,
            {
                "ingest_timestamp": _ingest_timestamp(),
                "source_id": "molit_legal_district_code",
                "raw_response_hash": "sha256:district-1",
                "code": "1168010100",
                "name": "서울특별시 강남구 역삼동",
                "is_active": "존재",
            },
        ),
        (
            BronzeIngestManifest,
            {
                "manifest_id": "6cbf8dea-f539-4c65-b429-b6b72e95d4a0",
                "source_id": "molit_apt_trade_v2",
                "api_endpoint": "https://api.example.com/molit/trades",
                "request_params": {"LAWD_CD": "11680", "DEAL_YMD": "202601"},
                "response_count": 25,
                "ingested_at": _ingest_timestamp(),
                "status": "success",
                "error_message": None,
            },
        ),
    ],
)
def test_json_serialization_round_trip_for_all_models(model_cls: type, payload: dict[str, object]) -> None:
    model = model_cls(**payload)
    json_data = model.model_dump_json()
    restored = model_cls.model_validate_json(json_data)
    assert restored == model
