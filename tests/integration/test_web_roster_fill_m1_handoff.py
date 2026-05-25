"""Feature 012 US3：M1/M2 → feature 009 志願頁 handoff。"""

from __future__ import annotations

import json
import re
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


def _study_form(mech: str = "M1") -> dict:
    """study-group 範本：6 學生（無志願）。"""
    form = {"template_id": "study-group", "seed": "2026", "mechanism": mech}
    students = [
        ("S01", "小明", "4"), ("S02", "小華", "5"), ("S03", "小美", "4"),
        ("S04", "阿志", "6"), ("S05", "小芬", "5"), ("S06", "小傑", "4"),
    ]
    for i, (rid, name, grade) in enumerate(students):
        form[f"role_{i}_id"] = rid
        form[f"role_{i}_name"] = name
        form[f"role_{i}_grade"] = grade
    # Feature 013：對象一律由 UI 填
    groups = [
        ("G1", "程式組", "program", "4", "3"),
        ("G2", "自然組", "science", "4", "3"),
        ("G3", "人文組", "humanities", "4", "3"),
    ]
    for j, (tid, name, topic, min_grade, cap) in enumerate(groups):
        form[f"target_{j}_id"] = tid
        form[f"target_{j}_capacity"] = cap
        form[f"target_{j}_name"] = name
        form[f"target_{j}_topic"] = topic
        form[f"target_{j}_min_grade"] = min_grade
    return form


def test_m1_with_prefs_template_renders_preferences_form(client: TestClient):
    """T040：M1 + 範本有 prefs schema → 200 + 志願頁。"""
    r = client.post("/match/run-from-form", data=_study_form("M1"))
    assert r.status_code == 200
    assert "填寫志願" in r.text or "志願" in r.text
    assert 'name="roster_bytes_b64"' in r.text


def test_m2_with_prefs_template_renders_preferences_form(client: TestClient):
    """T041：M2 同上。"""
    r = client.post("/match/run-from-form", data=_study_form("M2"))
    assert r.status_code == 200
    assert "志願" in r.text
    assert 'name="roster_bytes_b64"' in r.text


def test_m1_without_prefs_template_falls_back_to_failed_record(client: TestClient):
    """T042：無 prefs schema 範本 + M1 → 直接走 pipeline → failed record。"""
    form = {"template_id": "teacher-class", "seed": "2026", "mechanism": "M1",
            "role_0_id": "T01", "role_0_name": "王", "role_0_speciality": "國文", "role_0_seniority": "8",
            "target_0_id": "C01", "target_0_capacity": "2", "target_0_name": "甲班",
            "target_0_required_subjects": "國文;數學", "target_0_feature": "bilingual"}
    r = client.post("/match/run-from-form", data=form)
    # follow redirect → match detail with failed record
    assert r.status_code == 200
    assert "失敗" in r.text or "MechanismRequiresPreferences" in r.text or "preferences" in r.text.lower()


def test_handed_off_form_can_submit_preferences_and_run_match(client: TestClient):
    """T043：端到端 — UI 填名單 + M1 → 志願頁 → POST /match/preferences → 跑通。"""
    r1 = client.post("/match/run-from-form", data=_study_form("M1"))
    assert r1.status_code == 200

    # 從志願頁 HTML 抽出 hidden inputs
    def extract(name: str) -> str:
        m = re.search(rf'name="{name}"\s+value="([^"]*)"', r1.text)
        assert m, f"未找到 hidden input {name}"
        return m.group(1)

    pref_form = {
        "template_id": extract("template_id"),
        "mechanism": extract("mechanism"),
        "seed": extract("seed"),
        "roster_bytes_b64": extract("roster_bytes_b64"),
        "roster_filename": extract("roster_filename"),
        "targets_bytes_b64": extract("targets_bytes_b64"),
        "_action": "submit",
    }
    # 為每位學生填志願（study-group 預設對象通常 G1/G2/G3）
    for sid in ["S01", "S02", "S03", "S04", "S05", "S06"]:
        pref_form[f"pref_{sid}_1"] = "G1"

    r2 = client.post("/match/preferences", data=pref_form)
    assert r2.status_code == 200, r2.text[:500]
    assert "配對完成" in r2.text
