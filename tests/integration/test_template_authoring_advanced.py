"""Feature 011 US2：進階模式（YAML 編輯器 + AI prompt）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


VALID_YAML = """
schema_version: "1.0"
id: my-yaml-tpl
name: 我的範本
description: 測試用
attributes:
  roles:
    - key: name
      type: str
      required: true
      description: 姓名
  targets:
    - key: name
      type: str
      required: true
      description: 對象名
rules:
  - id: R001
    description: 規則 1
    expr:
      eq: {field: role.name, value: x}
"""


def test_advanced_mode_renders_yaml_textarea(client: TestClient):
    """T050：頁面含進階模式 textarea + AI prompt 填空。"""
    r = client.get("/templates/new")
    assert r.status_code == 200
    assert 'id="adv-raw-yaml"' in r.text
    assert 'id="ai-scenario"' in r.text
    assert "複製給 AI 看的說明" in r.text


def test_validate_accepts_raw_yaml_string(client: TestClient):
    """T051：進階模式合法 YAML → ok=true。"""
    r = client.post(
        "/templates/validate",
        data={"mode": "advanced", "raw_yaml": VALID_YAML},
    )
    j = r.json()
    assert j["ok"] is True, j
    assert j["summary"]["id"] == "my-yaml-tpl"


def test_validate_returns_error_on_invalid_yaml_syntax(client: TestClient):
    """T052：YAML 語法錯 → ok=false。"""
    r = client.post(
        "/templates/validate",
        data={"mode": "advanced", "raw_yaml": "id: foo\n  bad: indentation:\nname"},
    )
    j = r.json()
    assert j["ok"] is False
    assert any("YAML" in e or "語法" in e for e in j["errors"])


def test_validate_returns_error_on_invalid_expr_operator(client: TestClient):
    """T053：未知 expr 算子 → ok=false。"""
    bad = VALID_YAML.replace("eq: {field: role.name, value: x}", "gt: {field: role.name, value: x}")
    r = client.post(
        "/templates/validate",
        data={"mode": "advanced", "raw_yaml": bad},
    )
    j = r.json()
    assert j["ok"] is False


def test_save_advanced_mode_persists_yaml(client: TestClient, tmp_path: Path):
    """T054：進階模式儲存後檔案存在、內容可被 parse_template 接受。"""
    r = client.post(
        "/templates/save",
        data={"mode": "advanced", "raw_yaml": VALID_YAML},
    )
    j = r.json()
    assert j["ok"] is True
    assert j["id"] == "my-yaml-tpl"
    assert j["version"] == 1
    saved = tmp_path / "templates" / "my-yaml-tpl" / "v1.yaml"
    assert saved.exists()
    assert "my-yaml-tpl" in saved.read_text(encoding="utf-8")


def test_authoring_guide_endpoint_returns_markdown(client: TestClient):
    """JS copyAiPrompt 需要的 endpoint。"""
    r = client.get("/templates/authoring-guide.txt")
    assert r.status_code == 200
    assert "matcher 模板撰寫指南" in r.text or "template-authoring" in r.text.lower()
