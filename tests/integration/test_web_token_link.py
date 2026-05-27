"""Feature 014 US2：token 個別連結（免登入、不可枚舉）。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app
from matcher.web.security import sign_participant_token
from tests.integration._authhelper import login

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes()


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def _run_match(client, monkeypatch) -> str:
    login(client, monkeypatch, "admin@example.com")
    page = client.get("/match/new").text
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    import io
    csv = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\nT02,\xe6\x9d\x8e,\xe6\x95\xb8\xe5\xad\xb8,5\n"
    r = client.post("/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": csrf},
        files={"roster": ("roster.csv", io.BytesIO(csv), "text/csv"),
               "targets_yaml": ("roster.targets.yaml", io.BytesIO(SIDECAR), "application/x-yaml")},
        follow_redirects=False)
    return r.headers["location"].rsplit("/", 1)[-1]


def test_result_page_shows_token_links(client, monkeypatch):
    rid = _run_match(client, monkeypatch)
    html = client.get(f"/match/{rid}").text
    assert "/r/" in html
    # 不該再用可枚舉的舊路徑當連結
    assert f"/match/{rid}/participant/T01" not in html


def test_token_link_anonymous_ok(client, monkeypatch):
    rid = _run_match(client, monkeypatch)
    token = sign_participant_token(rid, "T01")
    anon = TestClient(client.app)  # 全新 client，未登入
    r = anon.get(f"/r/{token}")
    assert r.status_code == 200
    assert "您的配對結果" in r.text


def test_token_link_only_own_participant(client, monkeypatch):
    rid = _run_match(client, monkeypatch)
    anon = TestClient(client.app)
    # T01 的 token 顯示 T01（王），不含 T02（李）的姓名作為「本人」
    html = anon.get(f"/r/{sign_participant_token(rid, 'T01')}").text
    assert "王" in html


def test_forged_or_random_token_404(client, monkeypatch):
    _run_match(client, monkeypatch)
    anon = TestClient(client.app)
    assert anon.get("/r/totally-made-up-token").status_code == 404
    # 竄改合法 token
    tok = sign_participant_token("x", "y")
    assert anon.get(f"/r/{tok[:-1]}X").status_code == 404


def test_old_individual_path_blocked_for_anon(client, monkeypatch):
    rid = _run_match(client, monkeypatch)
    anon = TestClient(client.app)
    # 未登入走舊可枚舉路徑 → 導向登入（非 200）
    r = anon.get(f"/match/{rid}/participant/T01", follow_redirects=False)
    assert r.status_code in (303, 403)
