"""Feature 014 Phase 2：登入流程基本行為。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app
from tests.integration._authhelper import login


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def test_unauthenticated_matches_redirects_to_login(client: TestClient):
    r = client.get("/matches", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_login_sets_session_and_grants_access(client: TestClient, monkeypatch):
    login(client, monkeypatch, "admin@example.com")
    r = client.get("/matches")
    assert r.status_code == 200
    assert "admin@example.com" in r.text  # 頁首顯示登入者


def test_logout_clears_session(client: TestClient, monkeypatch):
    login(client, monkeypatch, "admin@example.com")
    # 取得 csrf token
    page = client.get("/matches").text
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert m
    r = client.post("/logout", data={"csrf_token": m.group(1)}, follow_redirects=False)
    assert r.status_code == 303
    # 登出後再訪管理頁 → 導向登入
    r2 = client.get("/matches", follow_redirects=False)
    assert r2.status_code == 303


def test_login_page_accessible_anonymously(client: TestClient):
    r = client.get("/login")
    assert r.status_code == 200
    assert "用 Google 登入" in r.text
