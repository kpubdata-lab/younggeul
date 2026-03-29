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

In addition, data publication policy must align with snapshot reproducibility (ADR-003) and benchmark transparency without leaking provider-restricted artifacts. Contributors need a predictable workflow where code and manifests are versioned in git, but high-volume or policy-sensitive payloads remain external. This keeps onboarding clear while preserving legal and operational boundaries.

Another practical constraint is contributor ergonomics: accidental large-file commits should be rare and quickly detectable. The policy must therefore be enforceable using default repository behavior (`.gitignore`) plus explicit CLI workflows, not tribal knowledge. This reduces maintenance load as the contributor base grows.

## Decision
We will enforce a strict **Public Data Publication Policy** for the Younggeul project.

1.  **No Raw Data in Git**: All files in the Bronze, Silver, and Gold data layers are explicitly added to `.gitignore`. No raw API responses or large CSV/Parquet files from these layers may be committed to the repository.
2.  **Manifests Only**: Only metadata and manifest files (JSON files describing the data's schema, source URL, and expected hash) should be committed. This allows the system to verify the data's integrity without storing the data itself.
3.  **Derived Artifacts for Snapshots**: While raw data is ignored, the resulting "Gold" level artifacts used in snapshots (ADR-003) may be published to external storage (e.g., S3, Hugging Face Datasets) rather than being stored in git.
4.  **Synthetic Test Fixtures**: All unit and integration tests must use small, hand-crafted synthetic datasets (test fixtures) rather than subsets of real API data. These fixtures must be small enough to be committed to git and must contain no PII (Personally Identifiable Information).
5.  **User-Driven Ingestion**: The data collection pipeline must be designed so that users provide their own API keys (from 공공데이터포털) and run the ingestion process themselves on their local machines or in their own infrastructure.
6.  **CI/CD Isolation**: CI/CD pipelines will primarily use synthetic fixtures for testing. A separate, scheduled workflow (using GitHub Secrets for API keys) may run a full data ingestion and snapshot generation process to verify the end-to-end pipeline.

## Alternatives Considered
### A) Commit data directly to git (possibly with LFS)
- **Pros**
  - Easy cloning of code + data in one step.
  - Reproducibility appears straightforward for small datasets.
- **Cons**
  - Large storage and bandwidth overhead.
  - Potential ToS/policy violations through redistribution.
  - Git history becomes heavy and hard to maintain.

### B) Host all data on an external CDN maintained by project
- **Pros**
  - Keeps repository size small.
  - Centralized distribution endpoint.
- **Cons**
  - Shifts legal/compliance burden to maintainers.
  - Requires ongoing ops budget and governance.
  - Risk of accidental redistribution beyond provider terms.

### C) User-driven ingestion + manifest-only git strategy (Selected)
- **Pros**
  - Better ToS alignment and legal safety.
  - Small, fast repository for contributors and CI.
  - Compatible with immutable snapshot verification.
- **Cons**
  - Higher onboarding effort for first-time users.
  - Requires clear CLI documentation and integrity checks.

## Rationale
The selected policy minimizes legal exposure while preserving reproducibility guarantees through manifests and snapshot IDs rather than raw payload storage. It aligns with the project’s architecture: deterministic pipelines, manifest-based snapshot integrity, and synthetic fixtures for CI.

A central hosted-dataset approach would simplify setup but creates continuous operational and legal liability for maintainers. Committing raw datasets into git (even via LFS) introduces long-term repository drag and weakens compliance controls.

By separating “code + metadata” from “user-acquired data,” Younggeul remains lightweight and portable while still enabling verifiable data provenance.

This also keeps test and documentation pipelines predictable: CI can run on synthetic fixtures while production-like ingestion remains opt-in for users with their own credentials and infrastructure. The result is a cleaner boundary between open-source code distribution and data access responsibilities.

## Examples
### 1) Actual `.gitignore` data exclusion rules

```gitignore
# Data artifacts
data/bronze/**
data/silver/**
data/gold/**
data/snapshots/**
!data/.gitkeep
eval_results/
demo_output/
```

These patterns enforce that raw and derived data artifacts are not committed by default.

### 2) CLI ingestion and snapshot publication commands

```bash
younggeul ingest --output-dir ./output/pipeline
younggeul snapshot publish --data-dir ./output/pipeline --snapshot-dir ./output/snapshots
younggeul snapshot list --snapshot-dir ./output/snapshots
```

The command wiring is implemented in `apps/kr-seoul-apartment/src/younggeul_app_kr_seoul_apartment/cli.py` via `ingest`, `snapshot publish`, and `snapshot list` subcommands.

Command declarations in the codebase:

```python
@main.command("ingest")
def ingest_command(...):
    ...

@snapshot_group.command("publish")
def snapshot_publish_command(...):
    ...
```

### 3) Manifest-only commit pattern

```text
git add docs/adr/006-public-data-policy.md
git add output/snapshots/<dataset_snapshot_id>/manifest.json
# Do NOT add snapshot table payload files or data/bronze|silver|gold directories
```

This preserves provenance (`dataset_snapshot_id`, table hashes, record counts) without storing provider-distributed raw datasets in git.

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
