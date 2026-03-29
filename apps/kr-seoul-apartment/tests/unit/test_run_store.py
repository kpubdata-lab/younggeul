from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from younggeul_app_kr_seoul_apartment.web.run_store import RunMeta, RunStore


def test_create_run_creates_directory_and_meta_json(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)

    run_id = store.create_run("강남구 시뮬레이션")

    run_dir = tmp_path / run_id
    meta_path = run_dir / "meta.json"
    assert run_dir.is_dir()
    assert meta_path.is_file()

    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == run_id
    assert payload["query"] == "강남구 시뮬레이션"
    assert payload["status"] == "pending"


def test_update_status_changes_status(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)
    run_id = store.create_run("test")

    store.update_status(run_id, "running")

    run_meta = store.get_run(run_id)
    assert run_meta is not None
    assert run_meta.status == "running"


def test_get_run_returns_run_meta(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)
    run_id = store.create_run("test")

    run_meta = store.get_run(run_id)

    assert isinstance(run_meta, RunMeta)
    assert run_meta.run_id == run_id


def test_get_run_returns_none_for_nonexistent(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)

    assert store.get_run("does-not-exist") is None


def test_list_runs_returns_sorted_by_created_at_desc(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)
    first_run_id = store.create_run("first")
    second_run_id = store.create_run("second")

    first_meta_path = tmp_path / first_run_id / "meta.json"
    second_meta_path = tmp_path / second_run_id / "meta.json"
    first_meta = RunMeta.model_validate_json(first_meta_path.read_text(encoding="utf-8"))
    second_meta = RunMeta.model_validate_json(second_meta_path.read_text(encoding="utf-8"))

    older = first_meta.model_copy(update={"created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    newer = second_meta.model_copy(update={"created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)})
    first_meta_path.write_text(json.dumps(older.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    second_meta_path.write_text(json.dumps(newer.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")

    runs = store.list_runs()

    assert [run.run_id for run in runs] == [second_run_id, first_run_id]


def test_update_status_with_report_writes_report_md(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)
    run_id = store.create_run("report")
    markdown_report = "# Simulation Report\n\n내용"

    store.update_status(run_id, "completed", report=markdown_report)

    report_path = tmp_path / run_id / "report.md"
    run_meta = store.get_run(run_id)
    assert report_path.is_file()
    assert report_path.read_text(encoding="utf-8") == markdown_report
    assert run_meta is not None
    assert run_meta.status == "completed"
    assert run_meta.completed_at is not None
