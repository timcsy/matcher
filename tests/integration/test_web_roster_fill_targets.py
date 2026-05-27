"""Feature 012 US2：自訂範本無 default_targets → UI 填對象。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app


CUSTOM_TPL_YAML = """
schema_version: "1.0"
id: custom-group
name: 自訂分組
description: 沒有預設對象
attributes:
  participants:
    - key: name
      type: str
      required: true
      description: 學生姓名
    - key: grade
      type: int
      required: true
      description: 年級
  targets:
    - key: name
      type: str
      required: true
      description: 組別名稱
    - key: topic
      type: str
      required: true
      description: 主題
rules:
  - id: R001
    description: 年級至少 1
    expr:
      ge: {field: participant.grade, value: 1}
"""


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    c = TestClient(create_app())
    # 預先寫入自訂範本（透過 /templates/save advanced 模式）
    r = c.post("/templates/save", data={"mode": "advanced", "raw_yaml": CUSTOM_TPL_YAML})
    assert r.json().get("ok"), r.text
    return c


def test_fill_page_always_shows_targets_section(client: TestClient):
    """Feature 013：對象段永遠顯示（移除 default_targets 概念後）。"""
    r = client.get("/match/new/fill?template_id=teacher-class")
    assert r.status_code == 200
    assert "對象清單" in r.text


def test_fill_page_shows_targets_section_for_custom_template_without_default_targets(client: TestClient):
    """T031：無 default_targets → 顯示對象段 + 範本宣告的對象屬性欄位。"""
    r = client.get("/match/new/fill?template_id=custom-group")
    assert r.status_code == 200
    assert "對象清單" in r.text
    assert "組別名稱" in r.text
    assert "主題" in r.text
    assert "新增一個對象" in r.text


def test_post_run_from_form_with_ui_targets_succeeds(client: TestClient):
    """T032：UI 填 5 參與者 + 3 對象 → M0 跑通 → audit.targets 含這 3 對象。"""
    form = {
        "template_id": "custom-group", "seed": "2026", "mechanism": "M0",
    }
    for i, (rid, name, grade) in enumerate([
        ("S01", "小明", "4"), ("S02", "小華", "5"), ("S03", "小美", "4"),
        ("S04", "阿志", "6"), ("S05", "小芬", "5"),
    ]):
        form[f"participant_{i}_id"] = rid
        form[f"participant_{i}_name"] = name
        form[f"participant_{i}_grade"] = grade
    for j, (tid, name, topic, cap) in enumerate([
        ("G1", "程式組", "program", "2"),
        ("G2", "自然組", "science", "2"),
        ("G3", "藝術組", "art", "2"),
    ]):
        form[f"target_{j}_id"] = tid
        form[f"target_{j}_name"] = name
        form[f"target_{j}_topic"] = topic
        form[f"target_{j}_capacity"] = cap

    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 200, r.text[:500]
    assert "配對完成" in r.text
    rid = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)
    audit = json.loads(client.get(f"/match/{rid}/audit").content)
    assert audit["mechanism"] == "M0"
    tgt_ids = {t["id"] for t in audit["roster_snapshot"]["targets"]}
    assert tgt_ids == {"G1", "G2", "G3"}


def test_post_run_from_form_empty_targets_rejected(client: TestClient):
    """無 default_targets 範本 + UI 沒填對象 → 400。"""
    form = {
        "template_id": "custom-group", "seed": "2026", "mechanism": "M0",
        "participant_0_id": "S01", "participant_0_name": "小明", "participant_0_grade": "4",
    }
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 400
    assert "對象" in r.text
