"""Feature 014：刪除自訂範本（擁有者限定、硬刪除、過去配對不受影響）。"""

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
id: del-tpl
name: 待刪範本
description: 測試
attributes:
  roles:
    - {key: name, type: str, required: true, description: 姓名}
    - {key: grade, type: int, required: true, description: 年級}
  targets:
    - {key: name, type: str, required: true, description: 組名}
rules:
  - id: R001
    description: 年級至少 1
    expr: {ge: {field: role.grade, value: 1}}
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
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get("/templates/new").text).group(1)


def _save(client, monkeypatch, email, yaml_text=CUSTOM_YAML):
    login(client, monkeypatch, email)
    r = client.post("/templates/save", data={"mode": "advanced", "raw_yaml": yaml_text, "csrf_token": _csrf(client)})
    assert r.json().get("ok"), r.text
    return r.json()["id"]


def test_owner_can_delete(make_client, monkeypatch):
    c = make_client()
    tid = _save(c, monkeypatch, "a@example.com")
    assert c.get(f"/templates/{tid}").status_code == 200
    r = c.post(f"/templates/{tid}/delete", data={"csrf_token": _csrf(c)}, follow_redirects=False)
    assert r.status_code == 303
    # 刪除後不存在
    assert c.get(f"/templates/{tid}", follow_redirects=False).status_code == 404
    assert tid not in c.get("/templates").text


def test_non_owner_cannot_delete(make_client, monkeypatch):
    ca = make_client()
    tid = _save(ca, monkeypatch, "a@example.com")
    cb = make_client()
    login(cb, monkeypatch, "b@example.com")
    r = cb.post(f"/templates/{tid}/delete", data={"csrf_token": _csrf(cb)}, follow_redirects=False)
    assert r.status_code == 403
    # 仍存在
    assert ca.get(f"/templates/{tid}").status_code == 200


def test_builtin_cannot_be_deleted(make_client, monkeypatch):
    c = make_client()
    login(c, monkeypatch, "a@example.com")
    r = c.post("/templates/teacher-class/delete", data={"csrf_token": _csrf(c)}, follow_redirects=False)
    assert r.status_code == 403


def test_delete_requires_csrf(make_client, monkeypatch):
    c = make_client()
    tid = _save(c, monkeypatch, "a@example.com")
    r = c.post(f"/templates/{tid}/delete", data={}, follow_redirects=False)
    assert r.status_code == 403


def test_past_match_survives_template_deletion(make_client, monkeypatch):
    """紅利驗證：刪範本後，用該範本跑過的配對紀錄與個別連結仍可查（audit 內嵌快照）。"""
    c = make_client()
    tid = _save(c, monkeypatch, "a@example.com")
    csrf = _csrf(c)
    # 用該自訂範本跑一次配對（UI 填名單）
    form = {
        "template_id": tid, "seed": "2026", "mechanism": "M0", "csrf_token": csrf,
        "role_0_name": "小明", "role_0_grade": "5",
        "target_0_id": "G1", "target_0_capacity": "3", "target_0_name": "甲組",
    }
    r = c.post("/match/run-from-form", data=form, follow_redirects=False)
    assert r.status_code == 303
    mid = r.headers["location"].rsplit("/", 1)[-1]
    # 刪掉範本
    c.post(f"/templates/{tid}/delete", data={"csrf_token": _csrf(c)})
    assert c.get(f"/templates/{tid}", follow_redirects=False).status_code == 404
    # 過去配對紀錄仍可查（snapshot 自包含）
    detail = c.get(f"/match/{mid}")
    assert detail.status_code == 200
    assert "配對完成" in detail.text
