"""Feature 012 Phase 2：UI 表單 → CSV / YAML bytes 純函式測試。"""

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
    """T001：3 位角色 → CSV bytes 可被 DictReader 解析。"""
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
    assert rows[0]["name"] == "王老師"
    assert rows[0]["speciality"] == "國文"
    assert rows[0]["seniority"] == "8"
    # header 含範本宣告的所有 keys
    assert reader.fieldnames == ["id", "name", "speciality", "seniority"]


def test_assemble_roster_csv_filters_empty_rows():
    """T002：空白行自動過濾。"""
    tpl = REG.get("teacher-class")
    form = {
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "", "role_1_name": "", "role_1_speciality": "", "role_1_seniority": "",  # 空白
        "role_2_id": "T03", "role_2_name": "陳老師", "role_2_speciality": "英文", "role_2_seniority": "3",
    }
    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 2
    assert {r["id"] for r in rows} == {"T01", "T03"}


def test_assemble_roster_csv_byte_equiv_with_csv_path(tmp_path: Path):
    """T003：UI 表單組的 CSV 經 load_roster_csv 載入後 → 與直接 CSV 上傳 5 段 bytewise 等價。"""
    from matcher.data_import import load_roster_csv
    from matcher.pipeline import MatcherInput, run_match

    tpl = REG.get("teacher-class")
    form = {
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "T02", "role_1_name": "李老師", "role_1_speciality": "數學", "role_1_seniority": "5",
    }

    # Path A：UI 表單
    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    p_a = tmp_path / "a.csv"
    p_a.write_bytes(csv_bytes)
    ro_a, meta_a = load_roster_csv(p_a, tpl)
    audit_a = run_match(MatcherInput(
        ruleset=tpl.ruleset, roster=ro_a, seed=2026, preferences=None,
        mechanism="M0", template=tpl, import_metadata=meta_a,
    )).audit

    # Path B：手寫 CSV（與表單組出的完全等價）
    handwritten = "id,name,speciality,seniority\nT01,王老師,國文,8\nT02,李老師,數學,5\n"
    p_b = tmp_path / "b.csv"
    p_b.write_text(handwritten, encoding="utf-8-sig")
    ro_b, meta_b = load_roster_csv(p_b, tpl)
    audit_b = run_match(MatcherInput(
        ruleset=tpl.ruleset, roster=ro_b, seed=2026, preferences=None,
        mechanism="M0", template=tpl, import_metadata=meta_b,
    )).audit

    # 五段 bytewise 等價
    for key in ("qualified_set", "assignment", "filter_trace", "allocation_trace", "template_snapshot"):
        s_a = json.dumps(audit_a[key], sort_keys=True, ensure_ascii=False)
        s_b = json.dumps(audit_b[key], sort_keys=True, ensure_ascii=False)
        assert s_a == s_b, f"{key} 不等價"


def test_assemble_targets_yaml_returns_none_when_default_targets_exists():
    """T004：範本有 default_targets → 不輸出 sidecar。"""
    tpl = REG.get("teacher-class")  # 有 default_targets
    form = {"target_0_id": "X", "target_0_capacity": "5"}  # 即使表單有資料
    assert assemble_targets_yaml_bytes(form, tpl) is None


def test_assemble_targets_yaml_basic():
    """T005：UI 對象段 → 合法 YAML targets list。

    用一個 monkey-patched template（去掉 default_targets）模擬自訂範本。
    """
    import dataclasses
    base = REG.get("study-group")
    no_defaults = dataclasses.replace(base, default_targets=tuple())

    form = {
        "target_0_id": "G1", "target_0_capacity": "3",
        "target_0_name": "程式組", "target_0_topic": "program", "target_0_min_grade": "4",
        "target_1_id": "G2", "target_1_capacity": "3",
        "target_1_name": "自然組", "target_1_topic": "science", "target_1_min_grade": "4",
    }
    yaml_bytes = assemble_targets_yaml_bytes(form, no_defaults)
    assert yaml_bytes is not None
    data = yaml.safe_load(yaml_bytes)
    assert "targets" in data
    assert len(data["targets"]) == 2
    assert data["targets"][0] == {
        "id": "G1", "capacity": 3,
        "attributes": {"name": "程式組", "topic": "program", "min_grade": 4},
    }
