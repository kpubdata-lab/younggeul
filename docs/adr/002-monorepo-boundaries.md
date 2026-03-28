# ADR-002: Monorepo Structure and Package Boundaries

## Status
Accepted

## Date
2026-03-28

## Context
The Younggeul project must simultaneously support:
1.  **Platform Core**: A reusable, generic real estate engine including reasoning logic, evidence validation, and data plane processing.
2.  **Specialized Applications**: Domain-specific or geography-specific logic (e.g., analyzing Seoul apartments vs. Busan commercial properties).
3.  **Benchmark/Evaluation Framework**: A way to measure the performance and correctness of the platform across various datasets.

Without clear package boundaries, these components could become tightly coupled. For instance, if the core platform depends on Seoul-specific apartment data schemas, it becomes difficult to extend the system to other asset types or countries.

## Decision
We will adopt a **Monorepo Structure** with three distinct top-level directories, each with its own package definition and clear dependency directions.

### Directory Structure
- `core/`: This contains the platform-agnostic runtime. It defines the schemas for Bronze/Silver/Gold data, the LangGraph state machine structure, and the evidence-gated reporting engine. It will be publishable as the `younggeul-core` package.
- `apps/`: This directory houses geography and asset-specific implementations. Each subdirectory follows the pattern `{country}-{asset}`, such as `apps/kr-seoul-apartment`. These applications configure the core engine with specific data sources (e.g., 매매 실거래가, 전월세) and domain-specific prompts.
- `benchmarks/`: This directory contains evaluation scenarios organized by domain, such as `benchmarks/investment-roi` or `benchmarks/housing-affordability`. These benchmarks include "golden" datasets and automated assertions.

### Dependency Rules
1.  **Core is Foundation**: The `core/` package MUST NOT import anything from `apps/` or `benchmarks/`. It must remain purely generic.
2.  **Apps Build on Core**: Packages in `apps/` import from `core/`. They provide the concrete implementation of the abstract interfaces defined in core.
3.  **Benchmarks Evaluate Both**: Packages in `benchmarks/` may import from both `core/` and any package in `apps/` to run full end-to-end evaluation cycles.
4.  **No Cross-App Imports**: Packages within `apps/` should not depend on each other (e.g., `kr-seoul-apartment` should not import from `kr-daegu-commercial`). Common logic between apps should be promoted to `core/`.

## Consequences
### Positive
- **Clear Separation of Concerns**: Developers working on the core engine can do so without being distracted by specific real estate market details.
- **Extensibility**: Adding a new country or asset type is as simple as creating a new subdirectory in `apps/` and implementing the required core interfaces.
- **Scalable Testing**: Benchmarks can be run against the generic core using synthetic data or against specific applications using real-world datasets.

### Negative
- **Build Complexity**: Managing a monorepo requires more sophisticated build and CI tooling (e.g., using workspaces in npm/yarn/pnpm or specialized tools like Nx/Turborepo).
- **Initial Setup Cost**: Defining the abstract interfaces in `core/` that are flexible enough for all future `apps/` requires careful upfront design.

### Neutral
- **Versioning**: Each package in the monorepo can have its own versioning scheme, though they are managed in a single git repository.

## References
- ADR-004: LangGraph Usage Boundaries
- ADR-005: Evidence-Gated Reporting
