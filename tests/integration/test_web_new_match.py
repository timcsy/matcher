"""US1：完整媒合流程整合測試。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    """每個測試使用獨立的 data/matches 目錄（透過 monkey-patching MatchStore base_dir）。"""
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def test_new_match_page(tmp_path: Path):
    c = _client(tmp_path)
    r = c.get("/match/new")
    assert r.status_code == 200
    assert "新建媒合" in r.text
    assert "teacher-class" in r.text
    assert "隨機種子" in r.text


def test_run_match_csv_to_result_to_audit(tmp_path: Path):
    """完整端到端：上傳 CSV → 結果頁 → 下載 audit → 與 CLI 路徑等價。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"

    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    assert r.status_code == 200, r.text  # follow_redirects 預設啟用 → 直接看到結果頁
    assert "媒合完成" in r.text
    assert "下載稽核紀錄" in r.text

    # 從結果頁取出 record_id
    import re
    m = re.search(r'/match/([0-9T:-]+-[a-f0-9]{8})/audit', r.text)
    assert m, "結果頁無 audit 下載連結"
    record_id = m.group(1)

    # 下載 audit
    r2 = c.get(f"/match/{record_id}/audit")
    assert r2.status_code == 200
    web_audit = json.loads(r2.content)

    # CLI 同樣輸入跑一次比對
    cli_out = tmp_path / "cli.json"
    from typer.testing import CliRunner
    from matcher.cli import app as cli_app
    runner = CliRunner()
    rr = runner.invoke(cli_app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv_path),
        "--seed", "123456",
        "--output", str(cli_out),
    ])
    assert rr.exit_code == 0, rr.output
    cli_audit = json.loads(cli_out.read_text(encoding="utf-8"))

    # 核心五段 bytewise 相同
    for key in ["qualified_set", "assignment", "filter_trace", "allocation_trace", "template_snapshot"]:
        assert web_audit[key] == cli_audit[key], f"{key} 不相等"


def test_run_with_xlsx(tmp_path: Path):
    c = _client(tmp_path)
    xlsx_path = ROOT / "examples" / "study-group" / "roster.xlsx"
    with xlsx_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026"},
            files={"roster": (
                "roster.xlsx",
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )},
        )
    assert r.status_code == 200, r.text
    assert "媒合完成" in r.text


def test_failed_match_writes_record(tmp_path: Path):
    """缺欄位的 CSV → 結果頁顯示失敗、紀錄寫入。"""
    c = _client(tmp_path)
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("姓名,年資\n王老師,8\n", encoding="utf-8")  # 缺 speciality

    with bad_csv.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "1"},
            files={"roster": ("bad.csv", f, "text/csv")},
        )
    assert r.status_code == 200
    assert "媒合失敗" in r.text
    assert "RosterColumnMismatch" in r.text
    assert "speciality" in r.text
