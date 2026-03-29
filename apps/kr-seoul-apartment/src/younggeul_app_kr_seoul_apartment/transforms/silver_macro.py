"""Silver normalization for macroeconomic Bronze records."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from younggeul_core.state.bronze import BronzeInterestRate, BronzeMigration
from younggeul_core.state.silver import SilverInterestRate, SilverMigration

_PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def parse_date(raw: str | None) -> date | None:
    """Parse an ISO-formatted date string.

    Args:
        raw: Raw date string.

    Returns:
        Parsed date value, or ``None`` when invalid.
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return None


def parse_decimal_2dp(raw: str | None) -> Decimal | None:
    """Parse decimal text and quantize to two decimal places.

    Args:
        raw: Raw decimal value string.

    Returns:
        Parsed and quantized decimal value, or ``None`` if invalid.
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_count(raw: str | None) -> int | None:
    """Parse count text that may include comma separators.

    Args:
        raw: Raw count string.

    Returns:
        Parsed integer count, or ``None`` when parsing fails.
    """
    if raw is None:
        return None
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def build_period(year: str | None, month: str | None) -> str | None:
    """Build a ``YYYY-MM`` period string from year and month fields.

    Args:
        year: Raw year string.
        month: Raw month string.

    Returns:
        Validated period string, or ``None`` when input is invalid.
    """
    if year is None or month is None:
        return None
    year_clean = year.strip()
    month_clean = month.strip()
    if not year_clean or not month_clean:
        return None
    period = f"{year_clean}-{month_clean.zfill(2)}"
    if _PERIOD_PATTERN.fullmatch(period) is None:
        return None
    return period


def normalize_interest_rate(bronze: BronzeInterestRate) -> SilverInterestRate | None:
    """Normalize one Bronze interest-rate record.

    Args:
        bronze: Source Bronze interest-rate record.

    Returns:
        Normalized Silver interest-rate record, or ``None`` if invalid.
    """
    rate_date = parse_date(bronze.date)
    if rate_date is None:
        return None

    rate_type = bronze.rate_type
    if rate_type is None or not rate_type.strip():
        return None

    rate_value = parse_decimal_2dp(bronze.rate_value)
    if rate_value is None:
        return None

    return SilverInterestRate(
        rate_date=rate_date,
        rate_type=rate_type,
        rate_value=rate_value,
        source_id=bronze.source_id,
        ingest_timestamp=bronze.ingest_timestamp,
    )


def normalize_migration(bronze: BronzeMigration) -> SilverMigration | None:
    """Normalize one Bronze migration record.

    Args:
        bronze: Source Bronze migration record.

    Returns:
        Normalized Silver migration record, or ``None`` if invalid.
    """
    period = build_period(bronze.year, bronze.month)
    if period is None:
        return None

    region_code = bronze.region_code
    if region_code is None or not region_code.strip():
        return None

    region_name = bronze.region_name
    if region_name is None or not region_name.strip():
        return None

    in_count = parse_count(bronze.in_count)
    out_count = parse_count(bronze.out_count)
    net_count = parse_count(bronze.net_count)
    if in_count is None or out_count is None or net_count is None:
        return None

    return SilverMigration(
        period=period,
        region_code=region_code,
        region_name=region_name,
        in_count=in_count,
        out_count=out_count,
        net_count=net_count,
        source_id=bronze.source_id,
        ingest_timestamp=bronze.ingest_timestamp,
    )


def normalize_interest_rate_batch(records: list[BronzeInterestRate]) -> list[SilverInterestRate]:
    """Normalize a batch of Bronze interest-rate records.

    Args:
        records: Bronze interest-rate records to normalize.

    Returns:
        Successfully normalized Silver interest-rate records.
    """
    normalized: list[SilverInterestRate] = []
    for record in records:
        silver = normalize_interest_rate(record)
        if silver is not None:
            normalized.append(silver)
    return normalized


def normalize_migration_batch(records: list[BronzeMigration]) -> list[SilverMigration]:
    """Normalize a batch of Bronze migration records.

    Args:
        records: Bronze migration records to normalize.

    Returns:
        Successfully normalized Silver migration records.
    """
    normalized: list[SilverMigration] = []
    for record in records:
        silver = normalize_migration(record)
        if silver is not None:
            normalized.append(silver)
    return normalized
