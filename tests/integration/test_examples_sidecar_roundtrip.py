"""Feature 013 Phase 2：examples/*/roster.targets.yaml 完整性守門。"""

from __future__ import annotations

from pathlib import Path

import yaml

from matcher.data_import import load_roster_csv
from matcher.pipeline import MatcherInput, run_match
from matcher.template_loader import TemplateRegistry

REG = TemplateRegistry()
ROOT = Path(__file__).resolve().parents[2]


def test_examples_teacher_class_with_sidecar_round_trips():
    tpl = REG.get("teacher-class")
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    sidecar = ROOT / "examples" / "teacher-class" / "roster.targets.yaml"
    assert csv_path.exists(), "examples/teacher-class/roster.csv 應存在"
    assert sidecar.exists(), "examples/teacher-class/roster.targets.yaml 應存在（feature 013 Phase 2 補上）"

    ro, meta = load_roster_csv(csv_path, tpl)
    result = run_match(MatcherInput(
        ruleset=tpl.ruleset, roster=ro, seed=2026, preferences=None,
        mechanism="M0", template=tpl, import_metadata=meta,
    ))
    assert len(result.audit["roster_snapshot"]["targets"]) == 5
    assert {t["id"] for t in result.audit["roster_snapshot"]["targets"]} == {"C01", "C02", "C03", "C04", "C05"}


def test_examples_study_group_sidecar_has_three_groups():
    """study-group 範例的 sidecar 含 3 個小組（G1 程式 / G2 自然 / G3 人文）。"""
    sidecar = ROOT / "examples" / "study-group" / "roster.targets.yaml"
    assert sidecar.exists()
    data = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    assert {t["id"] for t in data["targets"]} == {"G1", "G2", "G3"}


def test_examples_sidecar_yaml_parseable():
    """旁檔 YAML 結構合法。"""
    for name in ("teacher-class", "study-group"):
        p = ROOT / "examples" / name / "roster.targets.yaml"
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert "targets" in data
        assert len(data["targets"]) >= 3
        for t in data["targets"]:
            assert "id" in t
            assert "capacity" in t and t["capacity"] >= 1
            assert "attributes" in t
