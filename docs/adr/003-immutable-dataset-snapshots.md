# ADR-003: Immutable Dataset Snapshots

## Status
Accepted

## Date
2026-03-28

## Context
Younggeul simulations (e.g., forecasting ROI for Seoul apartments) must be reproducible. If the underlying data in our "Gold" tables (매매 실거래가, 전월세 등) changes between two simulation runs, comparing their results becomes impossible. Without a way to fix the dataset in time, we cannot perform meaningful A/B testing on prompt changes or architectural shifts.

Furthermore, auditing a simulation run requires knowing exactly what data the agent saw at that moment. A dynamic, ever-changing database makes such auditing impossible.

The system also needs deterministic identifiers for caching, report traceability, and reproducible benchmark baselines. When teams share runs, they must be able to verify that all tables and hashes match without manual reconciliation. This requires a manifest format with explicit table metadata, integrity checks, and a stable `dataset_snapshot_id` derivation rule.

## Decision
We will implement an **Immutable Dataset Snapshot** system for all simulation and evaluation runs.

1.  **Unique Identifier**: Every simulation run must reference an immutable `dataset_snapshot_id`. This ID is a deterministic SHA-256 hash derived from the collective hashes of all individual tables (Bronze/Silver/Gold) included in the snapshot.
2.  **Explicit Reference**: No simulation can proceed without an explicit snapshot reference. The configuration file for any run must specify the `dataset_snapshot_id`.
3.  **Storage Format**: Snapshots are stored as sets of versioned Parquet files accompanied by a JSON manifest. The manifest includes metadata about data sources, ingestion timestamps, and the specific table schema versions.
4.  **Deterministic Production**: Identical input data (raw files and processing scripts) must always produce an identical `dataset_snapshot_id`. This ensures that snapshots can be safely cached and distributed between team members.
5.  **Audit Trail**: The `dataset_snapshot_id` will be logged as part of every simulation's trace data, allowing us to recreate the exact environment of any historical run.

## Alternatives Considered
### A) Git-tracked data files
- **Pros**
  - Simple mental model: data versioned directly in git history.
  - Easy to inspect diffs for tiny datasets.
- **Cons**
  - Repository bloat for realistic real-estate data volumes.
  - Poor scalability for frequent updates.
  - Difficult to enforce strict run-time snapshot pinning semantics.

### B) Database with versioned tables
- **Pros**
  - Centralized data governance and query flexibility.
  - Potentially strong audit controls at DB layer.
- **Cons**
  - Higher operational cost and infrastructure dependency.
  - Harder local reproducibility for contributors.
  - Additional migration/versioning complexity across environments.

### C) Immutable snapshot manifests + content hashes (Selected)
- **Pros**
  - Deterministic identity and integrity checks.
  - Portable artifacts that can be moved across environments.
  - Clean linkage into simulation/report traces.
- **Cons**
  - Requires explicit publish/resolve workflow.
  - Storage lifecycle policy needed for older snapshots.

## Rationale
The selected approach balances determinism, portability, and operational simplicity. The core requirement is reproducibility across local runs, CI, and shared environments without relying on centralized mutable state. Hash-addressed snapshots directly satisfy this requirement.

The implementation in `core/src/younggeul_core/storage/snapshot.py` codifies strict schema validation (`dataset_snapshot_id` and `table_hash` must be lowercase 64-char SHA-256 hex) and integrity verification (`validate_integrity`). In app-level publishing (`apps/kr-seoul-apartment/.../snapshot.py`), table content is hashed, snapshot ID is computed deterministically, and a manifest is written with table metadata.

This gives an auditable chain from raw table bytes → table hash → ordered hash set → snapshot ID used by simulations and reports.

## Examples
### 1) Manifest schema and required fields (real implementation)

```python
# core/src/younggeul_core/storage/snapshot.py
class SnapshotManifest(BaseModel):
    dataset_snapshot_id: str
    created_at: datetime
    description: str | None = None
    table_entries: list[SnapshotTableEntry]
    source_ids: list[str] = Field(default_factory=list)
    ingestion_started_at: datetime | None = None
    ingestion_completed_at: datetime | None = None
```

`SnapshotTableEntry` includes:
- `table_name`
- `table_hash`
- `record_count`
- `schema_version`
- `source_uri` (optional)
- `file_format` (`"parquet" | "csv" | "jsonl"`)

### 2) Deterministic `dataset_snapshot_id` computation

```python
# core/src/younggeul_core/storage/snapshot.py
@classmethod
def compute_snapshot_id(cls, table_hashes: dict[str, str]) -> str:
    items = sorted(table_hashes.items(), key=lambda item: item[0])
    joined = "".join(f"{table_name}:{table_hash}" for table_name, table_hash in items)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
```

This guarantees ordering independence at input map level and stable output for the same table hash set.

### 3) Concrete publish flow and manifest output

```python
# apps/kr-seoul-apartment/src/.../snapshot.py
table_hash = hashlib.sha256(jsonl_content).hexdigest()
dataset_snapshot_id = SnapshotManifest.compute_snapshot_id({_TABLE_NAME: table_hash})

manifest = SnapshotManifest(
    dataset_snapshot_id=dataset_snapshot_id,
    created_at=created_at,
    table_entries=[
        SnapshotTableEntry(
            table_name=_TABLE_NAME,
            table_hash=table_hash,
            record_count=len(sorted_rows),
            schema_version="1.0.0",
            file_format="jsonl",
        )
    ],
)
```

The manifest is serialized to `manifest.json` in the snapshot directory and verified during `resolve_snapshot` before use.

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
