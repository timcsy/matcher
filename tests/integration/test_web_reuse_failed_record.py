"""Feature 021 #3：配對失敗也存清單快照，「用這份清單再配對」對失敗紀錄也可用。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.web.app import create_app
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _failed_record_with_snapshot(rid: str) -> MatchRecord:
    return MatchRecord(
        schema_version=SCHEMA_VERSION, id=rid, created_at="2026-05-27T00:00:00+00:00",
        template_id="teacher-class", seed=1, input_file=None, mechanism="M0",
        status="failed", audit=None,
        error={"type": "QualifiedSetEmpty", "exit_code": 10, "message": "x"},
        owner="test@example.com",
        roster_snapshot={
            "participants": [{"id": "T01", "attributes": {"name": "王", "speciality": "國文"}, "preferences": []}],
            "targets": [{"id": "C01", "capacity": 2, "attributes": {"name": "三甲", "required_subjects": ["國文"], "feature": "雙語"}}],
        },
    )


def test_failed_record_shows_reuse_link(client, tmp_path):
    MatchStore().save(_failed_record_with_snapshot("2026-05-27T00-00-00-failrec1"))
    body = client.get("/matches").text
    assert "用這份清單再配對" in body
    assert "from_record=2026-05-27T00-00-00-failrec1" in body


def test_reuse_failed_record_prefills_fill_form(client, tmp_path):
    MatchStore().save(_failed_record_with_snapshot("2026-05-27T00-00-00-failrec2"))
    r = client.get("/match/new/fill?template_id=teacher-class&from_record=2026-05-27T00-00-00-failrec2")
    assert r.status_code == 200
    assert "王" in r.text and "三甲" in r.text
    assert "上次失敗" in r.text  # 失敗紀錄專屬提示


def test_reuse_failed_record_without_snapshot_400(client, tmp_path):
    rec = _failed_record_with_snapshot("2026-05-27T00-00-00-failrec3")
    rec.roster_snapshot = None
    MatchStore().save(rec)
    r = client.get("/match/new/fill?template_id=teacher-class&from_record=2026-05-27T00-00-00-failrec3")
    assert r.status_code == 400
