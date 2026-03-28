# ADR-001: Clean-Room Development and Licensing

## Status
Accepted

## Date
2026-03-28

## Context
The Younggeul project aims to provide a robust open-source platform for real estate analysis and simulation. A previous internal project, MiroFish, addressed similar domains but was developed with a tight coupling to Zep Cloud and OASIS. Crucially, MiroFish was licensed under the AGPL-3.0 (Affero General Public License), which imposes significant restrictions on commercial redistribution and integration into proprietary SaaS offerings.

To maximize adoption, encourage commercial compatibility, and foster a broad ecosystem of contributors, Younggeul must be licensed under the Apache License 2.0. However, the existence of MiroFish creates a risk of "licensing contamination" if any code, architectural patterns, or specific LLM prompts are carried over from the AGPL-licensed codebase.

## Decision
We will implement a strict **Clean-Room Development** process for Younggeul.

1.  **License Selection**: The project will be licensed under the **Apache License 2.0**. All new files must include the appropriate header.
2.  **Zero Inheritance**: No code, documentation, or internal architectural diagrams from the MiroFish project (or any other AGPL project) may be copied, referenced, or used as a template for Younggeul.
3.  **Prompt Engineering**: All LLM prompts used for reasoning, extraction, and reporting must be written from scratch. Even if the functional goal is identical to a MiroFish prompt, the implementation must be original.
4.  **Independent Implementation**: The core engine, data pipelines (Bronze/Silver/Gold), and agent orchestration must be designed based on the requirements of Younggeul without looking at the MiroFish implementation details.
5.  **Clean Dependency Graph**: Younggeul will not depend on Zep Cloud or OASIS in its core runtime, ensuring a portable and unencumbered codebase.

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
