"""Feature 011 US1：簡單模式建立模板整合測試。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """每測試用獨立 data/templates/ tmp 目錄；同時隔離 MatchStore。"""
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    # 替換 routes/pages.py 的 _registry singleton 為 tmp-dir 版
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def _form_minimal(template_id: str = "club", **overrides):
    out = {
        "mode": "simple",
        "template_id": template_id,
        "template_name": "社團報名",
        "template_description": "測試",
        "role_attr_0_key": "name",
        "role_attr_0_type": "str",
        "role_attr_0_required": "on",
        "role_attr_0_description": "姓名",
        "role_attr_1_key": "grade",
        "role_attr_1_type": "int",
        "role_attr_1_required": "on",
        "role_attr_1_description": "年級",
        "target_attr_0_key": "name",
        "target_attr_0_type": "str",
        "target_attr_0_required": "on",
        "target_attr_0_description": "對象名",
        "rule_0_id": "R001",
        "rule_0_type": "ge",
        "rule_0_field": "role.grade",
        "rule_0_value": "1",
        "target_0_id": "T01",
        "target_0_capacity": "3",
        "target_0_name": "甲組",
    }
    out.update(overrides)
    return out


def test_get_new_page_default_simple_mode(client: TestClient):
    r = client.get("/templates/new")
    assert r.status_code == 200
    assert "簡單模式" in r.text
    assert "進階模式" in r.text
    assert "name=\"template_id\"" in r.text


def test_scenario_prefill_via_query_param(client: TestClient):
    r = client.get("/templates/new?scenario=club-signup")
    assert r.status_code == 200
    # 預填 club-signup 的 id
    assert "value=\"club-signup\"" in r.text or 'value="club-signup"' in r.text


def test_validate_endpoint_returns_summary(client: TestClient):
    r = client.post("/templates/validate", data=_form_minimal())
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["summary"]["id"] == "club"
    assert j["summary"]["attribute_count"]["roles"] == 2


def test_validate_endpoint_returns_errors_on_missing_id(client: TestClient):
    form = _form_minimal()
    form["template_id"] = ""
    r = client.post("/templates/validate", data=form)
    j = r.json()
    assert j["ok"] is False
    assert len(j["errors"]) >= 1


def test_save_creates_v1_yaml_file(client: TestClient, tmp_path: Path):
    r = client.post("/templates/save", data=_form_minimal(template_id="my-club"))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["version"] == 1
    assert (tmp_path / "templates" / "my-club" / "v1.yaml").exists()


def test_save_then_match_new_dropdown_shows_template(client: TestClient):
    client.post("/templates/save", data=_form_minimal(template_id="my-club-2"))
    r = client.get("/match/new")
    assert "my-club-2" in r.text


def test_save_persists_across_registry_reinit(client: TestClient, tmp_path: Path):
    client.post("/templates/save", data=_form_minimal(template_id="persist-test"))
    # 模擬重啟：新建 registry
    new_reg = TemplateRegistry(custom_dir=tmp_path / "templates")
    assert "persist-test" in new_reg.list_ids()
    assert new_reg.is_builtin("persist-test") is False


def test_save_rejects_builtin_id(client: TestClient):
    r = client.post("/templates/save", data=_form_minimal(template_id="teacher-class"))
    assert r.status_code == 409
    j = r.json()
    assert "內建模板" in j["errors"][0]


def test_save_rejects_invalid_id_format(client: TestClient):
    r = client.post("/templates/save", data=_form_minimal(template_id="Bad ID"))
    assert r.status_code == 400
    j = r.json()
    assert "格式不合法" in j["errors"][0] or "id" in j["errors"][0].lower()
