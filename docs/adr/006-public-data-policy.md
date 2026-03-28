# ADR-006: Public Data Publication Policy

## Status
Accepted

## Date
2026-03-28

## Context
Younggeul relies heavily on public data provided by the South Korean government (e.g., 국토교통부 실거래가 공개시스템, 행정안전부 법정동코드). While this data is public, redistributing it in bulk through a git repository creates several problems:
1.  **ToS Compliance**: Some data providers have terms of service that prohibit redistribution or require users to obtain their own API keys.
2.  **Repo Bloat**: Real estate datasets can be several gigabytes in size, which is unsuitable for git storage.
3.  **Data Staleness**: Committing raw data makes it difficult to keep it up-to-date across all development environments.

## Decision
We will enforce a strict **Public Data Publication Policy** for the Younggeul project.

1.  **No Raw Data in Git**: All files in the Bronze, Silver, and Gold data layers are explicitly added to `.gitignore`. No raw API responses or large CSV/Parquet files from these layers may be committed to the repository.
2.  **Manifests Only**: Only metadata and manifest files (JSON files describing the data's schema, source URL, and expected hash) should be committed. This allows the system to verify the data's integrity without storing the data itself.
3.  **Derived Artifacts for Snapshots**: While raw data is ignored, the resulting "Gold" level artifacts used in snapshots (ADR-003) may be published to external storage (e.g., S3, Hugging Face Datasets) rather than being stored in git.
4.  **Synthetic Test Fixtures**: All unit and integration tests must use small, hand-crafted synthetic datasets (test fixtures) rather than subsets of real API data. These fixtures must be small enough to be committed to git and must contain no PII (Personally Identifiable Information).
5.  **User-Driven Ingestion**: The data collection pipeline must be designed so that users provide their own API keys (from 공공데이터포털) and run the ingestion process themselves on their local machines or in their own infrastructure.
6.  **CI/CD Isolation**: CI/CD pipelines will primarily use synthetic fixtures for testing. A separate, scheduled workflow (using GitHub Secrets for API keys) may run a full data ingestion and snapshot generation process to verify the end-to-end pipeline.

## Consequences
### Positive
- **Legal Compliance**: We avoid potential violations of government data terms of service by requiring users to obtain their own access credentials.
- **Repository Performance**: Keeping large binary data out of git ensures that the repository remains small and fast to clone and branch.
- **Improved Testing**: Synthetic fixtures allow for more targeted testing of edge cases (e.g., negative prices, missing fields) that might not appear in real-world data samples.

### Negative
- **Onboarding Friction**: New developers and users must set up their own API keys and run the ingestion process before they can see "real" results.
- **Infrastructure Overhead**: We need a robust mechanism for managing and distributing immutable snapshots (ADR-003) outside of the git repository.

### Neutral
- **Consistency Verification**: We will need automated checks to ensure that no developer accidentally commits a large data file to the repository.

## References
- ADR-003: Immutable Dataset Snapshots
