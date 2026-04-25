from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from younggeul_app_kr_seoul_apartment.canonical import SEOUL_GU_CODES
from younggeul_app_kr_seoul_apartment.pipeline import BronzeInput, PipelineResult, run_pipeline
from younggeul_core.state.bronze import BronzeAptTransaction, BronzeInterestRate, BronzeMigration

_FIXED_NOW = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)


def _make_bronze_apt(**overrides: Any) -> BronzeAptTransaction:
    payload: dict[str, Any] = {
        "ingest_timestamp": _FIXED_NOW,
        "source_id": "molit.apartment.transactions",
        "raw_response_hash": "a" * 64,
        "deal_amount": "82,000",
        "build_year": "2016",
        "deal_year": "2025",
        "deal_month": "7",
        "deal_day": "15",
        "dong": "역삼동",
        "apt_name": "래미안",
        "floor": "12",
        "area_exclusive": "84.99",
        "jibun": "123-45",
        "road_name": "테헤란로",
        "serial_number": "2025-001",
        "sgg_code": "11680",
        "umd_code": "10300",
    }
    payload.update(overrides)
    return BronzeAptTransaction(**payload)


def _make_bronze_rate(**overrides: Any) -> BronzeInterestRate:
    payload: dict[str, Any] = {
        "ingest_timestamp": _FIXED_NOW,
        "source_id": "bank_of_korea_base_rate",
        "raw_response_hash": "b" * 64,
        "date": "2025-07-01",
        "rate_type": "base_rate",
        "rate_value": "3.50",
        "unit": "%",
    }
    payload.update(overrides)
    return BronzeInterestRate(**payload)


def _make_bronze_migration(**overrides: Any) -> BronzeMigration:
    payload: dict[str, Any] = {
        "ingest_timestamp": _FIXED_NOW,
        "source_id": "kostat_population_migration",
        "raw_response_hash": "c" * 64,
        "year": "2025",
        "month": "07",
        "region_code": "11",
        "region_name": "서울특별시",
        "in_count": "150000",
        "out_count": "140000",
        "net_count": "10000",
    }
    payload.update(overrides)
    return BronzeMigration(**payload)


def _make_full_bronze_input() -> BronzeInput:
    apt_transactions = [
        _make_bronze_apt(
            serial_number="2025-001",
            deal_amount="82,000",
            deal_month="7",
            deal_day="15",
            sgg_code="11680",
            apt_name="래미안",
        ),
        _make_bronze_apt(
            serial_number="2025-002",
            deal_amount="84,000",
            deal_month="7",
            deal_day="20",
            sgg_code="11680",
            apt_name="아이파크",
        ),
        _make_bronze_apt(
            serial_number="2025-003",
            deal_amount="90,000",
            deal_month="8",
            deal_day="10",
            sgg_code="11680",
            apt_name="푸르지오",
        ),
        _make_bronze_apt(
            serial_number="2025-004",
            deal_amount="70,000",
            deal_month="7",
            deal_day="12",
            sgg_code="11650",
            apt_name="서초힐스",
            dong="서초동",
            umd_code="10100",
        ),
        _make_bronze_apt(
            serial_number="2025-005",
            deal_amount="95,000",
            deal_month="8",
            deal_day="05",
            sgg_code="11650",
            apt_name="아크로",
            dong="반포동",
            umd_code="10200",
        ),
        _make_bronze_apt(
            serial_number="2025-006",
            deal_amount="110,000",
            deal_month="7",
            deal_day="25",
            sgg_code="11650",
            apt_name="취소건",
            cancel_deal_type="O",
            cancel_deal_day="20250726",
            dong="서초동",
            umd_code="10100",
        ),
        _make_bronze_apt(serial_number="2025-007", deal_amount="50,000", sgg_code="41135", apt_name="분당아파트"),
        _make_bronze_apt(serial_number="2025-008", deal_amount="60,000", sgg_code="26110", apt_name="부산아파트"),
        _make_bronze_apt(serial_number="2025-009", deal_amount="not-a-number", sgg_code="11680", apt_name="파싱실패"),
    ]

    interest_rates = [
        _make_bronze_rate(date="2025-07-01", rate_value="3.50"),
        _make_bronze_rate(date="2025-08-01", rate_value="3.25", raw_response_hash="d" * 64),
    ]

    migrations = [
        _make_bronze_migration(year="2025", month="07", net_count="10000"),
        _make_bronze_migration(year="2025", month="08", net_count="-5000", raw_response_hash="e" * 64),
    ]

    return BronzeInput(
        apt_transactions=apt_transactions,
        interest_rates=interest_rates,
        migrations=migrations,
    )


def _result_bytes(result: PipelineResult) -> bytes:
    parts: list[str] = ["silver.apt"]
    parts.extend(item.model_dump_json() for item in result.silver.apt_transactions)
    parts.append("silver.rates")
    parts.extend(item.model_dump_json() for item in result.silver.interest_rates)
    parts.append("silver.migrations")
    parts.extend(item.model_dump_json() for item in result.silver.migrations)
    parts.append("gold")
    parts.extend(item.model_dump_json() for item in result.gold)
    return "\n".join(parts).encode("utf-8")


class TestPipelineEndToEnd:
    def test_run_pipeline_full_bronze_to_silver_to_gold(self) -> None:
        bronze = _make_full_bronze_input()

        result = run_pipeline(bronze)

        assert len(result.silver.apt_transactions) == 6
        assert all(row.gu_code in {"11680", "11650"} for row in result.silver.apt_transactions)
        assert all(row.apt_name != "파싱실패" for row in result.silver.apt_transactions)

        assert len(result.silver.interest_rates) == 2
        assert [row.rate_date.strftime("%Y-%m") for row in result.silver.interest_rates] == ["2025-07", "2025-08"]
        assert [row.rate_value for row in result.silver.interest_rates] == [Decimal("3.50"), Decimal("3.25")]

        assert len(result.silver.migrations) == 2
        assert [row.period for row in result.silver.migrations] == ["2025-07", "2025-08"]
        assert [row.net_count for row in result.silver.migrations] == [10000, -5000]

        assert len(result.gold) == 4

        gold_by_key = {(row.gu_code, row.period): row for row in result.gold}
        assert set(gold_by_key) == {
            ("11680", "2025-07"),
            ("11680", "2025-08"),
            ("11650", "2025-07"),
            ("11650", "2025-08"),
        }

        gangnam_july = gold_by_key[("11680", "2025-07")]
        assert gangnam_july.sale_count == 2
        assert gangnam_july.avg_price == 830_000_000
        assert gangnam_july.base_interest_rate == Decimal("3.50")
        assert gangnam_july.net_migration == 10000

        seocho_july = gold_by_key[("11650", "2025-07")]
        assert seocho_july.sale_count == 1
        assert seocho_july.avg_price == 700_000_000

        seocho_aug = gold_by_key[("11650", "2025-08")]
        assert seocho_aug.sale_count == 1
        assert seocho_aug.avg_price == 950_000_000
        assert seocho_aug.base_interest_rate == Decimal("3.25")
        assert seocho_aug.net_migration == -5000

        first_run = run_pipeline(bronze)
        second_run = run_pipeline(bronze)
        assert first_run == second_run


class TestPipelineDeterminism:
    def test_run_pipeline_is_byte_for_byte_deterministic(self) -> None:
        bronze = _make_full_bronze_input()

        first = run_pipeline(bronze)
        second = run_pipeline(bronze)

        assert _result_bytes(first) == _result_bytes(second)


class TestPipelineEmptyInput:
    def test_empty_bronze_input_returns_empty_silver_and_gold(self) -> None:
        result = run_pipeline(
            BronzeInput(
                apt_transactions=[],
                interest_rates=[],
                migrations=[],
            )
        )

        assert result.silver.apt_transactions == []
        assert result.silver.interest_rates == []
        assert result.silver.migrations == []
        assert result.gold == []


class TestPipelineAllSeoulDistricts:
    def test_pipeline_emits_one_gold_row_per_seoul_gu(self) -> None:
        bronze = BronzeInput(
            apt_transactions=[
                _make_bronze_apt(serial_number=f"2025-{index:03d}", sgg_code=code)
                for index, code in enumerate(SEOUL_GU_CODES, start=1)
            ],
            interest_rates=[_make_bronze_rate()],
            migrations=[_make_bronze_migration()],
        )

        result = run_pipeline(bronze)

        assert len(result.gold) == len(SEOUL_GU_CODES)
        assert {row.gu_code for row in result.gold} == set(SEOUL_GU_CODES)
