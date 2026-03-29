# ADR-001: Clean-Room Development and Licensing

## Status
Accepted

## Date
2026-03-28

## Context
The Younggeul project aims to provide a robust open-source platform for real estate analysis and simulation. A previous internal project, MiroFish, addressed similar domains but was developed with a tight coupling to Zep Cloud and OASIS. Crucially, MiroFish was licensed under the AGPL-3.0 (Affero General Public License), which imposes significant restrictions on commercial redistribution and integration into proprietary SaaS offerings.

To maximize adoption, encourage commercial compatibility, and foster a broad ecosystem of contributors, Younggeul must be licensed under the Apache License 2.0. However, the existence of MiroFish creates a risk of "licensing contamination" if any code, architectural patterns, or specific LLM prompts are carried over from the AGPL-licensed codebase.

This risk is not only legal but also operational: once contamination is suspected, downstream adopters may avoid the project regardless of technical quality. The project also needs a clean provenance story for enterprise due diligence, including package audits and procurement reviews. Finally, architecture and prompts must be independently designed so that future governance decisions can rely on clearly documented original authorship.

## Decision
We will implement a strict **Clean-Room Development** process for Younggeul.

1.  **License Selection**: The project will be licensed under the **Apache License 2.0**. All new files must include the appropriate header.
2.  **Zero Inheritance**: No code, documentation, or internal architectural diagrams from the MiroFish project (or any other AGPL project) may be copied, referenced, or used as a template for Younggeul.
3.  **Prompt Engineering**: All LLM prompts used for reasoning, extraction, and reporting must be written from scratch. Even if the functional goal is identical to a MiroFish prompt, the implementation must be original.
4.  **Independent Implementation**: The core engine, data pipelines (Bronze/Silver/Gold), and agent orchestration must be designed based on the requirements of Younggeul without looking at the MiroFish implementation details.
5.  **Clean Dependency Graph**: Younggeul will not depend on Zep Cloud or OASIS in its core runtime, ensuring a portable and unencumbered codebase.

## Alternatives Considered
### A) Fork MiroFish and attempt relicensing
- **Pros**
  - Fastest path to a feature-complete baseline.
  - Existing battle-tested prompt and pipeline logic.
- **Cons**
  - AGPL inheritance would remain or require complex rights clearance.
  - High legal uncertainty for external adopters.
  - Strong risk of carrying over hidden coupling to Zep Cloud/OASIS.

### B) Dual-license with AGPL compatibility layer
- **Pros**
  - Could preserve some prior components while adding permissive wrappers.
  - Potentially less rewrite effort than full reimplementation.
- **Cons**
  - Core legal ambiguity remains for derivative components.
  - Operational complexity in separating boundaries of AGPL vs Apache code.
  - Difficult for contributors to reason about what is safe to modify or redistribute.

### C) Clean-room implementation from scratch (Selected)
- **Pros**
  - Strongest legal clarity and provenance.
  - Clean architecture reset without historical coupling constraints.
  - Simplifies enterprise adoption under Apache-2.0 expectations.
- **Cons**
  - Highest short-term implementation effort.
  - Requires systematic re-validation of old domain edge cases.

## Rationale
The selected clean-room strategy best aligns with the project’s adoption goals: broad open-source usage, commercial compatibility, and low-friction legal review. The primary design constraint is not only “can it work?” but “can every component be shown as independently authored and redistributable under Apache-2.0.”

A fork or compatibility-layer approach could reduce initial engineering cost, but both introduce legal and governance debt that compounds over time. In contrast, a clean-room process localizes cost at project inception and keeps long-term maintenance simpler.

The runtime architecture already reflects this decision:
- `core/` defines generic reusable mechanics.
- `apps/` provides market/domain implementations.
- `benchmarks/` evaluates behavior without changing legal boundaries.

This separation allows independent evolution while preserving licensing clarity and avoiding vendor lock-in dependencies.

## Examples
### 1) Required Apache-2.0 file header template
The project policy requires each new source file to include an Apache-2.0 notice header.

```python
# Copyright 2026 Younggeul Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
```

### 2) Dependency direction that avoids AGPL-coupled runtime components
Current repository layout and packaging show explicit separation:

```text
/data/GitHub/younggeul/
├── core/
├── apps/
│   └── kr-seoul-apartment/
└── benchmarks/
    └── kr-housing/
```

`pyproject.toml` wheel packages:

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "core/src/younggeul_core",
  "apps/kr-seoul-apartment/src/younggeul_app_kr_seoul_apartment",
]
```

`apps` importing from `core` (allowed direction):

```python
# apps/kr-seoul-apartment/src/younggeul_app_kr_seoul_apartment/cli.py
from younggeul_core.state.bronze import BronzeAptTransaction, BronzeInterestRate, BronzeMigration
from younggeul_core.state.gold import GoldDistrictMonthlyMetrics
from younggeul_core.state.simulation import SnapshotRef
```

These examples demonstrate a clean core-first dependency graph (`core -> apps -> benchmarks` usage pattern) and no runtime dependency on Zep Cloud/OASIS.

## Consequences
### Positive
- **Commercial Compatibility**: The Apache-2.0 license allows companies to use and extend Younggeul without the "copyleft" requirements of AGPL, making it attractive for enterprise use cases.
- **Legal Certainty**: By following a clean-room approach, we eliminate the risk of copyright infringement or licensing disputes related to the MiroFish codebase.
- **Improved Architecture**: Starting from scratch allows us to learn from past mistakes and design a more modern system using LangGraph and deterministic data planes without legacy baggage.

### Negative
- **Increased Effort**: We cannot "save time" by copying existing utility functions or proven prompts. Everything must be re-engineered, re-tested, and re-validated.
- **Loss of Specific Knowledge**: Subtle edge cases discovered during MiroFish development that were baked into its code might be missed initially in Younggeul and must be rediscovered through rigorous testing.

### Neutral
- **Documentation Overhead**: We must clearly document the origin of our designs to demonstrate independent creation if ever challenged.

## References
- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- ADR-002: Monorepo Structure and Package Boundaries
