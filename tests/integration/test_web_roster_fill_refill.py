"""UX 改善：填清單頁驗證錯誤回填（不丟資料、不露英文代碼）。"""

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


def test_missing_targets_refills_form_keeps_roles_no_english_code(client: TestClient):
    """只填角色、沒填對象 → 回填清單頁（非錯誤頁），保留已填角色，且不露英文代碼。"""
    form = {
        "template_id": "teacher-class", "seed": "123456", "mechanism": "M0",
        "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_name": "李老師", "role_1_speciality": "數學", "role_1_seniority": "5",
    }
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 400
    # 留在填清單頁（不是整頁「發生錯誤」頁）
    assert "填清單" in r.text
    assert "還差一步" in r.text
    # 不露英文技術代碼
    assert "EmptyTargets" not in r.text
    assert "EmptyRoster" not in r.text
    # 已填的角色資料被回填（出現在 prefill JSON 裡）
    assert "王老師" in r.text
    assert "李老師" in r.text


def test_empty_roster_refills_with_friendly_message(client: TestClient):
    """完全沒填 → 回填頁 + 友善訊息，無英文代碼。"""
    form = {"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"}
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 400
    assert "填清單" in r.text
    assert "EmptyRoster" not in r.text
    assert "EmptyTargets" not in r.text


def test_non_integer_seed_refills_keeps_data(client: TestClient):
    """種子填了非數字 → 回填頁保留資料 + 友善訊息。"""
    form = {
        "template_id": "teacher-class", "seed": "abc", "mechanism": "M0",
        "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "target_0_id": "C01", "target_0_capacity": "2", "target_0_name": "甲班",
        "target_0_required_subjects": "國文;數學", "target_0_feature": "雙語",
    }
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 400
    assert "整數" in r.text or "數字" in r.text
    assert "王老師" in r.text  # 資料保留


def test_separator_tolerance_chinese_punctuation(client: TestClient):
    """list_str 欄位用頓號 / 全形分號也能正確切分。"""
    import json
    form = {
        "template_id": "teacher-class", "seed": "2026", "mechanism": "M0",
        "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        # 用頓號與全形分號混搭
        "target_0_id": "C01", "target_0_capacity": "2", "target_0_name": "甲班",
        "target_0_required_subjects": "國文、數學", "target_0_feature": "雙語",
    }
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 200
    assert "配對完成" in r.text
    import re
    rid = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)
    audit = json.loads(client.get(f"/match/{rid}/audit").content)
    c01 = next(t for t in audit["roster_snapshot"]["targets"] if t["id"] == "C01")
    assert c01["attributes"]["required_subjects"] == ["國文", "數學"]
