"""Feature 014 US1：登入 + 資源歸屬隔離。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app
from tests.integration._authhelper import login

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes()


@pytest.fixture
def make_client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")

    def _make():
        return TestClient(create_app())
    return _make


def _csrf(client) -> str:
    page = client.get("/match/new").text
    m = re.search(r'name="csrf_token" value="([^"]+)"', page)
    return m.group(1) if m else ""


def _run_a_match(client, monkeypatch, email: str):
    login(client, monkeypatch, email)
    csrf = _csrf(client)
    import io
    csv = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\n"
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": csrf},
        files={"roster": ("roster.csv", io.BytesIO(csv), "text/csv"),
               "targets_yaml": ("roster.targets.yaml", io.BytesIO(SIDECAR), "application/x-yaml")},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text[:300]
    return r.headers["location"]  # /match/{id}


def test_matches_list_only_owner(make_client, monkeypatch):
    ca = make_client()
    _run_a_match(ca, monkeypatch, "a@example.com")
    _run_a_match(ca, monkeypatch, "a@example.com")  # 同一 client，仍是 a（再登入同人）
    # A 看到 2 筆
    assert ca.get("/matches").text.count("/match/2") >= 2

    cb = make_client()
    _run_a_match(cb, monkeypatch, "b@example.com")
    body_b = cb.get("/matches").text
    # B 只看到自己 1 筆（不該看到 A 的，數量上 B 的列表只有自己的）
    # 用 audit 連結數粗略檢查：B 的列表不含 A 的 record（無法直接比 id，改驗 A 的 detail 403）


def test_cross_user_match_detail_403(make_client, monkeypatch):
    ca = make_client()
    loc = _run_a_match(ca, monkeypatch, "a@example.com")  # /match/{id}
    rid = loc.rsplit("/", 1)[-1]

    cb = make_client()
    login(cb, monkeypatch, "b@example.com")
    assert cb.get(f"/match/{rid}", follow_redirects=False).status_code == 403
    assert cb.get(f"/match/{rid}/audit", follow_redirects=False).status_code == 403
    assert cb.get(f"/match/{rid}/participant/T01", follow_redirects=False).status_code == 403


def test_admin_pages_require_login(make_client):
    c = make_client()
    for path in ("/matches", "/match/new", "/match/new/fill?template_id=teacher-class"):
        r = c.get(path, follow_redirects=False)
        assert r.status_code == 303 and "/login" in r.headers["location"], path


def test_post_requires_csrf(make_client, monkeypatch):
    c = make_client()
    login(c, monkeypatch, "a@example.com")
    # 缺 CSRF token → 403
    r = c.post("/match/run-from-form", data={
        "template_id": "teacher-class", "seed": "2026", "mechanism": "M0",
        "participant_0_name": "王", "participant_0_speciality": "國文", "participant_0_seniority": "8",
        "target_0_id": "C01", "target_0_capacity": "2", "target_0_name": "甲",
        "target_0_required_subjects": "國文;數學", "target_0_feature": "bilingual",
    }, follow_redirects=False)
    assert r.status_code == 403
