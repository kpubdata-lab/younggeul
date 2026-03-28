# ADR-003: Immutable Dataset Snapshots

## Status
Accepted

## Date
2026-03-28

## Context
Younggeul simulations (e.g., forecasting ROI for Seoul apartments) must be reproducible. If the underlying data in our "Gold" tables (매매 실거래가, 전월세 등) changes between two simulation runs, comparing their results becomes impossible. Without a way to fix the dataset in time, we cannot perform meaningful A/B testing on prompt changes or architectural shifts.

Furthermore, auditing a simulation run requires knowing exactly what data the agent saw at that moment. A dynamic, ever-changing database makes such auditing impossible.

## Decision
We will implement an **Immutable Dataset Snapshot** system for all simulation and evaluation runs.

1.  **Unique Identifier**: Every simulation run must reference an immutable `dataset_snapshot_id`. This ID is a deterministic SHA-256 hash derived from the collective hashes of all individual tables (Bronze/Silver/Gold) included in the snapshot.
2.  **Explicit Reference**: No simulation can proceed without an explicit snapshot reference. The configuration file for any run must specify the `dataset_snapshot_id`.
3.  **Storage Format**: Snapshots are stored as sets of versioned Parquet files accompanied by a JSON manifest. The manifest includes metadata about data sources, ingestion timestamps, and the specific table schema versions.
4.  **Deterministic Production**: Identical input data (raw files and processing scripts) must always produce an identical `dataset_snapshot_id`. This ensures that snapshots can be safely cached and distributed between team members.
5.  **Audit Trail**: The `dataset_snapshot_id` will be logged as part of every simulation's trace data, allowing us to recreate the exact environment of any historical run.

## Consequences
### Positive
- **Perfect Reproducibility**: We can rerun any simulation from months ago and get the same result, assuming the code and model remain the same.
- **Efficient Caching**: Since snapshots are immutable and identifiable by hash, we can cache them on CI/CD runners or local development machines without worrying about cache invalidation.
- **Auditable Evidence**: When the system generates a report claim (ADR-005), the cited evidence is pinned to a specific, immutable version of the data.

### Negative
- **Storage Overhead**: Each snapshot is an immutable copy of the data (though Parquet compression helps). Frequent snapshots of very large datasets could lead to significant storage costs.
- **Publication Requirement**: A snapshot must be explicitly generated and published before it can be used in a simulation, adding an extra step to the developer workflow.

### Neutral
- **Cleanup Strategy**: We will need a policy for purging old snapshots that are no longer referenced by active simulations or benchmarks to manage storage growth.

## References
- ADR-004: LangGraph Usage Boundaries
- ADR-006: Public Data Publication Policy
