"""Live ingest pipeline: fetches Seoul gu × month(s) from real APIs via kpubdata.

v0.1 scope (option C — see docs/adr/007):
- MOLIT apartment trades and BOK base rate are fetched live.
- KOSTAT population migration is **not emitted** in live mode. The kpubdata
  ``kosis.population_migration`` dataset only exposes ``T70``/``T80`` aggregate
  metrics while ``BronzeMigration`` requires per-region in/out/net counts;
  wiring those requires either a different KOSIS table or a Bronze schema
  change, which is tracked separately.
"""

from __future__ import annotations

from kpubdata import Client

from younggeul_core.connectors.rate_limit import RateLimiter

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


def _validate_lawd_code(lawd_code: str) -> None:
    if len(lawd_code) != 5 or not lawd_code.isdigit():
        msg = f"lawd_code must be 5 digits, got {lawd_code!r}"
        raise ValueError(msg)


def _validate_deal_ym(deal_ym: str) -> None:
    if len(deal_ym) != 6 or not deal_ym.isdigit():
        msg = f"deal_ym must be YYYYMM (6 digits), got {deal_ym!r}"
        raise ValueError(msg)


def run_live_ingest(
    *,
    client: Client,
    lawd_code: str,
    deal_ym: str,
    rate_limit_interval: float = _DEFAULT_RATE_LIMIT_INTERVAL,
) -> BronzeInput:
    """Fetch MOLIT and BOK data for one gu × one month and return a BronzeInput.

    Thin wrapper over :func:`run_live_ingest_months` for the single-month case.
    See that function for full semantics.
    """
    return run_live_ingest_months(
        client=client,
        lawd_code=lawd_code,
        deal_yms=[deal_ym],
        rate_limit_interval=rate_limit_interval,
    )


def run_live_ingest_months(
    *,
    client: Client,
    lawd_code: str,
    deal_yms: list[str],
    rate_limit_interval: float = _DEFAULT_RATE_LIMIT_INTERVAL,
) -> BronzeInput:
    """Fetch MOLIT and BOK data for one gu × N months and return a BronzeInput.

    MOLIT is queried once per month (the API does not accept a range); BOK is
    queried with ``start_date=min(deal_yms)`` and ``end_date=max(deal_yms)``
    so a single request covers the whole window. KOSTAT migrations are omitted
    in live mode (see module docstring).

    Args:
        client: Authenticated kpubdata client (built via ``client_factory.build_client``).
        lawd_code: 5-digit MOLIT sigungu code (e.g. ``"11680"`` for Gangnam-gu).
        deal_yms: One or more target months in ``YYYYMM`` format. Order is
            preserved in the output. Duplicates are rejected.
        rate_limit_interval: Minimum seconds between consecutive API calls per
            connector. Defaults to 1.0 to stay well within data.go.kr quotas.

    Returns:
        ``BronzeInput`` populated with apt transactions across all requested
        months and interest rates spanning the full window, ready for
        ``run_pipeline``. With multiple months, downstream Gold output will
        include YoY/MoM change ratios where comparison anchors are available.

    Raises:
        ValueError: If ``lawd_code`` or any ``deal_ym`` is malformed, if
            ``deal_yms`` is empty, or if it contains duplicates.
    """
    _validate_lawd_code(lawd_code)
    if not deal_yms:
        raise ValueError("deal_yms must not be empty")
    if len(set(deal_yms)) != len(deal_yms):
        raise ValueError(f"deal_yms must not contain duplicates, got {deal_yms!r}")
    for ym in deal_yms:
        _validate_deal_ym(ym)

    limiter = RateLimiter(min_interval=rate_limit_interval)

    apt_dataset = client.dataset("datago.apt_trade")
    rate_dataset = client.dataset("bok.base_rate")

    apt_connector = MolitAptConnector(client=apt_dataset, rate_limiter=limiter)
    bok_connector = BokInterestRateConnector(client=rate_dataset, rate_limiter=limiter)

    apt_records = []
    for ym in deal_yms:
        apt_result = apt_connector.fetch(MolitAptRequest(sigungu_code=lawd_code, year_month=ym))
        apt_records.extend(apt_result.records)

    rate_result = bok_connector.fetch(
        BokInterestRateRequest(
            stat_code=_BOK_BASE_RATE_STAT_CODE,
            item_code1=_BOK_BASE_RATE_ITEM_CODE,
            frequency=_BOK_BASE_RATE_FREQUENCY,
            start_date=min(deal_yms),
            end_date=max(deal_yms),
            rate_type=_BOK_BASE_RATE_TYPE,
            source_id=_BOK_BASE_RATE_SOURCE_ID,
        )
    )

    return BronzeInput(
        apt_transactions=apt_records,
        interest_rates=rate_result.records,
        migrations=[],
    )


__all__ = ["run_live_ingest", "run_live_ingest_months"]
