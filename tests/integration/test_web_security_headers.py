"""Feature 017：安全標頭 + owner=None 拒絕 + 路徑遍歷的整合測試。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.web.app import create_app
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION


@pytest.fixture
def tmp_store(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return tmp_path


@pytest.fixture
def client(tmp_store):
    return TestClient(create_app())


def test_security_headers_present(client):
    r = client.get("/match/new")
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "same-origin"


def test_csp_restricts_script_sources_and_framing():
    # CSP 主要保護：限制外部 script 來源主機 + 防點擊劫持
    from matcher.web.app import _CSP
    script_src = _CSP.split("script-src")[1].split(";")[0]
    # 只允許本專案實際用到的 CDN，未知主機被擋
    assert "https://cdn.jsdelivr.net" in script_src
    assert "https://evil.example" not in script_src
    assert "frame-ancestors 'none'" in _CSP
    assert "object-src 'none'" in _CSP


def _make_record(rid: str, owner) -> MatchRecord:
    return MatchRecord(
        schema_version=SCHEMA_VERSION, id=rid, created_at="2026-05-27T00:00:00+00:00",
        template_id="teacher-class", seed=1, input_file=None, mechanism="M0",
        status="failed", audit=None, error={"type": "X", "message": "m"}, owner=owner,
    )


def test_ownerless_record_denied(client, tmp_store):
    # owner=None 的舊紀錄不對任何登入者開放（安全預設）
    MatchStore().save(_make_record("2026-05-27T00-00-00-deadbeef", None))
    r = client.get("/match/2026-05-27T00-00-00-deadbeef")
    assert r.status_code == 403


def test_own_record_visible(client, tmp_store):
    # auto-login 的 test@example.com 擁有的紀錄可看
    MatchStore().save(_make_record("2026-05-27T00-00-00-cafebabe", "test@example.com"))
    r = client.get("/match/2026-05-27T00-00-00-cafebabe")
    assert r.status_code == 200


def test_path_traversal_record_id(client):
    # 夾帶 ../ 的 record id → 視為找不到（404），不讀到任意檔
    r = client.get("/match/..%2f..%2f..%2fetc%2fpasswd")
    assert r.status_code in (404, 400)
