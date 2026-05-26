"""Feature 014 US3：範本私有/公開可見性。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app
from tests.integration._authhelper import login

CUSTOM_YAML = """
schema_version: "1.0"
id: a-private-tpl
name: A 的範本
description: 測試用
attributes:
  roles:
    - {key: name, type: str, required: true, description: 姓名}
  targets:
    - {key: name, type: str, required: true, description: 組名}
rules:
  - id: R001
    description: 規則
    expr: {eq: {field: role.name, value: x}}
"""


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
    page = client.get("/templates/new").text
    return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)


def _save_template(client, monkeypatch, email: str, yaml_text: str = CUSTOM_YAML):
    login(client, monkeypatch, email)
    csrf = _csrf(client)
    r = client.post("/templates/save", data={"mode": "advanced", "raw_yaml": yaml_text, "csrf_token": csrf})
    assert r.json().get("ok"), r.text
    return r.json()["id"]


def test_private_template_hidden_from_others(make_client, monkeypatch):
    ca = make_client()
    tid = _save_template(ca, monkeypatch, "a@example.com")

    cb = make_client()
    login(cb, monkeypatch, "b@example.com")
    # B 的列表看不到 A 的私有範本
    assert tid not in cb.get("/templates").text
    # B 直接開 → 403
    assert cb.get(f"/templates/{tid}", follow_redirects=False).status_code == 403


def test_public_template_visible_and_forkable(make_client, monkeypatch):
    ca = make_client()
    tid = _save_template(ca, monkeypatch, "a@example.com")
    # A 設為公開
    csrf = _csrf(ca)
    r = ca.post(f"/templates/{tid}/visibility", data={"visibility": "public", "csrf_token": csrf},
                follow_redirects=False)
    assert r.status_code == 303

    cb = make_client()
    login(cb, monkeypatch, "b@example.com")
    # B 看得到、可開、頁面提供「複製為自訂版本」
    assert tid in cb.get("/templates").text
    detail = cb.get(f"/templates/{tid}")
    assert detail.status_code == 200
    assert "複製為自訂版本" in detail.text


def test_non_owner_cannot_edit_public_template(make_client, monkeypatch):
    ca = make_client()
    tid = _save_template(ca, monkeypatch, "a@example.com")
    csrf = _csrf(ca)
    ca.post(f"/templates/{tid}/visibility", data={"visibility": "public", "csrf_token": csrf})

    cb = make_client()
    login(cb, monkeypatch, "b@example.com")
    # B 不能編輯（即使公開）
    assert cb.get(f"/templates/{tid}/edit", follow_redirects=False).status_code == 403
    # B 也不能存成 A 的 id
    csrf_b = _csrf(cb)
    r = cb.post("/templates/save", data={"mode": "advanced", "raw_yaml": CUSTOM_YAML, "csrf_token": csrf_b},
                follow_redirects=False)
    assert r.status_code == 403


def test_builtin_visible_to_all_logged_in(make_client, monkeypatch):
    c = make_client()
    login(c, monkeypatch, "anyone@example.com")
    body = c.get("/templates").text
    assert "teacher-class" in body
    assert "study-group" in body
    # 內建可開、可複製
    d = c.get("/templates/teacher-class")
    assert d.status_code == 200
    assert "複製為自訂版本" in d.text
