"""MatchStore 單元測試。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from matcher.web.errors import MatchRecordNotFound
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION


def _make_record(record_id: str, status: str = "success") -> MatchRecord:
    return MatchRecord(
        schema_version=SCHEMA_VERSION,
        id=record_id,
        created_at="2026-05-22T10:00:00+00:00",
        template_id="teacher-class",
        seed=1,
        input_file="x.csv",
        mechanism="M0",
        status=status,
        audit={"foo": "bar"} if status == "success" else None,
        error={"type": "X", "exit_code": 99, "message": "..."} if status == "failed" else None,
    )


def test_save_and_get(tmp_path: Path):
    store = MatchStore(base_dir=tmp_path)
    rec = _make_record("test-001")
    rid = store.save(rec)
    assert rid == "test-001"
    loaded = store.get("test-001")
    assert loaded.id == "test-001"
    assert loaded.audit == {"foo": "bar"}


def test_get_not_found(tmp_path: Path):
    store = MatchStore(base_dir=tmp_path)
    with pytest.raises(MatchRecordNotFound):
        store.get("no-such")


def test_list_descending(tmp_path: Path):
    store = MatchStore(base_dir=tmp_path)
    store.save(_make_record("2026-01-01T00-00-00-aaaaaaaa"))
    time.sleep(0.01)
    store.save(_make_record("2026-02-01T00-00-00-bbbbbbbb"))
    time.sleep(0.01)
    store.save(_make_record("2026-03-01T00-00-00-cccccccc"))
    records = store.list()
    assert len(records) == 3
    # 依檔名（時間戳）遞減
    assert records[0].id.startswith("2026-03")
    assert records[2].id.startswith("2026-01")


def test_list_respects_limit(tmp_path: Path):
    store = MatchStore(base_dir=tmp_path)
    for i in range(10):
        store.save(_make_record(f"2026-0{i}-01T00-00-00-{'a'*8}"))
    records = store.list(limit=3)
    assert len(records) == 3


def test_failed_record_roundtrip(tmp_path: Path):
    store = MatchStore(base_dir=tmp_path)
    rec = _make_record("failed-001", status="failed")
    store.save(rec)
    loaded = store.get("failed-001")
    assert loaded.status == "failed"
    assert loaded.error["exit_code"] == 99
    assert loaded.audit is None


def test_save_is_atomic(tmp_path: Path):
    """寫入完成後不應留下 .tmp 檔。"""
    store = MatchStore(base_dir=tmp_path)
    store.save(_make_record("atomic-001"))
    assert (tmp_path / "atomic-001.json").exists()
    assert not (tmp_path / "atomic-001.json.tmp").exists()
