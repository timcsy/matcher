"""Feature 016 US1：上傳兩個試算表（角色 + 對象）配對。"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app

ROSTER = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\nT02,\xe6\x9d\x8e,\xe6\x95\xb8\xe5\xad\xb8,5\n"
# 對象 CSV（中文表頭、頓號分隔、雙語/stem 通過 R003）
TARGETS_CSV = (
    "編號,容量,班級名稱,班級需要的科目清單,班級特色\n"
    "C01,2,三年甲班,國文、數學,雙語\n"
    "C02,2,三年乙班,國文、英文、自然,stem\n"
).encode("utf-8")


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def _csrf(c):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get("/match/new").text).group(1)


def test_two_csv_files_match_succeeds(client):
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": _csrf(client)},
        files={"roster": ("roster.csv", io.BytesIO(ROSTER), "text/csv"),
               "targets_yaml": ("targets.csv", io.BytesIO(TARGETS_CSV), "text/csv")},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "配對完成" in r.text
    rid = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)
    audit = json.loads(client.get(f"/match/{rid}/audit").content)
    assert {t["id"] for t in audit["roster_snapshot"]["targets"]} == {"C01", "C02"}


def test_csv_roster_xlsx_targets_mixed(client):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["編號", "容量", "班級名稱", "班級需要的科目清單", "班級特色"])
    ws.append(["C01", 2, "甲班", "國文;數學", "雙語"])
    bio = io.BytesIO(); wb.save(bio)
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": _csrf(client)},
        files={"roster": ("roster.csv", io.BytesIO(ROSTER), "text/csv"),
               "targets_yaml": ("targets.xlsx", io.BytesIO(bio.getvalue()),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        follow_redirects=True,
    )
    assert r.status_code == 200 and "配對完成" in r.text


def test_targets_csv_equivalent_to_yaml_sidecar(client, tmp_path):
    """SC-005：對象 CSV vs YAML 旁檔 → audit 對象等價。"""
    # A：對象 CSV
    ra = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": _csrf(client)},
        files={"roster": ("roster.csv", io.BytesIO(ROSTER), "text/csv"),
               "targets_yaml": ("targets.csv", io.BytesIO(TARGETS_CSV), "text/csv")},
        follow_redirects=True,
    )
    rid_a = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', ra.text).group(1)
    targets_a = json.loads(client.get(f"/match/{rid_a}/audit").content)["roster_snapshot"]["targets"]

    # B：同資料 YAML 旁檔
    yaml_sidecar = (
        "targets:\n"
        "  - {id: C01, capacity: 2, attributes: {name: 三年甲班, required_subjects: [國文, 數學], feature: 雙語}}\n"
        "  - {id: C02, capacity: 2, attributes: {name: 三年乙班, required_subjects: [國文, 英文, 自然], feature: stem}}\n"
    ).encode("utf-8")
    rb = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": _csrf(client)},
        files={"roster": ("roster.csv", io.BytesIO(ROSTER), "text/csv"),
               "targets_yaml": ("x.targets.yaml", io.BytesIO(yaml_sidecar), "application/x-yaml")},
        follow_redirects=True,
    )
    rid_b = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', rb.text).group(1)
    targets_b = json.loads(client.get(f"/match/{rid_b}/audit").content)["roster_snapshot"]["targets"]

    assert json.dumps(targets_a, sort_keys=True, ensure_ascii=False) == \
           json.dumps(targets_b, sort_keys=True, ensure_ascii=False)


def test_no_targets_source_friendly_error(client):
    """只上傳角色、對象檔給空 → 友善錯誤（不露技術碼）。"""
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0",
              "csrf_token": _csrf(client), "_skip_auto_sidecar": "1"},
        files={"roster": ("roster.csv", io.BytesIO(ROSTER), "text/csv")},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "對象" in r.text  # 提到缺對象
