"""Feature 011 US3：編輯 + 版本歷史 + Fork。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
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


def _minimal_form(tpl_id: str = "my-tpl", name: str = "我的範本"):
    return {
        "mode": "simple",
        "template_id": tpl_id,
        "template_name": name,
        "template_description": "測試用",
        "participant_attr_0_key": "name", "participant_attr_0_type": "str",
        "participant_attr_0_required": "on", "participant_attr_0_description": "姓名",
        "target_attr_0_key": "name", "target_attr_0_type": "str",
        "target_attr_0_required": "on", "target_attr_0_description": "對象名",
        "rule_0_id": "R001", "rule_0_type": "ge",
        "rule_0_field": "participant.name", "rule_0_value": "1",
    }


def _save(client, **overrides):
    form = _minimal_form()
    form.update(overrides)
    return client.post("/templates/save", data=form)


def test_custom_template_detail_shows_edit_button(client: TestClient):
    """T060：自訂範本詳細頁含「編輯」按鈕。"""
    _save(client)
    r = client.get("/templates/my-tpl")
    assert r.status_code == 200
    assert "編輯" in r.text
    assert "/templates/my-tpl/edit" in r.text


def test_builtin_template_detail_shows_fork_button(client: TestClient):
    """T061：內建範本顯示「複製為自訂版本」、不含「編輯」。"""
    r = client.get("/templates/teacher-class")
    assert r.status_code == 200
    assert "複製為自訂版本" in r.text
    assert "/templates/new?fork=teacher-class" in r.text
    # 應不含「編輯」按鈕（不是內建範本可編輯）
    assert "/templates/teacher-class/edit" not in r.text


def test_edit_page_preloads_latest_version(client: TestClient):
    """T062：寫 v1 + v2 後編輯頁預載 v2 內容。"""
    _save(client)
    _save(client, template_name="第二版")
    r = client.get("/templates/my-tpl/edit")
    assert r.status_code == 200
    # 預載 v2 的 name
    assert "第二版" in r.text


def test_save_existing_id_writes_v_next(client: TestClient, tmp_path: Path):
    """T063：已有 v1 + v2 後再 save → v3。"""
    _save(client)
    _save(client, template_name="第二版")
    r = _save(client, template_name="第三版")
    j = r.json()
    assert j["ok"] is True
    assert j["version"] == 3
    assert (tmp_path / "templates" / "my-tpl" / "v1.yaml").exists()
    assert (tmp_path / "templates" / "my-tpl" / "v2.yaml").exists()
    assert (tmp_path / "templates" / "my-tpl" / "v3.yaml").exists()


def test_version_history_section_lists_all_versions(client: TestClient):
    """T064：詳細頁顯示版本歷史 v1, v2, v3。"""
    _save(client)
    _save(client, template_name="第二版")
    _save(client, template_name="第三版")
    r = client.get("/templates/my-tpl")
    assert "版本歷史" in r.text
    assert "v1" in r.text
    assert "v2" in r.text
    assert "v3" in r.text


def test_get_specific_version_returns_yaml_content(client: TestClient):
    """T065：GET /templates/{id}/versions/{v} 回 YAML 內容。"""
    _save(client)
    _save(client, template_name="第二版")
    r = client.get("/templates/my-tpl/versions/1")
    assert r.status_code == 200
    data = yaml.safe_load(r.content)
    assert data["id"] == "my-tpl"
    assert data["name"] == "我的範本"  # v1 的 name

    r2 = client.get("/templates/my-tpl/versions/2")
    data2 = yaml.safe_load(r2.content)
    assert data2["name"] == "第二版"


def test_fork_builtin_prefills_form_with_builtin_content(client: TestClient):
    """T066：fork=teacher-class 預填表單。"""
    r = client.get("/templates/new?fork=teacher-class")
    assert r.status_code == 200
    # 預填 id 為 teacher-class-fork
    assert "teacher-class-fork" in r.text


def test_edit_builtin_returns_403(client: TestClient):
    """T067：嘗試編輯內建範本 → 403。"""
    r = client.get("/templates/teacher-class/edit")
    assert r.status_code == 403
    assert "不可編輯" in r.text


def test_get_version_for_builtin_returns_404(client: TestClient):
    """T068：內建範本沒有版本概念 → 404。"""
    r = client.get("/templates/teacher-class/versions/1")
    assert r.status_code == 404
