"""Schemas for rendered report entries, sections, and documents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RenderedClaimEntry(BaseModel, frozen=True):
    """Rendered claim row included in a report section.

    Attributes:
        claim_id: Claim identifier.
        claim_type: Claim category.
        statement: Human-readable claim statement.
        metrics: Optional structured metrics for the claim.
        evidence_count: Number of supporting evidence items.
        gate_status: Citation gate status for the claim.
    """

    claim_id: str
    claim_type: str
    statement: str
    metrics: dict[str, object] | None = None
    evidence_count: int
    gate_status: str


class RenderedSection(BaseModel, frozen=True):
    """Rendered report section grouping related claims.

    Attributes:
        section_key: Section key used for ordering and routing.
        title: Section display title.
        claims: Claims included in the section.
        claim_count: Number of claims in the section.
    """

    section_key: str
    title: str
    claims: list[RenderedClaimEntry]
    claim_count: int


class RenderedReport(BaseModel, frozen=True):
    """Fully rendered simulation report output.

    Attributes:
        run_id: Simulation run identifier.
        round_no: Final round number represented by the report.
        rendered_at: Report generation timestamp.
        total_claims: Number of total generated claims.
        passed_claims: Number of claims that passed citation checks.
        failed_claims: Number of claims that failed citation checks.
        sections: Rendered report sections.
        markdown: Full markdown rendering of the report.
    """

    run_id: str
    round_no: int
    rendered_at: datetime
    total_claims: int
    passed_claims: int
    failed_claims: int
    sections: list[RenderedSection]
    markdown: str
