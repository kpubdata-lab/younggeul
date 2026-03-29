"""Evidence record schemas and in-memory storage interface."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel, frozen=True):
    """Immutable evidence payload linked to simulation subjects.

    Attributes:
        evidence_id: Unique evidence identifier.
        kind: Evidence category used by report generation.
        subject_type: Subject domain type for the evidence.
        subject_id: Subject identifier within the subject type.
        round_no: Simulation round associated with this evidence.
        payload: Structured evidence payload.
        source_event_ids: Event IDs used to derive the evidence.
        created_at: Evidence creation timestamp.
    """

    evidence_id: str
    kind: str
    subject_type: str
    subject_id: str
    round_no: int
    payload: dict[str, Any]
    source_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class EvidenceStore(Protocol):
    """Protocol for evidence storage backends."""

    def add(self, record: EvidenceRecord) -> None: ...

    def get(self, evidence_id: str) -> EvidenceRecord | None: ...

    def get_all(self) -> list[EvidenceRecord]: ...

    def get_by_kind(self, kind: str) -> list[EvidenceRecord]: ...

    def get_by_subject(self, subject_type: str, subject_id: str) -> list[EvidenceRecord]: ...

    def count(self) -> int: ...


class InMemoryEvidenceStore:
    """In-memory evidence store keyed by evidence ID."""

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> None:
        """Insert a new evidence record.

        Args:
            record: Evidence record to store.

        Raises:
            ValueError: When the evidence ID already exists.
        """
        if record.evidence_id in self._records:
            raise ValueError(f"Duplicate evidence_id: {record.evidence_id}")
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        """Return one evidence record by ID.

        Args:
            evidence_id: Evidence identifier.

        Returns:
            Matching evidence record when present, else ``None``.
        """
        return self._records.get(evidence_id)

    def get_all(self) -> list[EvidenceRecord]:
        """Return all stored evidence records.

        Returns:
            Stored records in insertion order.
        """
        return list(self._records.values())

    def get_by_kind(self, kind: str) -> list[EvidenceRecord]:
        """Return records matching an evidence kind.

        Args:
            kind: Evidence kind to filter by.

        Returns:
            Matching evidence records.
        """
        return [record for record in self._records.values() if record.kind == kind]

    def get_by_subject(self, subject_type: str, subject_id: str) -> list[EvidenceRecord]:
        """Return records matching a specific subject.

        Args:
            subject_type: Subject type to filter by.
            subject_id: Subject identifier to filter by.

        Returns:
            Matching evidence records.
        """
        return [
            record
            for record in self._records.values()
            if record.subject_type == subject_type and record.subject_id == subject_id
        ]

    def count(self) -> int:
        """Return the number of stored evidence records.

        Returns:
            Total evidence record count.
        """
        return len(self._records)
