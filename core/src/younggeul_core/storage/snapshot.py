"""Snapshot manifest schemas and helpers for dataset integrity checks."""

import hashlib
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class SnapshotTableEntry(BaseModel):
    """Describe one table included in a dataset snapshot.

    Attributes:
        table_name: Logical table name.
        table_hash: SHA-256 hash of the table content.
        record_count: Number of records in the table.
        schema_version: Schema version used for this table.
        source_uri: Optional source URI for table provenance.
        file_format: Storage format for the table export.
    """

    table_name: str
    table_hash: str
    record_count: int = Field(ge=0)
    schema_version: str
    source_uri: str | None = None
    file_format: Literal["parquet", "csv", "jsonl"] = "parquet"

    model_config = ConfigDict(frozen=True)

    @field_validator("table_hash")
    @classmethod
    def validate_table_hash(cls, value: str) -> str:
        """Validate that table_hash is a lowercase SHA-256 hex string.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if not _SHA256_HEX_RE.fullmatch(value):
            raise ValueError("table_hash must be a 64-character lowercase hex SHA-256 string")
        return value


class SnapshotManifest(BaseModel):
    """Represent a full dataset snapshot manifest and derived aggregates.

    Attributes:
        dataset_snapshot_id: Unique snapshot identifier.
        created_at: Timestamp when the snapshot was created.
        description: Optional snapshot description.
        table_entries: Table-level entries included in the snapshot.
        source_ids: Source identifiers contributing to the snapshot.
        ingestion_started_at: Optional ingestion start timestamp.
        ingestion_completed_at: Optional ingestion completion timestamp.
    """

    dataset_snapshot_id: str
    created_at: datetime
    description: str | None = None
    table_entries: list[SnapshotTableEntry]
    source_ids: list[str] = Field(default_factory=list)
    ingestion_started_at: datetime | None = None
    ingestion_completed_at: datetime | None = None

    model_config = ConfigDict(frozen=True)

    @field_validator("dataset_snapshot_id")
    @classmethod
    def validate_dataset_snapshot_id(cls, value: str) -> str:
        """Validate that dataset_snapshot_id is lowercase SHA-256 hex.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if not _SHA256_HEX_RE.fullmatch(value):
            raise ValueError("dataset_snapshot_id must be a 64-character lowercase hex SHA-256 string")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def table_hashes(self) -> dict[str, str]:
        """Return table hashes indexed by table name.

        Returns:
            Mapping of table names to table hashes.
        """

        return {entry.table_name: entry.table_hash for entry in self.table_entries}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def record_counts(self) -> dict[str, int]:
        """Return record counts indexed by table name.

        Returns:
            Mapping of table names to record counts.
        """

        return {entry.table_name: entry.record_count for entry in self.table_entries}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_records(self) -> int:
        """Return the total number of records across all tables.

        Returns:
            Sum of all table record counts.
        """

        return sum(entry.record_count for entry in self.table_entries)

    def validate_integrity(self) -> bool:
        """Validate that manifest content reproduces dataset_snapshot_id.

        Returns:
            True when computed and declared snapshot IDs match.
        """

        computed_id = self.compute_snapshot_id(self.table_hashes)
        return computed_id == self.dataset_snapshot_id

    def get_table(self, name: str) -> SnapshotTableEntry | None:
        """Return a table entry by name when present.

        Args:
            name: Table name to look up.

        Returns:
            Matching table entry, or None when no entry exists.
        """

        for entry in self.table_entries:
            if entry.table_name == name:
                return entry
        return None

    @classmethod
    def compute_snapshot_id(cls, table_hashes: dict[str, str]) -> str:
        """Compute a deterministic snapshot ID from table hashes.

        Args:
            table_hashes: Mapping of table names to table hashes.

        Returns:
            SHA-256 digest representing the ordered table hash set.
        """

        items = sorted(table_hashes.items(), key=lambda item: item[0])
        joined = "".join(f"{table_name}:{table_hash}" for table_name, table_hash in items)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()
