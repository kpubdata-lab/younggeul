# ADR-004: LangGraph Usage Boundaries

## Status
Accepted

## Date
2026-03-28

## Context
LangGraph provides a powerful framework for multi-agent orchestration, allowing for cycles, branching, and complex state management. However, unconstrained use of LangGraph—especially with free-form message lists—tends to produce "black box" agents that are difficult to debug, hard to test, and prone to state bloat. We need to define clear boundaries and patterns for LangGraph usage in Younggeul to ensure reproducibility and maintainability.

## Decision
We will enforce several strict constraints on how LangGraph is used within the project:

1.  **No `add_messages` Pattern**: We will not use the standard `list[BaseMessage]` pattern in our LangGraph state. All state must be defined using explicit, typed fields in a `TypedDict`. This forces developers to consider exactly what information is being passed between nodes.
2.  **No LLM in the Data Plane**: The data transformation pipeline (Bronze → Silver → Gold) must be 100% deterministic code. No LLM-based entity resolution or fuzzy matching is allowed in these stages. Entity resolution must use a predefined, multi-step algorithm based on identifiers like building codes (법정동코드) and parcel numbers (지번).
3.  **Structured Action Proposals**: Every agent node must read the typed state and produce a structured `ActionProposal` object. No free-form string passing between nodes is permitted. This makes it possible to unit-test individual nodes by mocking their input and verifying their output structure.
4.  **External Trace Store**: Large trace data, full LLM prompt/response pairs, and intermediate reasoning steps must be written to an external JSONL store. They should NOT be kept in the LangGraph state. This prevents the state from growing too large, which can lead to memory issues and slow checkpointing.
5.  **Bounded Recursion**: Every simulation or multi-step reasoning graph must have a hard cap on the number of rounds (configurable, but defaulting to 8). This prevents infinite loops and ensures predictable execution times.

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
