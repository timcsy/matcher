"""Feature 012 US1：UI 填角色名單 → 跑通 M0 → Web/CSV bytewise 等價。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from matcher.cli import app as cli_app
from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]
FIVE_KEYS = ("qualified_set", "assignment", "filter_trace", "allocation_trace", "template_snapshot")


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def test_new_match_page_has_three_modes(client: TestClient):
    """T016：/match/new 三選一。"""
    r = client.get("/match/new")
    assert "上傳清單檔" in r.text
    assert "直接填清單" in r.text
    assert "從過去紀錄" in r.text


def test_fill_page_renders_role_attrs_from_template(client: TestClient):
    """T010：填寫頁顯示範本宣告的中文欄位名。"""
    r = client.get("/match/new/fill?template_id=teacher-class")
    assert r.status_code == 200
    assert "老師姓名" in r.text
    assert "老師專業科目" in r.text
    assert "年資" in r.text
    assert "新增一位" in r.text


def test_fill_page_404_on_unknown_template(client: TestClient):
    """T011：未知範本 → 404。"""
    r = client.get("/match/new/fill?template_id=no-such")
    assert r.status_code == 404


def _fill_form(n: int = 3, seed: str = "2026"):
    """產生 n 位老師的 form dict（含 id/name/speciality/seniority）。"""
    form = {
        "template_id": "teacher-class",
        "seed": seed,
        "mechanism": "M0",
    }
    data = [
        ("T01", "王老師", "國文", "8"),
        ("T02", "李老師", "數學", "5"),
        ("T03", "陳老師", "英文", "3"),
        ("T04", "林老師", "自然", "10"),
        ("T05", "張老師", "社會", "6"),
        ("T06", "黃老師", "數學", "4"),
        ("T07", "周老師", "國文", "7"),
    ]
    for i, (rid, name, spec, sen) in enumerate(data[:n]):
        form[f"role_{i}_id"] = rid
        form[f"role_{i}_name"] = name
        form[f"role_{i}_speciality"] = spec
        form[f"role_{i}_seniority"] = sen
    # Feature 013：對象一律由 UI 填或旁檔，不再有 default_targets
    classes = [
        ("C01", "三年甲班", "國文;數學", "雙語", "2"),
        ("C02", "三年乙班", "國文;英文;自然", "stem", "2"),
        ("C03", "三年丙班", "數學;自然", "stem", "2"),
        ("C04", "三年丁班", "國文;英文", "藝術", "2"),
        ("C05", "三年戊班", "國文;社會;自然", "藝術", "2"),
    ]
    for j, (tid, name, subjects, feature, cap) in enumerate(classes):
        form[f"target_{j}_id"] = tid
        form[f"target_{j}_capacity"] = cap
        form[f"target_{j}_name"] = name
        form[f"target_{j}_required_subjects"] = subjects
        form[f"target_{j}_feature"] = feature
    return form


def test_post_run_from_form_m0_succeeds(client: TestClient):
    """T012：M0 跑通。"""
    form = _fill_form(n=3)
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 200  # follow_redirects 預設 → 結果頁
    assert "配對完成" in r.text
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text)
    rid = m.group(1)
    audit = json.loads(client.get(f"/match/{rid}/audit").content)
    assert audit["mechanism"] == "M0"
    assert len(audit["assignment"]) == 3


def test_post_run_from_form_audit_bytewise_equals_csv_path(client: TestClient, tmp_path: Path):
    """T013：UI 填的 audit 與 CSV 路徑 5 段 bytewise 等價。"""
    # Path A: UI form POST
    form = _fill_form(n=3)
    r = client.post("/match/run-from-form", data=form)
    rid_a = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)
    audit_a = json.loads(client.get(f"/match/{rid_a}/audit").content)

    # Path B: CLI runner with handwritten CSV + sidecar
    csv_text = "id,name,speciality,seniority\nT01,王老師,國文,8\nT02,李老師,數學,5\nT03,陳老師,英文,3\n"
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(csv_text, encoding="utf-8-sig")
    sidecar = tmp_path / "test.targets.yaml"
    sidecar.write_text("""targets:
  - id: C01
    capacity: 2
    attributes: {name: "三年甲班", required_subjects: ["國文", "數學"], feature: "雙語"}
  - id: C02
    capacity: 2
    attributes: {name: "三年乙班", required_subjects: ["國文", "英文", "自然"], feature: "stem"}
  - id: C03
    capacity: 2
    attributes: {name: "三年丙班", required_subjects: ["數學", "自然"], feature: "stem"}
  - id: C04
    capacity: 2
    attributes: {name: "三年丁班", required_subjects: ["國文", "英文"], feature: "藝術"}
  - id: C05
    capacity: 2
    attributes: {name: "三年戊班", required_subjects: ["國文", "社會", "自然"], feature: "藝術"}
""", encoding="utf-8")
    audit_path = tmp_path / "cli.json"
    runner = CliRunner()
    r2 = runner.invoke(cli_app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv_path),
        "--seed", "2026",
        "--output", str(audit_path),
    ])
    assert r2.exit_code == 0, r2.output
    audit_b = json.loads(audit_path.read_text(encoding="utf-8"))

    for key in FIVE_KEYS:
        s_a = json.dumps(audit_a[key], sort_keys=True, ensure_ascii=False)
        s_b = json.dumps(audit_b[key], sort_keys=True, ensure_ascii=False)
        assert s_a == s_b, f"{key} 不等價"


def test_post_run_from_form_filters_empty_rows(client: TestClient):
    """T014：含空白行的 form 與「只填 3 位的 form」等價。"""
    # 5 列但其中 2 列空白
    form = {
        "template_id": "teacher-class", "seed": "2026", "mechanism": "M0",
        "role_0_id": "T01", "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        "role_1_id": "", "role_1_name": "", "role_1_speciality": "", "role_1_seniority": "",
        "role_2_id": "T02", "role_2_name": "李老師", "role_2_speciality": "數學", "role_2_seniority": "5",
        "role_3_id": "", "role_3_name": "", "role_3_speciality": "", "role_3_seniority": "",
        "role_4_id": "T03", "role_4_name": "陳老師", "role_4_speciality": "英文", "role_4_seniority": "3",
        # Feature 013：必須填對象
        "target_0_id": "C01", "target_0_capacity": "3",
        "target_0_name": "三年甲班", "target_0_required_subjects": "國文;數學", "target_0_feature": "雙語",
    }
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 200
    rid = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)
    audit = json.loads(client.get(f"/match/{rid}/audit").content)
    assert len(audit["assignment"]) == 3


def test_post_run_from_form_requires_at_least_one_role(client: TestClient):
    """T015：全空角色 → 400。"""
    form = {"template_id": "teacher-class", "seed": "2026", "mechanism": "M0"}
    r = client.post("/match/run-from-form", data=form)
    assert r.status_code == 400
    assert "至少" in r.text or "請填" in r.text or "清單" in r.text
