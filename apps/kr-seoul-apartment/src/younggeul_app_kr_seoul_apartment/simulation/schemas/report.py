from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RenderedClaimEntry(BaseModel, frozen=True):
    claim_id: str
    claim_type: str
    statement: str
    metrics: dict[str, object] | None = None
    evidence_count: int
    gate_status: str


class RenderedSection(BaseModel, frozen=True):
    section_key: str
    title: str
    claims: list[RenderedClaimEntry]
    claim_count: int


class RenderedReport(BaseModel, frozen=True):
    run_id: str
    round_no: int
    rendered_at: datetime
    total_claims: int
    passed_claims: int
    failed_claims: int
    sections: list[RenderedSection]
    markdown: str
