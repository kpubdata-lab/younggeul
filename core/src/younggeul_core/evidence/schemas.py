"""Pydantic schemas for evidence, claims, and gate evaluation records."""

from datetime import datetime
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class EvidenceRecord(BaseModel):
    """Represent a single evidence item backing a generated claim.

    Attributes:
        evidence_id: Unique identifier for the evidence record.
        dataset_snapshot_id: Snapshot identifier tied to the evidence source.
        source_table: Source table name where the value originated.
        source_row_hash: SHA-256 hash for the source row.
        field_name: Name of the source field.
        field_value: Serialized field value used as evidence.
        field_type: Logical type of the evidence value.
        gu_code: Optional district code associated with the evidence.
        period: Optional reporting period associated with the evidence.
        created_at: Timestamp when the evidence record was created.
    """

    evidence_id: str
    dataset_snapshot_id: str
    source_table: str
    source_row_hash: str
    field_name: str
    field_value: str
    field_type: Literal["int", "float", "str", "date", "bool"]
    gu_code: str | None = None
    period: str | None = None
    created_at: datetime

    model_config = ConfigDict(frozen=True)

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id_uuid(cls, value: str) -> str:
        """Validate that evidence_id is a UUID string.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        UUID(value)
        return value

    @field_validator("dataset_snapshot_id", "source_row_hash")
    @classmethod
    def validate_sha256_hex(cls, value: str) -> str:
        """Validate that hash-like fields are lowercase SHA-256 hex.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if not _SHA256_HEX_RE.fullmatch(value):
            raise ValueError("must be a 64-character lowercase hex SHA-256 string")
        return value


class ClaimRecord(BaseModel):
    """Represent a report claim and its evidence review state.

    Attributes:
        claim_id: Unique identifier for the claim.
        run_id: Identifier of the simulation or report run.
        claim_json: Structured claim payload.
        evidence_ids: Evidence identifiers referenced by the claim.
        gate_status: Current gate status for claim verification.
        gate_checked_at: Timestamp when the gate was last checked.
        repair_count: Number of repair attempts applied to the claim.
        repair_notes: Optional notes describing repairs.
        created_at: Timestamp when the claim record was created.
    """

    claim_id: str
    run_id: str
    claim_json: dict[str, Any]
    evidence_ids: list[str]
    gate_status: Literal["pending", "passed", "failed", "repaired"] = "pending"
    gate_checked_at: datetime | None = None
    repair_count: int = 0
    repair_notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(frozen=True)

    @field_validator("claim_id", "run_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        """Validate that UUID-based identifiers are valid UUID strings.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        UUID(value)
        return value

    @field_validator("repair_count")
    @classmethod
    def validate_repair_count(cls, value: int) -> int:
        """Validate that repair_count does not exceed the allowed limit.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        if value > 2:
            raise ValueError("repair_count must be <= 2")
        return value


class GateResult(BaseModel):
    """Represent the verification outcome for a claim's evidence set.

    Attributes:
        claim_id: Identifier of the evaluated claim.
        status: Final gate outcome for the claim.
        checked_evidence_ids: Evidence identifiers checked by the gate.
        mismatches: Details of detected mismatches.
        checked_at: Timestamp when gate evaluation completed.
    """

    claim_id: str
    status: Literal["passed", "failed"]
    checked_evidence_ids: list[str]
    mismatches: list[dict[str, Any]] = Field(default_factory=list)
    checked_at: datetime

    model_config = ConfigDict(frozen=True)

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id_uuid(cls, value: str) -> str:
        """Validate that claim_id is a UUID string.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If validation fails.
        """

        UUID(value)
        return value
