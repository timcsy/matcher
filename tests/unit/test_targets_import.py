"""Feature 016：對象試算表（CSV/Excel）載入。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from matcher.data_import import (
    load_roster_csv,
    load_targets_csv,
    load_targets_xlsx,
)
from matcher.errors import DuplicateIdentity, RosterColumnMismatch
from matcher.template_loader import TemplateRegistry

REG = TemplateRegistry()
ROOT = Path(__file__).resolve().parents[2]

# teacher-class 對象屬性：name(班級名稱)/required_subjects(多筆)/feature(班級特色)
TC = "teacher-class"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8-sig")
    return p


def test_load_targets_csv_basic(tmp_path):
    csv = "id,capacity,name,required_subjects,feature\nC01,2,三年甲班,國文;數學,雙語\n"
    p = _write(tmp_path, "t.csv", csv)
    targets = load_targets_csv(p, REG.get(TC))
    assert len(targets) == 1
    t = targets[0]
    assert t.id == "C01" and t.capacity == 2
    assert t.attributes["name"] == "三年甲班"
    assert t.attributes["required_subjects"] == ["國文", "數學"]
    assert t.attributes["feature"] == "雙語"


def test_load_targets_csv_chinese_headers(tmp_path):
    csv = "編號,容量,班級名稱,班級需要的科目清單,班級特色\nC01,2,甲班,國文、數學,雙語\n"
    p = _write(tmp_path, "t.csv", csv)
    targets = load_targets_csv(p, REG.get(TC))
    assert targets[0].attributes["name"] == "甲班"
    # 頓號分隔也要切對
    assert targets[0].attributes["required_subjects"] == ["國文", "數學"]


def test_load_targets_csv_missing_capacity_col_raises(tmp_path):
    csv = "編號,班級名稱,班級特色\nC01,甲班,雙語\n"
    p = _write(tmp_path, "t.csv", csv)
    with pytest.raises(RosterColumnMismatch) as ei:
        load_targets_csv(p, REG.get(TC))
    assert "容量" in str(ei.value)


def test_load_targets_csv_duplicate_id_raises(tmp_path):
    csv = "id,capacity,name,required_subjects,feature\nC01,2,甲,國文,雙語\nC01,2,乙,數學,stem\n"
    p = _write(tmp_path, "t.csv", csv)
    with pytest.raises(DuplicateIdentity):
        load_targets_csv(p, REG.get(TC))


def test_load_targets_csv_no_id_column_auto_numbers(tmp_path):
    csv = "容量,班級名稱,班級需要的科目清單,班級特色\n2,甲,國文,雙語\n2,乙,數學,stem\n"
    p = _write(tmp_path, "t.csv", csv)
    targets = load_targets_csv(p, REG.get(TC))
    assert [t.id for t in targets] == ["T001", "T002"]


def test_load_targets_csv_partial_id_avoids_collision(tmp_path):
    csv = "編號,容量,班級名稱,班級需要的科目清單,班級特色\nT001,2,甲,國文,雙語\n,2,乙,數學,stem\n"
    p = _write(tmp_path, "t.csv", csv)
    targets = load_targets_csv(p, REG.get(TC))
    ids = [t.id for t in targets]
    assert ids[0] == "T001"
    assert ids[1] == "T002"  # 自動編號避開已填 T001
    assert len(set(ids)) == 2


def test_load_targets_xlsx_basic(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["id", "capacity", "name", "required_subjects", "feature"])
    ws.append(["C01", 2, "甲班", "國文;數學", "雙語"])
    p = tmp_path / "t.xlsx"
    wb.save(p)
    targets = load_targets_xlsx(p, REG.get(TC))
    assert targets[0].id == "C01" and targets[0].capacity == 2
    assert targets[0].attributes["required_subjects"] == ["國文", "數學"]


def test_load_roster_csv_with_injected_targets(tmp_path):
    roster = "id,name,speciality,seniority\nT01,王,國文,8\n"
    rp = _write(tmp_path, "r.csv", roster)
    tcsv = "id,capacity,name,required_subjects,feature\nC01,2,甲,國文,雙語\n"
    tp = _write(tmp_path, "t.csv", tcsv)
    targets = load_targets_csv(tp, REG.get(TC))
    ro, meta = load_roster_csv(rp, REG.get(TC), targets=targets)
    assert {t.id for t in ro.targets} == {"C01"}


def test_load_roster_csv_targets_none_uses_sidecar(tmp_path):
    roster = "id,name,speciality,seniority\nT01,王,國文,8\n"
    rp = _write(tmp_path, "r.csv", roster)
    # 旁檔提供 targets
    (tmp_path / "r.targets.yaml").write_text(
        'targets:\n  - {id: C9, capacity: 2, attributes: {name: 班, required_subjects: [國文], feature: 雙語}}\n',
        encoding="utf-8",
    )
    ro, meta = load_roster_csv(rp, REG.get(TC))  # targets=None → 旁檔
    assert {t.id for t in ro.targets} == {"C9"}
