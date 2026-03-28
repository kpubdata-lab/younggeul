# Technical Design Document: Younggeul (v0.1)

## 1. Introduction
This document serves as the comprehensive **Technical Design Document (TDD)** for the Younggeul project. Younggeul is an open-source, reproducible platform for South Korean real estate simulation and analysis, designed to provide high-fidelity insights into market dynamics while maintaining a strict evidence-based reasoning chain. 

The system aims to address the complexity of the South Korean housing market by modeling the interplay between macroeconomic factors (interest rates, population movement) and micro-level market behaviors (individual buyer and seller actions). By utilizing a multi-agent simulation framework, Younggeul allows researchers and enthusiasts to explore "what-if" scenarios, such as the impact of sudden regulatory changes or shifts in monetary policy.

The initial scope (**v0.1**) focuses specifically on **Seoul apartment directional and volume prediction** at a monthly granularity (`gu_month`). By separating deterministic data processing (Data Plane) from multi-agent reasoning (Simulation Plane) and measuring results against golden datasets (Evaluation Plane), Younggeul ensures that every market insight is both auditable and reproducible. This document outlines the architectural blueprints, data models, and operational workflows required to achieve these goals.

### 1.1 Document Scope and Goals
- **Architectural Definition**: Define the technical architecture across the three operational planes (Data, Simulation, Evaluation).
- **Reproducibility Standards**: Establish the data lifecycle and snapshotting requirements to guarantee perfect reproducibility.
- **Agent Orchestration**: Outline the LangGraph orchestration and multi-agent interaction patterns for market simulation.
- **Hallucination Prevention**: Formalize the evidence-gated reporting process to eliminate LLM-generated hallucinations.
- **Operational Excellence**: Detail the CI/CD and infrastructure components necessary for sustainable development.

### 1.2 Target Audience
- **Core Developers**: Who need to understand the architectural boundaries and state management.
- **Application Developers**: Who want to extend Younggeul to new regions or asset types.
- **Researchers/Analysts**: Who utilize the simulation and evaluation planes for market study.

## 2. System Architecture

### 2.1 Three-Plane Architecture
The system architecture is organized into three distinct planes of operation to separate data integrity from agent reasoning and performance measurement. This separation of concerns ensures that the platform remains extensible and that the reasoning logic can be independently verified against the underlying data.

- **Data Plane**: Handles the ingestion, cleaning, and aggregation of public data into immutable snapshots. It provides the ground truth for all simulations.
- **Simulation Plane**: Orchestrates the multi-agent market simulation using LangGraph. It models the decision-making processes of various market actors.
- **Evaluation Plane**: Provides a framework for measuring the accuracy and reliability of the simulations against historical benchmarks.

```text
+-----------------------------------------------------------------------+
|                           Evaluation Plane                            |
| (promptfoo, benchmarks/kr-housing, Metrics: Dir-Acc, RMSE, Coverage) |
+-----------------------------------^-----------------------------------+
                                    |
                                    | (Feeds back metrics for optimization)
                                    |
+-----------------------------------+-----------------------------------+
|                           Simulation Plane                            |
| (LangGraph, State: SimulationState, Agents: Planner/Scenario/Writer)  |
+-----------------------------------^-----------------------------------+
                                    |
                                    | (Provides immutable data snapshots)
                                    |
+-----------------------------------+-----------------------------------+
|                              Data Plane                               |
| (Pydantic, Bronze/Silver/Gold Layers, SHA-256 Snapshot Manifests)     |
+-----------------------------------------------------------------------+
```

### 2.2 Monorepo Layout
The project follows a strict monorepo structure as defined in ADR-002, ensuring clear boundaries and package-level isolation. This structure allows for independent versioning and testing of different components while maintaining a unified codebase.

- **`core/` (`younggeul-core`)**: Contains the platform-agnostic runtime. This includes the generic LangGraph state machine, evidence-gated reporting engine, base Pydantic schemas, and common utilities for data processing.
- **`apps/kr-seoul-apartment/`**: Houses the specialized implementation for the Seoul apartment market. This includes domain-specific prompts for the agents, specialized data ingestion logic for Korean public APIs, and regional market configuration.
- **`benchmarks/kr-housing/`**: Contains evaluation scenarios specific to the South Korean housing market. It includes "golden" datasets derived from historical records and automated metric assertions used by `promptfoo`.

**Dependency Direction:** `core` ← `apps` ← `benchmarks`. Dependencies never flow in reverse, ensuring the core remains generic and reusable across different geographies or asset types. This discipline prevents the core from being "polluted" by region-specific logic.

## 3. Data Plane
The Data Plane is responsible for the entire lifecycle of real estate data, from raw API responses to aggregated features used for simulation. Following ADR-004 and ADR-006, all operations in this plane are **100% deterministic**; no LLMs are used for data cleaning or entity resolution to avoid introducing non-deterministic errors at the foundation of the system.

### 3.1 Data Layers
1.  **Bronze (Raw)**: Unmodified API responses stored exactly as received from providers. This layer acts as a permanent record of the raw input. Primary sources include:
    - **MOLIT 실거래가 공개시스템**: Actual transaction prices for apartments.
    - **Bank of Korea (ECOS)**: Historical and current base interest rates.
    - **Statistics Korea (KOSIS)**: Net migration and population movement data.
2.  **Silver (Cleaned)**: Typed Pydantic models with standardized schemas. Data is normalized across different sources. Entity resolution (matching buildings across datasets) is performed using a deterministic multi-step algorithm based on Legal-Dong Codes (법정동코드) and Parcel Numbers (지번).
3.  **Gold (Aggregated)**: Features aggregated at the `gu_month` level (district-level monthly averages), which serves as the primary input for simulations. Key features include:
    - **Median Price** (매매 중위가격): The middle value of all transactions in a given month.
    - **Trading Volume** (거래량): Total number of transactions recorded.
    - **Price Change %** (전월 대비 가격 변동률): Month-over-month price trend.
    - **Base Interest Rate** (기준금리): The national interest rate at the time.
    - **Net Migration** (순이동 인구): The difference between people moving in and out of the district.

### 3.2 Snapshot System
To ensure perfect reproducibility (ADR-003), the system uses an immutable snapshot mechanism. This allows researchers to reference a specific version of the truth, even as new data is ingested into the system.

- **Identifier**: A unique `dataset_snapshot_id` generated using a SHA-256 hash derived from the collective contents of all tables included in the snapshot.
- **Storage**: Data is stored in versioned Parquet files, which provide efficient columnar storage and high compression. Each snapshot is accompanied by a JSON manifest.
- **Manifest**: Contains comprehensive metadata including source URLs, ingestion timestamps, schema versions, and the individual hashes of each table.

No raw data is stored in the git repository to keep it lightweight (ADR-006). Development and CI/CD pipelines rely on hand-crafted synthetic test fixtures that mirror the production schemas.

## 4. Simulation Plane (LangGraph)
The Simulation Plane orchestrates multi-agent reasoning using **LangGraph**. It models the complex interactions between various market participants (Buyers, Sellers, Landlords, Tenants) and external factors (Government Policy, Monetary Policy). This plane is designed to simulate realistic market reactions to shifting economic conditions.

### 4.1 State Schema
The `SimulationState` (TypedDict) strictly defines the information passed between nodes. This structured approach avoids the "black box" nature of free-form message lists and ensures that agents have access to only the information relevant to their current task, reducing the risk of context-leaking or reasoning errors (ADR-004):

- **`run_meta`**: Metadata for the simulation run, including unique identifiers, execution timestamps, and simulation name.
- **`snapshot`**: A reference to the specific `dataset_snapshot_id` being used as the simulation's ground truth, ensuring data-reasoning alignment.
- **`scenario`**: Parameters defining the simulation's initial conditions (e.g., "A 1% increase in interest rate coupled with a new property tax regulation").
- **`round_no`**: The current round of the simulation, hard-bounded to a maximum of 8 rounds to ensure termination, predictable costs, and timely delivery of results.
- **`world`**: A `dict[str, SegmentState]` representing the evolving state of different sub-markets (e.g., Gangnam-gu, Nowon-gu).
- **`participants`**: A `dict[str, ParticipantState]` that tracks the state (capital, holdings, sentiment) of various simulated actors throughout the rounds.
- **`governance_actions` / `market_actions`**: Logs of structured action proposals submitted by agents during the simulation, used for historical auditing.
- **`last_outcome`**: The result of the previous round's deterministic engine execution, including cleared volume and price movements.
- **`event_refs` / `evidence_refs`**: Pointers to specific data points or historical events in the snapshot that justify agent decisions, critical for the citation gate.
- **`report_claims`**: A list of structured `ReportClaim` objects generated by the reasoning agents for the final report generation phase.
- **`warnings`**: A collection of non-fatal warnings or data anomalies detected during the run that may impact the interpretation of results.

### 4.2 Graph Topology
The graph combines LLM-based reasoning nodes with deterministic execution nodes to maintain a balance between intelligent behavior and predictable market logic. This hybrid approach ensures that while agents can reason creatively, the market mechanics remain bound by the rules of supply and demand:

```text
START 
  |
  v
intake_planner (LLM: Analyzes user goals and defines simulation scope)
  |
  v
snapshot_resolver (det: Loads the pinned immutable snapshot)
  |
  v
scenario_builder (LLM: Translates high-level goals into concrete parameters)
  |
  v
init_world (det: Populates the initial state from the Gold data)
  |
  v
round_router <-------------------------------------------------------+
  |                                                                  |
  +--> [policy_agent, bank_agent] (LLM: Agents propose new           |
  |      regulations or interest rate adjustments based on state)    |
  |      |                                                           |
  |      v                                                           |
  |    apply_governance (det: Updates the world state with policies) |
  |      |                                                           |
  |      v                                                           |
  |    [buyer, investor, tenant, landlord, broker] (LLM: Agents      |
  |      | propose market actions like Buy/Sell/Rent/Hold)           |
  |      v                                                           |
  |    market_engine (det: Resolves market actions, calculates       |
  |      | volume and price changes using a deterministic formula)   |
  |      v                                                           |
  |    round_summarizer (det: Prepares the state for the next round)  |
  |      |                                                           |
  +------+-----------------------------------------------------------+
  |
  v
finalize (det: Aggregates all simulation logs and history)
  |
  v
report_writer_json_first (LLM: Phase 1 - Generates factual claims)
  |
  v
citation_gate (det: Phase 2 - Validates claims against the snapshot)
  |
  v
repair_loop (LLM: Optional - Fixes rejected claims, max 2 iterations)
  |
  v
final_renderer (det: Phase 3 - Renders prose from validated claims)
  |
  v
END
```

### 4.3 Agent Patterns and Constraints
- **Structured Action Proposals**: Every agent node must output a structured `ActionProposal` object rather than free text. This allows the deterministic engines to parse intentions without LLM assistance, ensuring high reliability in action resolution.
- **No `add_messages`**: To prevent state explosion, context window saturation, and high latency, the system does not use the standard LangChain message list pattern. State is updated explicitly and predictably.
- **External Trace Store**: Full LLM prompts and responses are written to an external JSONL store. The LangGraph state only keeps high-level summaries and structured results, making it lightweight and easy to checkpoint.
- **Bounded Rounds**: Multi-step reasoning is strictly bounded (max 8 rounds) to prevent infinite loops and ensure that simulations complete within a predictable timeframe and budget.

## 5. Evidence-Gated Reporting Pipeline
To eliminate hallucinations in generated reports, Younggeul implements a three-phase pipeline (ADR-005) that separates factual reasoning from linguistic expression. This structural decoupling ensures that every word in the final output can be traced back to verified data points.

1.  **Phase 1: JSON-First Claims**: The `report_writer` identifies key findings from the simulation and data plane. Instead of writing natural language prose, it generates a list of `ReportClaim` objects. Each claim contains a `claim_json` (a schema-enforced factual assertion, e.g., `{"price_trend": "increasing", "median_price": 1200000000, "district": "Gangnam"}`) and `evidence_ids` (specific identifiers for the data rows or simulation events that support the claim).
2.  **Phase 2: Deterministic Citation Gate**: A non-LLM validation node iterates through the generated claims. It performs a rigid check:
    - Verifies that all cited `evidence_ids` actually exist in the immutable `dataset_snapshot_id`.
    - Mathematically validates that the values in the `claim_json` match the evidence within a strictly defined tolerance (e.g., +/- 1%).
    - Claims that pass are marked "Validated"; those that fail are sent to the `repair_loop`.
3.  **Phase 3: Final Rendering**: Only the collection of validated JSON claims is passed to the `final_renderer`. This node is strictly a "linguistic translator" that converts the structured data into natural-sounding Korean prose. It is explicitly forbidden from adding any factual information not present in the validated claims.

### 5.1 Repair and Feedback Loop
Claims that fail the citation gate are not immediately discarded. They enter a **Repair Loop** where a "Critic" agent analyzes the failure (e.g., "The claim says 1.5B, but the evidence shows 1.48B") and attempts to correct the `claim_json`. This loop is limited to a maximum of 2 iterations to ensure efficiency. Claims that remain invalid after the repair loop are dropped from the final report to maintain 100% factual accuracy.

## 6. Evaluation Plane
The Evaluation Plane provides a rigorous framework for measuring the system's accuracy against historical data and expert-curated benchmarks. This enables continuous improvement of the simulation models and agent prompts.

- **Tooling**: Utilizes `promptfoo` for high-throughput, automated benchmark execution and comparison across different model versions.
- **Datasets**: Golden datasets are meticulously curated and stored in `benchmarks/kr-housing/`. These represent historical market periods (e.g., the 2021 price surge, the 2023 stabilization) with known outcomes.
- **Metrics**: 
  - **Directional Accuracy**: The percentage of times the system correctly predicted the direction (Up/Down/Stable) of price movement within a given district.
  - **Citation Coverage**: The percentage of generated claims that successfully pass the citation gate, measuring the "groundedness" of the reporting.
  - **RMSE (Root Mean Square Error)**: Measures the statistical deviation of predicted trading volumes and prices from actual historical volumes.
  - **Hallucination Rate**: Monitored as the inverse of Citation Coverage, specifically tracking claims that fail validation despite repair attempts.
- **Pinning**: All evaluation runs are strictly pinned to a specific `dataset_snapshot_id` to ensure that improvements in the agents can be measured independently of changes in the data distribution.

## 7. Infrastructure & CI/CD
The project leverages modern DevOps practices and a robust CI/CD infrastructure to ensure code quality, reliable data delivery, and scalable simulation execution.

### 7.1 GitHub Actions Workflows
Automated workflows are categorized into three main areas:
- **Quality Assurance**:
  - `lint`: Performs static analysis and code style enforcement using `ruff` and `mypy` (with strict mode enabled for the core components).
  - `test`: Executes unit and integration tests using `pytest` against synthetic fixtures to maintain 100% logic coverage without relying on real data.
- **Data Operations**:
  - `data-pipeline`: A scheduled workflow that performs periodic ingestion of new public data, performs Silver/Gold transformations, and generates updated immutable snapshots.
- **Simulation and Deployment**:
  - `simulation`: A manual workflow (via `workflow_dispatch`) that allows developers to run complex, high-resource scenarios on specialized hardware with manual approval gates.
  - `release`: Automates the versioning and publication of the `younggeul-core` and app packages to PyPI upon successful completion of all tests.

### 7.2 Execution and Observability
- **Stub Workflows**: The project includes stubbed workflows for `nightly-eval` (scheduled benchmarking), `codeql` (security vulnerability scanning), and `deploy-docs` (automated publishing of the TDD and API reference).
- **Inference Infrastructure**: Simulations requiring high-throughput LLM inference utilize self-hosted runners equipped with GPUs. This provides consistent performance and manages the operational costs of local model serving.
- **Observability Stack**:
  - **OpenTelemetry**: Integrated throughout the system to provide full-stack tracing. Every agent decision, market engine resolution, and reporting phase is traceable for debugging and audit purposes.
  - **LiteLLM**: Acts as a unified, load-balanced gateway to multiple cloud LLM providers, providing fallback and cost-tracking capabilities.
  - **vLLM**: Utilized for efficient local model serving, allowing for faster development cycles and reduced reliance on external APIs.

## 8. Tech Stack Summary
- **Language**: Python 3.12+ (Utilizing modern features like type hints, structural pattern matching, and native `asyncio` for concurrent agent execution).
- **Build & Packaging**: `hatchling` for building standardized wheel and sdist packages; `uv` for ultra-fast, deterministic dependency resolution and environment management.
- **Agent Orchestration**: `LangGraph` for managing complex agent state transitions, cyclic workflows, and persistent simulation checkpoints.
- **Schema Enforcement**: `Pydantic v2` for strict, high-performance data validation at every layer of the Data and Simulation planes.
- **Inference Engines**: `vLLM` (Local inference optimization) and `LiteLLM` (Unified provider management and monitoring).
- **Observability & Tracing**: `OpenTelemetry` SDKs for structured logging and trace export to collectors.
- **Benchmarking & Evaluation**: `promptfoo` for systematic testing of prompts and model outputs.
- **Quality Tools**: `ruff` (extremely fast linting and formatting), `mypy` (rigorous static type checking), `pytest` (comprehensive test runner).

## 9. Key Design Decisions (ADR Summary)
The following Architectural Decision Records govern the project's development and maintain its architectural integrity:
- **ADR-001: Clean-room development**: Ensures all project artifacts are original and correctly licensed under the Apache-2.0 license, preventing IP contamination.
- **ADR-002: Monorepo structure**: Defines clear boundaries between core platform logic, regional applications, and evaluation benchmarks to maximize modularity.
- **ADR-003: Immutable dataset snapshots**: Implements SHA-256 content-based addressing for all data artifacts to guarantee perfect reproducibility of simulation results.
- **ADR-004: Typed state management**: Enforces structured state transitions in LangGraph without using free-form message lists, ensuring predictable and debuggable agent behavior.
- **ADR-005: Evidence-gated reporting**: Introduces a three-phase pipeline (Claims → Validation → Prose) to mathematically eliminate LLM hallucinations from final reports.
- **ADR-006: Public data policy**: Prohibits the storage of raw government data in git, utilizing SHA-256 manifests for integrity and synthetic fixtures for local testing.

## 10. Data Model Summary
Key Pydantic models that define the communication protocols between different system components:
- **`Bronze/Silver/Gold Schemas`**: Define the structure of data as it flows through the transformation pipeline, ensuring consistency across disparate data sources.
- **`SimulationState`**: The master state object that tracks the evolution of the simulation, including world state, participant sentiment, and action history.
- **`ReportClaim`**: A structured container for factual assertions and their supporting evidence links, used to verify reports against the ground truth.
- **`ActionProposal`**: A polymorphic model representing various agent intentions (e.g., `MarketAction`, `PolicyAction`), enabling deterministic resolution by the market engine.
- **`SnapshotManifest`**: The JSON schema that defines the metadata, provenance, and integrity hashes of an immutable dataset snapshot.

## 11. Security & Compliance
The project maintains high standards for security, data privacy, and legal compliance to foster a trustable open-source ecosystem.

### 11.1 Data and Credential Security
- **Secrets Management**: API keys for government portals and LLM providers are never committed to code; they are managed exclusively through environment variables and GitHub Secrets.
- **Data Privacy**: The system is designed to handle only aggregate-level data (e.g., district-level medians). No PII (Personally Identifiable Information) is allowed in the repository, synthetic datasets, or simulation logs.

### 11.2 Legal and Licensing
- **Licensing**: All original work is published under the **Apache License 2.0**, encouraging broad adoption and commercial use without restrictive copyleft requirements.
- **Clean-Room Compliance**: Strict adherence to the clean-room protocol (ADR-001) ensures that the project is free from intellectual property contamination from previous projects. All prompts, code, and architectural designs are developed from scratch based on original requirements.
- **Data ToS**: By requiring users to provide their own API keys, Younggeul ensures compliance with the Terms of Service of various South Korean public data providers.
