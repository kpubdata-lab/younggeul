"""Unit tests for MolitAptConnector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from younggeul_app_kr_seoul_apartment.connectors.molit import (
    MolitAptConnector,
    MolitAptRequest,
    _normalize_dataframe,
    _safe_str,
)
from younggeul_core.connectors.protocol import Connector, ConnectorResult
from younggeul_core.connectors.rate_limit import RateLimiter
from younggeul_core.connectors.retry import ConnectorError
from younggeul_core.state.bronze import BronzeAptTransaction

_FIXED_NOW = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_now() -> datetime:
    return _FIXED_NOW


def _make_rate_limiter() -> RateLimiter:
    return RateLimiter(min_interval=0.0)


def _sample_dataframe() -> pd.DataFrame:
    """Create a synthetic DataFrame matching PublicDataReader output."""
    data: dict[str, list[Any]] = {
        "거래금액": ["82,000"],
        "건축년도": [2016.0],
        "년": [2025.0],
        "월": [7.0],
        "일": [15.0],
        "법정동": ["역삼동"],
        "아파트": ["래미안"],
        "층": [12.0],
        "전용면적": [84.99],
        "지번": ["123-45"],
        "법정동시군구코드": [11680.0],
        "아파트동": ["101동"],
        "도로명": ["테헤란로"],
        "도로명건물본번호코드": [123.0],
        "도로명건물부번호코드": [1.0],
        "도로명코드": [4100001.0],
        "도로명일련번호코드": [1.0],
        "도로명지상지하코드": [0.0],
        "본번": [123.0],
        "부번": [1.0],
        "지역코드": [680.0],
        "일련번호": ["2025-001"],
        "해제여부": [np.nan],
        "해제사유발생일": [np.nan],
        "거래유형": ["중개거래"],
        "중개사소재지": ["서울 강남구"],
        "매수자": ["개인"],
        "매도자": ["개인"],
        "등기일자": ["20250720"],
        "시군구코드": [11680.0],
        "읍면동코드": [10300.0],
    }
    return pd.DataFrame(data)


class TestSafeStr:
    def test_none_returns_none(self) -> None:
        assert _safe_str(None) is None

    def test_nan_returns_none(self) -> None:
        assert _safe_str(float("nan")) is None

    def test_numpy_nan_returns_none(self) -> None:
        assert _safe_str(np.nan) is None

    def test_int_like_float_with_flag(self) -> None:
        assert _safe_str(2023.0, int_like=True) == "2023"

    def test_int_like_float_without_flag(self) -> None:
        assert _safe_str(2023.0, int_like=False) == "2023.0"

    def test_regular_float(self) -> None:
        assert _safe_str(84.99, int_like=False) == "84.99"

    def test_string_passthrough(self) -> None:
        assert _safe_str("역삼동") == "역삼동"


class TestNormalizeDataframe:
    def test_nan_converted_to_none(self) -> None:
        df = pd.DataFrame({"해제여부": [np.nan], "아파트": ["래미안"]})
        rows = _normalize_dataframe(df)
        assert rows[0]["해제여부"] is None
        assert rows[0]["아파트"] == "래미안"

    def test_int_like_floats_normalized(self) -> None:
        df = pd.DataFrame({"건축년도": [2016.0], "법정동시군구코드": [11680.0]})
        rows = _normalize_dataframe(df)
        assert rows[0]["건축년도"] == "2016"
        assert rows[0]["법정동시군구코드"] == "11680"

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        rows = _normalize_dataframe(df)
        assert rows == []


class TestMolitAptConnector:
    def _make_connector(self, client: MagicMock | None = None) -> tuple[MolitAptConnector, MagicMock]:
        mock_client = client or MagicMock()
        connector = MolitAptConnector(
            client=mock_client,
            rate_limiter=_make_rate_limiter(),
            now_fn=_fixed_now,
        )
        return connector, mock_client

    def test_satisfies_connector_protocol(self) -> None:
        connector, _ = self._make_connector()
        assert isinstance(connector, Connector)

    def test_full_row_mapping(self) -> None:
        """Map a fully populated DataFrame row to BronzeAptTransaction."""
        connector, mock_client = self._make_connector()
        mock_client.get_data.return_value = _sample_dataframe()

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        result = connector.fetch(request)

        assert isinstance(result, ConnectorResult)
        assert len(result.records) == 1

        rec = result.records[0]
        assert isinstance(rec, BronzeAptTransaction)
        assert rec.deal_amount == "82,000"
        assert rec.build_year == "2016"
        assert rec.deal_year == "2025"
        assert rec.deal_month == "7"
        assert rec.deal_day == "15"
        assert rec.dong == "역삼동"
        assert rec.apt_name == "래미안"
        assert rec.floor == "12"
        assert rec.area_exclusive == "84.99"
        assert rec.jibun == "123-45"
        assert rec.regional_code == "11680"
        assert rec.sgg_code == "11680"
        assert rec.apt_dong == "101동"
        assert rec.road_name == "테헤란로"
        assert rec.cancel_deal_type is None  # NaN → None
        assert rec.req_gbn == "중개거래"
        assert rec.registration_date == "20250720"
        assert rec.umd_code == "10300"

        # Metadata
        assert rec.source_id == "molit.apartment.transactions"
        assert rec.ingest_timestamp == _FIXED_NOW
        assert rec.raw_response_hash is not None
        assert len(rec.raw_response_hash) == 64  # noqa: PLR2004

    def test_empty_dataframe_returns_empty_result(self) -> None:
        connector, mock_client = self._make_connector()
        mock_client.get_data.return_value = pd.DataFrame()

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        result = connector.fetch(request)

        assert result.records == []
        assert result.manifest.response_count == 0
        assert result.manifest.status == "success"

    def test_api_failure_returns_failed_manifest(self) -> None:
        connector, mock_client = self._make_connector()
        mock_client.get_data.side_effect = ConnectorError("API timeout")

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        result = connector.fetch(request)

        assert result.records == []
        assert result.manifest.status == "failed"
        assert "API timeout" in (result.manifest.error_message or "")

    def test_missing_columns_raises_non_retryable(self) -> None:
        connector, mock_client = self._make_connector()
        # DataFrame with only a few columns
        mock_client.get_data.return_value = pd.DataFrame({"거래금액": ["50,000"], "아파트": ["래미안"]})

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        from younggeul_core.connectors.retry import NonRetryableError

        with pytest.raises(NonRetryableError, match="Missing expected columns"):
            connector.fetch(request)

    def test_manifest_fields_correct(self) -> None:
        connector, mock_client = self._make_connector()
        mock_client.get_data.return_value = _sample_dataframe()

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        result = connector.fetch(request)

        m = result.manifest
        assert m.source_id == "molit.apartment.transactions"
        assert m.api_endpoint == "getRTMSDataSvcAptTradeDev"
        assert m.request_params == {
            "sigungu_code": "11680",
            "year_month": "202507",
        }
        assert m.response_count == 1
        assert m.status == "success"
        assert m.ingested_at == _FIXED_NOW

    def test_rate_limiter_called(self) -> None:
        mock_limiter = MagicMock(spec=RateLimiter)
        mock_client = MagicMock()
        mock_client.get_data.return_value = _sample_dataframe()

        connector = MolitAptConnector(
            client=mock_client,
            rate_limiter=mock_limiter,
            now_fn=_fixed_now,
        )
        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        connector.fetch(request)

        mock_limiter.wait.assert_called_once()

    def test_hash_deterministic_for_same_data(self) -> None:
        connector, mock_client = self._make_connector()
        mock_client.get_data.return_value = _sample_dataframe()

        request = MolitAptRequest(sigungu_code="11680", year_month="202507")
        r1 = connector.fetch(request)

        mock_client.get_data.return_value = _sample_dataframe()
        r2 = connector.fetch(request)

        assert r1.records[0].raw_response_hash == r2.records[0].raw_response_hash


class TestMolitAptRequest:
    def test_frozen(self) -> None:
        req = MolitAptRequest(sigungu_code="11680", year_month="202507")
        with pytest.raises(AttributeError):
            req.sigungu_code = "99999"  # type: ignore[misc]

    def test_fields(self) -> None:
        req = MolitAptRequest(sigungu_code="11680", year_month="202507")
        assert req.sigungu_code == "11680"
        assert req.year_month == "202507"
