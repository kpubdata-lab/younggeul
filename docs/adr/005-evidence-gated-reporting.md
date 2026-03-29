# ADR-005: Evidence-Gated Reporting

## Status
Accepted

## Date
2026-03-28

## Context
Generative AI models excel at producing natural-sounding prose but are prone to "hallucinations"—claims that are factually incorrect or unsupported by the source data. In real estate analysis, where financial decisions are based on the reported metrics (e.g., 매매가 추세, 수익률), a single hallucination can undermine the entire system's credibility. We need a structural guarantee that every claim in a generated report is backed by verifiable evidence.

The risk is amplified when reports summarize multi-round simulations and multiple market segments: tiny numerical drift or subject mismatch can silently produce plausible but wrong narratives. Human review alone is insufficient at scale, especially for regression testing and automated evaluation. The architecture therefore needs a deterministic gate between claim generation and narrative rendering.

## Decision
We will implement a **Three-Phase Evidence-Gated Reporting Pipeline**. This pipeline decouples the factual reasoning from the natural language generation.

1.  **Phase 1: JSON-First Claims Generation**: The "Report Writer" LLM does not write prose. Instead, it generates a list of structured `ReportClaim` objects. Each object contains a `claim_json` (a factual assertion as a schema-enforced JSON object) and a list of `evidence_ids` referencing the specific data points in our "Gold" tables or simulation logs.
2.  **Phase 2: Deterministic Citation Gate**: A deterministic validation node (non-LLM) iterates through the list of claims. For each claim, it verifies:
    -   That all cited `evidence_ids` exist and match the expected `dataset_snapshot_id`.
    -   That the values in the `claim_json` (e.g., "The average price is 1.5 billion KRW") match the values in the evidence store within a specified tolerance.
    -   Claims that pass this gate are marked as "Validated". Claims that fail are sent to a "Critic" LLM for repair or removal.
3.  **Phase 3: Prose Rendering**: Only claims that have successfully passed the citation gate are sent to a final "Renderer" LLM. The Renderer's job is purely linguistic: it converts the validated JSON claims into natural language prose. The Renderer is explicitly instructed NOT to add any factual information not present in the validated claims.

## Alternatives Considered
### A) Single-shot report generation
- **Pros**
  - Lowest latency and simplest orchestration.
  - Minimal implementation complexity.
- **Cons**
  - No structural guarantee of factual grounding.
  - Hard to audit claims and regress quality reliably.
  - High risk for financial decision-support use cases.

### B) Post-hoc fact-checking after prose generation
- **Pros**
  - Preserves natural generation flow.
  - Can catch some obvious inconsistencies.
- **Cons**
  - Repairs after narrative generation are brittle.
  - Difficult to map prose fragments back to exact evidence IDs.
  - Increased rework loops and inconsistent style after corrections.

### C) Three-phase evidence-gated pipeline (Selected)
- **Pros**
  - Claim-evidence linkage is explicit before prose exists.
  - Deterministic gate enforces minimum trust guarantees.
  - Clear operational metrics (passed/failed claims).
- **Cons**
  - More pipeline complexity and latency.
  - Requires robust claim schema and retry policies.

## Rationale
The selected design separates factual correctness from linguistic quality. This is essential because LLMs are strongest at language generation, while deterministic code is strongest at validation and constraint enforcement.

Younggeul already encodes this split in the graph topology and schemas. Claims are represented as `ReportClaim` objects in core state contracts, validated in `citation_gate`, and only then transformed into markdown by `report_renderer`.

The design constraint is “no unchecked fact reaches prose.” This is stricter than common RAG pipelines and better aligned with audit requirements for simulation-backed market analysis.

## Examples
### 1) Real `ReportClaim` schema

```python
# core/src/younggeul_core/state/simulation.py
class ReportClaim(BaseModel):
    claim_id: str
    claim_json: dict[str, object]
    evidence_ids: list[str]
    gate_status: Literal["pending", "passed", "failed", "repaired"] = "pending"
    repair_count: int = 0
```

This is the typed envelope passed between writer, gate, critic, and renderer stages.

### 2) Deterministic citation-gate validation flow

```python
# apps/kr-seoul-apartment/src/.../simulation/nodes/citation_gate_node.py
for claim in report_claims:
    evidence_ids = list(claim.evidence_ids)
    if not evidence_ids:
        failure_reason = "missing evidence_ids"
    ...
    record = evidence_store.get(evidence_id)
    if record is None:
        failure_reason = f"missing evidence record: {evidence_id}"
    ...
    if not any(record.round_no == round_no for record in resolved_records):
        failure_reason = f"no evidence for round_no={round_no}"
```

Claims are rewritten with `gate_status` (`passed`/`failed`) and summary outcomes are emitted as `CITATION_GATE` events.

### 3) Actual graph node sequence implementing the pipeline

```python
# apps/kr-seoul-apartment/src/.../simulation/graph.py
graph.add_node("report_writer", _traced_node("report_writer", report_writer_node))
graph.add_node("critic", _traced_node("critic", _make_passthrough_stub(event_store, "critic")))
graph.add_node("citation_gate", _traced_node("citation_gate", citation_gate_node))
graph.add_node("report_renderer", _traced_node("report_renderer", report_renderer_node))

graph.add_edge("report_writer", "critic")
graph.add_edge("critic", "citation_gate")
graph.add_edge("citation_gate", "report_renderer")
```

These concrete node names and edges encode the evidence-gated transition before final rendering.

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
