"""MOLIT apartment transaction connector using PublicDataReader."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar

import pandas as pd
from PublicDataReader import TransactionPrice

from younggeul_core.connectors.hashing import sha256_payload
from younggeul_core.connectors.manifest import build_manifest
from younggeul_core.connectors.protocol import ConnectorResult
from younggeul_core.connectors.rate_limit import RateLimiter
from younggeul_core.connectors.retry import NonRetryableError, retry
from younggeul_core.state.bronze import BronzeAptTransaction

# ---------------------------------------------------------------------------
# Column mapping: PublicDataReader Korean column → BronzeAptTransaction field
# ---------------------------------------------------------------------------
# PublicDataReader returns columns in Korean when translate=True (default).
# Some column names differ from the raw MOLIT API names.
# ---------------------------------------------------------------------------

COLUMN_MAP: dict[str, str] = {
    "거래금액": "deal_amount",
    "건축년도": "build_year",
    "년": "deal_year",
    "월": "deal_month",
    "일": "deal_day",
    "법정동": "dong",
    "아파트": "apt_name",
    "층": "floor",
    "전용면적": "area_exclusive",
    "지번": "jibun",
    "법정동시군구코드": "regional_code",
    "아파트동": "apt_dong",
    "도로명": "road_name",
    "도로명건물본번호코드": "road_name_bonbun",
    "도로명건물부번호코드": "road_name_bubun",
    "도로명코드": "road_name_code",
    "도로명일련번호코드": "road_name_seq",
    "도로명지상지하코드": "road_name_basement",
    "본번": "bonbun",
    "부번": "bubun",
    "지역코드": "land_code",
    "일련번호": "serial_number",
    "해제여부": "cancel_deal_type",
    "해제사유발생일": "cancel_deal_day",
    "거래유형": "req_gbn",
    "중개사소재지": "rdealer_lawdnm",
    "매수자": "buyer_gbn",
    "매도자": "seller_gbn",
    "등기일자": "registration_date",
    "시군구코드": "sgg_code",
    "읍면동코드": "umd_code",
}

# Fields that are numeric in pandas but should be clean integer strings
# (e.g., 2023.0 → "2023", 11650.0 → "11650")
_INT_LIKE_FIELDS: frozenset[str] = frozenset(
    {
        "건축년도",
        "년",
        "월",
        "일",
        "층",
        "법정동시군구코드",
        "도로명건물본번호코드",
        "도로명건물부번호코드",
        "도로명코드",
        "도로명일련번호코드",
        "도로명지상지하코드",
        "본번",
        "부번",
        "지역코드",
        "시군구코드",
        "읍면동코드",
    }
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class MolitAptRequest:
    """Partition-scoped request for one sigungu + one month."""

    sigungu_code: str
    year_month: str


def _safe_str(value: object, *, int_like: bool = False) -> str | None:
    """Convert a pandas cell value to str | None.

    - NaN / None → None
    - float that represents an integer (e.g. 2023.0) → "2023" when int_like=True
    - everything else → str(value)
    """
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or pd.isna(value)):
        return None
    if int_like and isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _normalize_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame rows to dicts with NaN→None and int-like float fix.

    Returns raw dicts with Korean column names (not yet mapped to Bronze fields).
    """
    rows: list[dict[str, Any]] = []
    for _, series in df.iterrows():
        row: dict[str, Any] = {}
        for col in df.columns:
            row[col] = _safe_str(series[col], int_like=col in _INT_LIKE_FIELDS)
        rows.append(row)
    return rows


def _map_to_bronze(
    raw_rows: list[dict[str, Any]],
    *,
    source_id: str,
    ingest_timestamp: datetime,
    raw_response_hash: str,
) -> list[BronzeAptTransaction]:
    """Map normalized raw dicts (Korean keys) to BronzeAptTransaction records."""
    records: list[BronzeAptTransaction] = []
    for raw in raw_rows:
        mapped: dict[str, Any] = {
            "ingest_timestamp": ingest_timestamp,
            "source_id": source_id,
            "raw_response_hash": raw_response_hash,
        }
        for korean_col, bronze_field in COLUMN_MAP.items():
            mapped[bronze_field] = raw.get(korean_col)

        # 법정동시군구코드 maps to both regional_code and sgg_code
        sgg_value = raw.get("법정동시군구코드")
        if sgg_value is not None:
            mapped["sgg_code"] = sgg_value

        records.append(BronzeAptTransaction(**mapped))
    return records


class MolitAptConnector:
    """Connector for MOLIT apartment transaction data via PublicDataReader.

    Satisfies ``Connector[MolitAptRequest, BronzeAptTransaction]`` protocol.
    """

    source_id: ClassVar[str] = "molit.apartment.transactions"

    def __init__(
        self,
        client: TransactionPrice,
        rate_limiter: RateLimiter,
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._now_fn = now_fn

    def fetch(self, request: MolitAptRequest) -> ConnectorResult[BronzeAptTransaction]:
        """Fetch apartment transactions for one sigungu + one month."""
        now = self._now_fn()

        # Retry wraps only the API call; rate limit inside retried callable
        def _call_api() -> pd.DataFrame:
            self._rate_limiter.wait()
            result: pd.DataFrame = self._client.get_data(
                property_type="아파트",
                trade_type="매매",
                sigungu_code=request.sigungu_code,
                year_month=request.year_month,
            )
            return result

        try:
            raw_df = retry(_call_api)
        except Exception as exc:
            # Build a failed manifest and re-raise
            manifest = build_manifest(
                source_id=self.source_id,
                api_endpoint="getRTMSDataSvcAptTradeDev",
                request_params={
                    "sigungu_code": request.sigungu_code,
                    "year_month": request.year_month,
                },
                response_count=0,
                ingested_at=now,
                status="failed",
                error_message=str(exc),
            )
            return ConnectorResult(records=[], manifest=manifest)

        # Handle empty response
        if raw_df is None or raw_df.empty:
            manifest = build_manifest(
                source_id=self.source_id,
                api_endpoint="getRTMSDataSvcAptTradeDev",
                request_params={
                    "sigungu_code": request.sigungu_code,
                    "year_month": request.year_month,
                },
                response_count=0,
                ingested_at=now,
                status="success",
            )
            return ConnectorResult(records=[], manifest=manifest)

        # Validate expected columns exist
        missing = set(COLUMN_MAP.keys()) - set(raw_df.columns)
        if missing:
            msg = f"Missing expected columns in MOLIT response: {sorted(missing)}"
            raise NonRetryableError(msg)

        # Stage 1: Normalize (NaN → None, float fix)
        raw_rows = _normalize_dataframe(raw_df)

        # Compute hash from normalized raw dicts (before Bronze mapping)
        response_hash = sha256_payload(raw_rows)

        # Stage 2: Map to Bronze records
        records = _map_to_bronze(
            raw_rows,
            source_id=self.source_id,
            ingest_timestamp=now,
            raw_response_hash=response_hash,
        )

        manifest = build_manifest(
            source_id=self.source_id,
            api_endpoint="getRTMSDataSvcAptTradeDev",
            request_params={
                "sigungu_code": request.sigungu_code,
                "year_month": request.year_month,
            },
            response_count=len(records),
            ingested_at=now,
            status="success",
        )

        return ConnectorResult(records=records, manifest=manifest)
