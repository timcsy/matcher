"""Feature 012 Phase 2 + Feature 013：UI 表單 → CSV / YAML bytes 純函式測試。"""

from __future__ import annotations

import io
import csv
import json
from pathlib import Path

import pytest
import yaml

from matcher.template_loader import TemplateRegistry
from matcher.web.roster_form import (
    assemble_roster_csv_bytes,
    assemble_targets_yaml_bytes,
)

REG = TemplateRegistry()


def test_assemble_roster_csv_basic():
    """3 位參與者 → CSV bytes 可被 DictReader 解析。"""
    tpl = REG.get("teacher-class")
    form = {
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "T02", "role_1_name": "李老師", "role_1_speciality": "數學", "role_1_seniority": "5",
        "role_2_id": "T03", "role_2_name": "陳老師", "role_2_speciality": "英文", "role_2_seniority": "3",
    }
    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 3
    assert rows[0]["id"] == "T01"
    assert reader.fieldnames == ["id", "name", "speciality", "seniority"]


def test_assemble_roster_csv_filters_empty_rows():
    tpl = REG.get("teacher-class")
    form = {
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "", "role_1_name": "", "role_1_speciality": "", "role_1_seniority": "",
        "role_2_id": "T03", "role_2_name": "陳老師", "role_2_speciality": "英文", "role_2_seniority": "3",
    }
    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 2
    assert {r["id"] for r in rows} == {"T01", "T03"}


def test_assemble_roster_csv_byte_equiv_with_csv_path(tmp_path: Path):
    """SC-002：UI 表單組的 CSV 經 load_roster_csv 載入後 → 與直接 CSV 上傳 5 段 bytewise 等價。"""
    from matcher.data_import import load_roster_csv
    from matcher.pipeline import MatcherInput, run_match

    tpl = REG.get("teacher-class")
    form = {
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "T02", "role_1_name": "李老師", "role_1_speciality": "數學", "role_1_seniority": "5",
    }
    # Feature 013：兩條路徑都需要 sidecar
    sidecar_content = """targets:
  - id: C01
    capacity: 2
    attributes: {name: "三年甲班", required_subjects: ["國文", "數學"], feature: "bilingual"}
  - id: C02
    capacity: 2
    attributes: {name: "三年乙班", required_subjects: ["國文", "英文", "自然"], feature: "stem"}
"""

    # Path A：UI 表單
    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    p_a = tmp_path / "a.csv"
    p_a.write_bytes(csv_bytes)
    (tmp_path / "a.targets.yaml").write_text(sidecar_content, encoding="utf-8")
    ro_a, meta_a = load_roster_csv(p_a, tpl)
    audit_a = run_match(MatcherInput(
        ruleset=tpl.ruleset, roster=ro_a, seed=2026, preferences=None,
        mechanism="M0", template=tpl, import_metadata=meta_a,
    )).audit

    # Path B：手寫 CSV
    handwritten = "id,name,speciality,seniority\nT01,王老師,國文,8\nT02,李老師,數學,5\n"
    p_b = tmp_path / "b.csv"
    p_b.write_text(handwritten, encoding="utf-8-sig")
    (tmp_path / "b.targets.yaml").write_text(sidecar_content, encoding="utf-8")
    ro_b, meta_b = load_roster_csv(p_b, tpl)
    audit_b = run_match(MatcherInput(
        ruleset=tpl.ruleset, roster=ro_b, seed=2026, preferences=None,
        mechanism="M0", template=tpl, import_metadata=meta_b,
    )).audit

    for key in ("qualified_set", "assignment", "filter_trace", "allocation_trace", "template_snapshot"):
        s_a = json.dumps(audit_a[key], sort_keys=True, ensure_ascii=False)
        s_b = json.dumps(audit_b[key], sort_keys=True, ensure_ascii=False)
        assert s_a == s_b, f"{key} 不等價"


def test_assemble_targets_yaml_returns_none_when_form_empty():
    """Feature 013：未填任何對象 → 回 None。"""
    tpl = REG.get("teacher-class")
    assert assemble_targets_yaml_bytes({}, tpl) is None


def test_assemble_targets_yaml_basic():
    """UI 對象段 → 合法 YAML targets list。"""
    tpl = REG.get("study-group")
    form = {
        "target_0_id": "G1", "target_0_capacity": "3",
        "target_0_name": "程式組", "target_0_topic": "program", "target_0_min_grade": "4",
        "target_1_id": "G2", "target_1_capacity": "3",
        "target_1_name": "自然組", "target_1_topic": "science", "target_1_min_grade": "4",
    }
    yaml_bytes = assemble_targets_yaml_bytes(form, tpl)
    assert yaml_bytes is not None
    data = yaml.safe_load(yaml_bytes)
    assert "targets" in data
    assert len(data["targets"]) == 2
    assert data["targets"][0] == {
        "id": "G1", "capacity": 3,
        "attributes": {"name": "程式組", "topic": "program", "min_grade": 4},
    }


def test_target_id_auto_generated_when_blank():
    """對象編號留空 → 自動產生 T001…（feature: 對象自動編號）。"""
    tpl = REG.get("study-group")
    form = {
        "target_0_id": "", "target_0_capacity": "3",
        "target_0_name": "程式組", "target_0_topic": "program", "target_0_min_grade": "4",
        "target_1_id": "", "target_1_capacity": "3",
        "target_1_name": "自然組", "target_1_topic": "science", "target_1_min_grade": "4",
    }
    data = yaml.safe_load(assemble_targets_yaml_bytes(form, tpl))
    ids = [t["id"] for t in data["targets"]]
    assert ids == ["T001", "T002"]


def test_target_auto_id_avoids_user_ids():
    """混填：使用者填了 T001，留空者自動跳過 → 不撞號。"""
    tpl = REG.get("study-group")
    form = {
        "target_0_id": "T001", "target_0_capacity": "3", "target_0_name": "甲",
        "target_0_topic": "program", "target_0_min_grade": "4",
        "target_1_id": "", "target_1_capacity": "3", "target_1_name": "乙",
        "target_1_topic": "science", "target_1_min_grade": "4",
    }
    data = yaml.safe_load(assemble_targets_yaml_bytes(form, tpl))
    ids = [t["id"] for t in data["targets"]]
    assert ids == ["T001", "T002"]  # 自動編號避開已填的 T001 → 給 T002
    assert len(set(ids)) == 2
