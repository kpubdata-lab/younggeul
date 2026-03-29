# ADR-004: LangGraph Usage Boundaries

## Status
Accepted

## Date
2026-03-28

## Context
LangGraph provides a powerful framework for multi-agent orchestration, allowing for cycles, branching, and complex state management. However, unconstrained use of LangGraph—especially with free-form message lists—tends to produce "black box" agents that are difficult to debug, hard to test, and prone to state bloat. We need to define clear boundaries and patterns for LangGraph usage in Younggeul to ensure reproducibility and maintainability.

Younggeul’s simulation pipeline must combine deterministic transforms, typed evidence artifacts, and constrained LLM usage. If graph state becomes untyped or overly conversational, deterministic replay and schema validation degrade quickly. We therefore need a strict state-machine style discipline for graph construction, node signatures, and accumulated state fields.

## Decision
We will enforce several strict constraints on how LangGraph is used within the project:

1.  **No `add_messages` Pattern**: We will not use the standard `list[BaseMessage]` pattern in our LangGraph state. All state must be defined using explicit, typed fields in a `TypedDict`. This forces developers to consider exactly what information is being passed between nodes.
2.  **No LLM in the Data Plane**: The data transformation pipeline (Bronze → Silver → Gold) must be 100% deterministic code. No LLM-based entity resolution or fuzzy matching is allowed in these stages. Entity resolution must use a predefined, multi-step algorithm based on identifiers like building codes (법정동코드) and parcel numbers (지번).
3.  **Structured Action Proposals**: Every agent node must read the typed state and produce a structured `ActionProposal` object. No free-form string passing between nodes is permitted. This makes it possible to unit-test individual nodes by mocking their input and verifying their output structure.
4.  **External Trace Store**: Large trace data, full LLM prompt/response pairs, and intermediate reasoning steps must be written to an external JSONL store. They should NOT be kept in the LangGraph state. This prevents the state from growing too large, which can lead to memory issues and slow checkpointing.
5.  **Bounded Recursion**: Every simulation or multi-step reasoning graph must have a hard cap on the number of rounds (configurable, but defaulting to 8). This prevents infinite loops and ensures predictable execution times.

## Alternatives Considered
### A) Free-form message list (standard LangGraph chat pattern)
- **Pros**
  - Very flexible for rapid prototyping.
  - Minimal upfront schema work.
- **Cons**
  - Poor traceability of business-critical fields.
  - State growth and replay instability in long runs.
  - Harder deterministic tests and static analysis.

### B) Hybrid typed state + free-form message channel
- **Pros**
  - Keeps key fields typed while preserving chat flexibility.
  - Easier migration path from prototype agents.
- **Cons**
  - Dual-state complexity; message channel can bypass contracts.
  - In practice, “temporary” free-form paths become permanent.
  - Validation surface remains ambiguous.

### C) Strict `TypedDict` state with no message list (Selected)
- **Pros**
  - Explicit contracts for every node transition.
  - Easier debugging and deterministic replay.
  - Better compatibility with schema validation and unit tests.
- **Cons**
  - More up-front schema maintenance.
  - Reduced flexibility for ad hoc agent communication.

## Rationale
Younggeul optimizes for reproducibility and auditability, not chat-like free-form interaction inside the orchestration runtime. Typed state ensures each node reads/writes explicit fields and keeps data-plane and reasoning-plane boundaries visible.

The existing graph implementation (`apps/kr-seoul-apartment/.../simulation/graph.py`) already reflects this design: nodes are named business transitions (`intake_planner`, `scenario_builder`, `world_initializer`, `citation_gate`, `report_renderer`), and edges model process flow rather than conversational turns.

By pairing strict `SimulationGraphState` fields with bounded rounds (`max_rounds`), we avoid hidden state channels and ensure that deterministic components remain testable independent of LLM variability.

## Examples
### 1) Real strict state schema (`TypedDict`)

```python
# apps/kr-seoul-apartment/src/.../simulation/graph_state.py
class SimulationGraphState(TypedDict, total=False):
    user_query: str
    intake_plan: dict[str, Any]
    participant_roster: dict[str, Any]
    run_meta: RunMeta
    snapshot: SnapshotRef
    scenario: ScenarioSpec
    round_no: int
    max_rounds: int
    world: dict[str, SegmentState]
    participants: dict[str, ParticipantState]
    governance_actions: dict[str, ActionProposal]
    market_actions: dict[str, ActionProposal]
    last_outcome: RoundOutcome | None
    event_refs: Annotated[list[str], operator.add]
    evidence_refs: Annotated[list[str], operator.add]
    report_claims: Annotated[list[ReportClaim], operator.add]
    warnings: Annotated[list[str], operator.add]
```

No `messages: list[BaseMessage]` field exists.

### 2) Node function signature used in practice

```python
# apps/kr-seoul-apartment/src/.../simulation/nodes/citation_gate_node.py
def make_citation_gate_node(evidence_store: EvidenceStore, event_store: EventStore) -> Any:
    def node(state: SimulationGraphState) -> dict[str, Any]:
        ...
        return {"warnings": warnings, "event_refs": [event_id]}
    return node
```

This enforces typed input (`SimulationGraphState`) and structured output (`dict[str, Any]` with known keys).

### 3) Rejected pattern (for contrast)

```python
# Rejected for Younggeul
class ChatState(TypedDict):
    messages: list[BaseMessage]
```

This pattern is intentionally avoided because it obscures domain state transitions and weakens deterministic validation.

## Consequences
### Positive
- **Improved Debuggability**: By having structured state and external traces, it is much easier to pinpoint exactly where an agent made a wrong decision.
- **Enhanced Reproducibility**: Deterministic data planes and structured state ensure that if you run the same agent on the same snapshot (ADR-003), you get consistent results.
- **Lower Memory Footprint**: Avoiding the "message list" pattern and offloading traces prevents state explosion in long-running simulations.

### Negative
- **Upfront Schema Work**: Developers must spend more time defining types and schemas for every node and state transition.
- **Reduced Flexibility**: Agents cannot "freestyle" their communication as easily. Every interaction must be modeled and constrained.

### Neutral
- **Shift in Mindset**: This requires developers to think of LangGraph more as a state machine for business logic rather than a general-purpose "chat" framework.

## References
- ADR-003: Immutable Dataset Snapshots
- ADR-005: Evidence-Gated Reporting
