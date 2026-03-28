# ADR-005: Evidence-Gated Reporting

## Status
Accepted

## Date
2026-03-28

## Context
Generative AI models excel at producing natural-sounding prose but are prone to "hallucinations"—claims that are factually incorrect or unsupported by the source data. In real estate analysis, where financial decisions are based on the reported metrics (e.g., 매매가 추세, 수익률), a single hallucination can undermine the entire system's credibility. We need a structural guarantee that every claim in a generated report is backed by verifiable evidence.

## Decision
We will implement a **Three-Phase Evidence-Gated Reporting Pipeline**. This pipeline decouples the factual reasoning from the natural language generation.

1.  **Phase 1: JSON-First Claims Generation**: The "Report Writer" LLM does not write prose. Instead, it generates a list of structured `ReportClaim` objects. Each object contains a `claim_json` (a factual assertion as a schema-enforced JSON object) and a list of `evidence_ids` referencing the specific data points in our "Gold" tables or simulation logs.
2.  **Phase 2: Deterministic Citation Gate**: A deterministic validation node (non-LLM) iterates through the list of claims. For each claim, it verifies:
    -   That all cited `evidence_ids` exist and match the expected `dataset_snapshot_id`.
    -   That the values in the `claim_json` (e.g., "The average price is 1.5 billion KRW") match the values in the evidence store within a specified tolerance.
    -   Claims that pass this gate are marked as "Validated". Claims that fail are sent to a "Critic" LLM for repair or removal.
3.  **Phase 3: Prose Rendering**: Only claims that have successfully passed the citation gate are sent to a final "Renderer" LLM. The Renderer's job is purely linguistic: it converts the validated JSON claims into natural language prose. The Renderer is explicitly instructed NOT to add any factual information not present in the validated claims.

## Consequences
### Positive
- **Zero-Hallucination Guarantee**: By structurally enforcing the link between claims and evidence before any prose is written, we eliminate the primary source of LLM error in reporting.
- **Auditability**: Every sentence in a final report can be traced back to a specific set of IDs in our immutable data snapshots (ADR-003).
- **Separation of Reasoning and Writing**: Different models can be used for Phase 1 (high reasoning capability) and Phase 3 (high linguistic quality), optimizing for both correctness and readability.

### Negative
- **Increased Latency**: A minimum of three LLM calls is required for every report. This makes the system slower than a single-shot generation approach.
- **Complex Repair Logic**: Handling failed claims and implementing the "Critic" loop adds significant complexity to the report generation logic.

### Neutral
- **Prompt Engineering Effort**: Three separate prompts must be developed and maintained, each with its own specialized few-shot examples and constraints.

## References
- ADR-003: Immutable Dataset Snapshots
- ADR-004: LangGraph Usage Boundaries
