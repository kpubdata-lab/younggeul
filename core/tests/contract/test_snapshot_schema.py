from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from younggeul_core.storage import SnapshotManifest, SnapshotTableEntry


def _entry(table_name: str, table_hash: str, record_count: int) -> SnapshotTableEntry:
    return SnapshotTableEntry(
        table_name=table_name,
        table_hash=table_hash,
        record_count=record_count,
        schema_version="1.0.0",
        source_uri="s3://bucket/path",
    )


def _entries() -> list[SnapshotTableEntry]:
    return [
        _entry("gold_district_monthly_metrics", "a" * 64, 10),
        _entry("gold_apt_price_index", "b" * 64, 25),
    ]


def _manifest(entries: list[SnapshotTableEntry] | None = None, snapshot_id: str | None = None) -> SnapshotManifest:
    table_entries = entries if entries is not None else _entries()
    table_hashes = {entry.table_name: entry.table_hash for entry in table_entries}
    computed = SnapshotManifest.compute_snapshot_id(table_hashes)
    return SnapshotManifest(
        dataset_snapshot_id=snapshot_id if snapshot_id is not None else computed,
        created_at=datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
        description="Daily snapshot",
        table_entries=table_entries,
        source_ids=["data_go_kr_apt_trade", "data_go_kr_rent"],
        ingestion_started_at=datetime(2026, 3, 28, 11, 50, tzinfo=timezone.utc),
        ingestion_completed_at=datetime(2026, 3, 28, 11, 59, tzinfo=timezone.utc),
    )


def test_snapshot_table_entry_round_trip_valid_data() -> None:
    entry = _entry("gold_district_monthly_metrics", "c" * 64, 123)

    payload = entry.model_dump()
    round_tripped = SnapshotTableEntry.model_validate(payload)

    assert round_tripped == entry


def test_snapshot_table_entry_rejects_invalid_table_hash() -> None:
    with pytest.raises(ValidationError):
        _entry("gold_district_monthly_metrics", "not-a-sha", 1)


def test_snapshot_manifest_construction_with_multiple_entries() -> None:
    manifest = _manifest()

    assert len(manifest.table_entries) == 2
    assert manifest.total_records == 35


def test_snapshot_manifest_rejects_non_64_hex_dataset_snapshot_id() -> None:
    with pytest.raises(ValidationError):
        _manifest(snapshot_id="1234")


def test_snapshot_manifest_validate_integrity_true_for_correct_id() -> None:
    manifest = _manifest()

    assert manifest.validate_integrity() is True


def test_snapshot_manifest_validate_integrity_false_for_tampered_id() -> None:
    manifest = _manifest(snapshot_id="f" * 64)

    assert manifest.validate_integrity() is False


def test_compute_snapshot_id_is_deterministic_for_same_input() -> None:
    table_hashes = {
        "gold_b": "b" * 64,
        "gold_a": "a" * 64,
    }

    first = SnapshotManifest.compute_snapshot_id(table_hashes)
    second = SnapshotManifest.compute_snapshot_id(table_hashes)

    assert first == second


def test_compute_snapshot_id_changes_when_any_hash_changes() -> None:
    initial = {"gold_a": "a" * 64, "gold_b": "b" * 64}
    changed = {"gold_a": "a" * 64, "gold_b": "c" * 64}

    initial_id = SnapshotManifest.compute_snapshot_id(initial)
    changed_id = SnapshotManifest.compute_snapshot_id(changed)

    assert changed_id != initial_id


def test_get_table_returns_entry_when_present() -> None:
    manifest = _manifest()

    entry = manifest.get_table("gold_district_monthly_metrics")

    assert entry is not None
    assert entry.table_hash == "a" * 64


def test_get_table_returns_none_when_missing() -> None:
    manifest = _manifest()

    assert manifest.get_table("missing_table") is None


def test_table_hashes_and_record_counts_are_computed() -> None:
    manifest = _manifest()

    assert manifest.table_hashes == {
        "gold_district_monthly_metrics": "a" * 64,
        "gold_apt_price_index": "b" * 64,
    }
    assert manifest.record_counts == {
        "gold_district_monthly_metrics": 10,
        "gold_apt_price_index": 25,
    }


def test_snapshot_manifest_json_round_trip() -> None:
    manifest = _manifest()

    payload = manifest.model_dump_json()
    round_tripped = SnapshotManifest.model_validate_json(payload)

    assert round_tripped == manifest
    assert round_tripped.validate_integrity() is True


def test_snapshot_manifest_allows_empty_table_entries() -> None:
    manifest = _manifest(entries=[])

    assert manifest.table_entries == []
    assert manifest.table_hashes == {}
    assert manifest.record_counts == {}
    assert manifest.total_records == 0
    assert manifest.validate_integrity() is True
