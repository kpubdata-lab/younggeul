"""Live ingest pipeline: fetches one Seoul gu × one month from real APIs via kpubdata.

v0.1 scope (option C — see docs/adr/007):
- MOLIT apartment trades and BOK base rate are fetched live.
- KOSTAT population migration uses a contextual fixture row, because the kpubdata
  ``kosis.population_migration`` dataset only exposes ``T70``/``T80`` metrics
  while ``BronzeMigration`` requires per-region in/out/net counts. Wiring those
  requires either a different KOSIS table or a Bronze schema change, which is
  tracked separately.
"""

from __future__ import annotations

from datetime import datetime, timezone

from kpubdata import Client

from younggeul_core.connectors.rate_limit import RateLimiter
from younggeul_core.state.bronze import BronzeMigration

from younggeul_app_kr_seoul_apartment.connectors.bok import (
    BokInterestRateConnector,
    BokInterestRateRequest,
)
from younggeul_app_kr_seoul_apartment.connectors.molit import (
    MolitAptConnector,
    MolitAptRequest,
)
from younggeul_app_kr_seoul_apartment.pipeline import BronzeInput

_BOK_BASE_RATE_STAT_CODE = "722Y001"
_BOK_BASE_RATE_ITEM_CODE = "0101000"
_BOK_BASE_RATE_FREQUENCY = "M"
_BOK_BASE_RATE_SOURCE_ID = "bank_of_korea_base_rate"
_BOK_BASE_RATE_TYPE = "base_rate"

_DEFAULT_RATE_LIMIT_INTERVAL = 1.0

_MIGRATION_FIXTURE_HASH = "0" * 64
_MIGRATION_FIXTURE_SOURCE_ID = "kostat_population_migration_fixture"
_SIDO_NAMES: dict[str, str] = {
    "11": "서울특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "29": "광주광역시",
    "30": "대전광역시",
    "31": "울산광역시",
    "36": "세종특별자치시",
    "41": "경기도",
}


def _validate_lawd_code(lawd_code: str) -> None:
    if len(lawd_code) != 5 or not lawd_code.isdigit():
        msg = f"lawd_code must be 5 digits, got {lawd_code!r}"
        raise ValueError(msg)


def _validate_deal_ym(deal_ym: str) -> None:
    if len(deal_ym) != 6 or not deal_ym.isdigit():
        msg = f"deal_ym must be YYYYMM (6 digits), got {deal_ym!r}"
        raise ValueError(msg)


def _sido_from_lawd(lawd_code: str) -> str:
    return lawd_code[:2]


def _build_migration_fixture(
    *,
    lawd_code: str,
    deal_ym: str,
    now: datetime,
) -> list[BronzeMigration]:
    sido_code = _sido_from_lawd(lawd_code)
    return [
        BronzeMigration(
            ingest_timestamp=now,
            source_id=_MIGRATION_FIXTURE_SOURCE_ID,
            raw_response_hash=_MIGRATION_FIXTURE_HASH,
            year=deal_ym[:4],
            month=deal_ym[4:6],
            region_code=sido_code,
            region_name=_SIDO_NAMES.get(sido_code, sido_code),
            in_count=None,
            out_count=None,
            net_count=None,
        )
    ]


def run_live_ingest(
    *,
    client: Client,
    lawd_code: str,
    deal_ym: str,
    rate_limit_interval: float = _DEFAULT_RATE_LIMIT_INTERVAL,
) -> BronzeInput:
    """Fetch MOLIT and BOK data for one gu × one month and return a BronzeInput.

    KOSTAT migrations are emitted as a single contextual fixture row (see module
    docstring).

    Args:
        client: Authenticated kpubdata client (built via ``client_factory.build_client``).
        lawd_code: 5-digit MOLIT sigungu code (e.g. ``"11680"`` for Gangnam-gu).
        deal_ym: Target month in ``YYYYMM`` format (e.g. ``"202503"``).
        rate_limit_interval: Minimum seconds between consecutive API calls per
            connector. Defaults to 1.0 to stay well within data.go.kr quotas.

    Returns:
        ``BronzeInput`` populated with apt transactions, interest rates and a
        single placeholder migration row, ready for ``run_pipeline``.

    Raises:
        ValueError: If ``lawd_code`` or ``deal_ym`` are malformed.
    """
    _validate_lawd_code(lawd_code)
    _validate_deal_ym(deal_ym)

    limiter = RateLimiter(min_interval=rate_limit_interval)

    apt_dataset = client.dataset("datago.apt_trade")
    rate_dataset = client.dataset("bok.base_rate")

    apt_connector = MolitAptConnector(client=apt_dataset, rate_limiter=limiter)
    bok_connector = BokInterestRateConnector(client=rate_dataset, rate_limiter=limiter)

    apt_result = apt_connector.fetch(MolitAptRequest(sigungu_code=lawd_code, year_month=deal_ym))
    rate_result = bok_connector.fetch(
        BokInterestRateRequest(
            stat_code=_BOK_BASE_RATE_STAT_CODE,
            item_code1=_BOK_BASE_RATE_ITEM_CODE,
            frequency=_BOK_BASE_RATE_FREQUENCY,
            start_date=deal_ym,
            end_date=deal_ym,
            rate_type=_BOK_BASE_RATE_TYPE,
            source_id=_BOK_BASE_RATE_SOURCE_ID,
        )
    )

    migrations = _build_migration_fixture(
        lawd_code=lawd_code,
        deal_ym=deal_ym,
        now=datetime.now(tz=timezone.utc),
    )

    return BronzeInput(
        apt_transactions=apt_result.records,
        interest_rates=rate_result.records,
        migrations=migrations,
    )


__all__ = ["run_live_ingest"]
