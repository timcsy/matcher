"""Feature 009 US1：完整填志願表單流程整合測試。"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from matcher.cli import app as cli_app
from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]
FIVE_KEYS = ["qualified_set", "assignment", "filter_trace",
             "allocation_trace", "template_snapshot"]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _empty_prefs_csv(students: int = 5) -> bytes:
    lines = ["id,姓名,年級,志願組別"]
    for i in range(1, students + 1):
        lines.append(f"S{i:02d},學生{i},5,")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post_run(c: TestClient, *, mechanism: str, csv_bytes: bytes, template_id: str = "study-group", seed: int = 2026):
    return c.post(
        "/match/run",
        data={"template_id": template_id, "seed": str(seed), "mechanism": mechanism},
        files={"roster": ("students.csv", csv_bytes, "text/csv")},
    )


# ── Phase 2 Foundational ──────────────────────────────────────────

def test_post_run_with_empty_prefs_m1_renders_preferences_form(tmp_path: Path):
    """T002：M1 + 全空 prefs → 200 + 填志願頁。"""
    c = _client(tmp_path)
    r = _post_run(c, mechanism="M1", csv_bytes=_empty_prefs_csv(9))
    assert r.status_code == 200, r.text
    assert "填寫志願" in r.text
    # 表格應含 9 學生 id
    for i in range(1, 10):
        assert f"S{i:02d}" in r.text


# ── US1 主要流程 ──────────────────────────────────────────────────

def test_preferences_form_lists_roles_and_targets(tmp_path: Path):
    """T010：表單列出 9 學生 + 27 個 select + 候選對象段。"""
    c = _client(tmp_path)
    r = _post_run(c, mechanism="M1", csv_bytes=_empty_prefs_csv(9))
    # 9 × 3 = 27 個 pref_ select
    selects = re.findall(r'<select name="pref_S\d{2}_\d"', r.text)
    assert len(selects) == 27, f"預期 27 個 select、實際 {len(selects)}"
    # 候選對象段
    assert "程式組（容量 3 人）" in r.text
    assert "自然組（容量 3 人）" in r.text
    assert "人文組（容量 3 人）" in r.text


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    """從填志願頁 HTML 抽出 hidden inputs（template_id/mechanism/seed/roster_bytes_b64/roster_filename）。"""
    out = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', html):
        out[m.group(1)] = m.group(2)
    return out


def _submit_preferences(c: TestClient, hidden: dict, prefs_by_role: dict[str, list[str]]):
    data = {**hidden, "_action": "submit"}
    for rid, prefs in prefs_by_role.items():
        for i, pref in enumerate(prefs, start=1):
            data[f"pref_{rid}_{i}"] = pref
    return c.post("/match/preferences", data=data)


def test_post_preferences_with_valid_choices_succeeds(tmp_path: Path):
    """T011：填志願 POST 成功 → 結果頁含 M1 audit。"""
    c = _client(tmp_path)
    r1 = _post_run(c, mechanism="M1", csv_bytes=_empty_prefs_csv(5))
    hidden = _extract_hidden_inputs(r1.text)
    assert hidden.get("mechanism") == "M1"

    prefs = {
        "S01": ["G1", "G2"],
        "S02": ["G1"],
        "S03": ["G3", "G1"],
        "S04": ["G2", "G1"],
        "S05": ["G2"],
    }
    r2 = _submit_preferences(c, hidden, prefs)
    assert r2.status_code == 200, r2.text  # follow_redirects 預設 → 結果頁
    assert "媒合完成" in r2.text
    assert "M1 RSD 隨機輪流挑" in r2.text

    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r2.text)
    rid = m.group(1)
    audit = json.loads(c.get(f"/match/{rid}/audit").content)
    assert audit["mechanism"] == "M1"
    assert audit["processing_order"] is not None


def test_web_csv_audit_bytewise_equal(tmp_path: Path):
    """T012：Web 填志願 vs CSV preferences 欄 → audit 五段 bytewise 相等。"""
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    c = _client(web_dir)

    # Web：上傳全空 CSV → 跳填志願頁 → 填志願 → 跑
    r1 = _post_run(c, mechanism="M1", csv_bytes=_empty_prefs_csv(5))
    hidden = _extract_hidden_inputs(r1.text)
    prefs = {
        "S01": ["G1", "G2"],
        "S02": ["G1"],
        "S03": ["G3", "G1"],
        "S04": ["G2", "G1"],
        "S05": ["G2"],
    }
    r2 = _submit_preferences(c, hidden, prefs)
    rid = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r2.text).group(1)
    web_audit = json.loads(c.get(f"/match/{rid}/audit").content)

    # CLI：等價 CSV
    csv_lines = ["id,姓名,年級,志願組別"]
    for i in range(1, 6):
        rid_str = f"S{i:02d}"
        prefs_str = ";".join(prefs[rid_str])
        csv_lines.append(f"{rid_str},學生{i},5,{prefs_str}")
    csv_path = cli_dir / "with_prefs.csv"
    csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
    out = cli_dir / "cli.json"
    runner = CliRunner()
    r = runner.invoke(cli_app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(csv_path),
        "--seed", "2026",
        "--mechanism", "M1",
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    cli_audit = json.loads(out.read_text(encoding="utf-8"))

    for k in FIVE_KEYS:
        s_w = json.dumps(web_audit[k], sort_keys=True, ensure_ascii=False)
        s_c = json.dumps(cli_audit[k], sort_keys=True, ensure_ascii=False)
        assert s_w == s_c, f"{k} 不相等"


def test_preferences_form_csv_with_partial_prefs_uses_skip_path(tmp_path: Path):
    """T013：CSV 已含 prefs → 不跳填志願頁、直接執行。"""
    c = _client(tmp_path)
    csv = b"id,\xe5\xa7\x93\xe5\x90\x8d,\xe5\xb9\xb4\xe7\xb4\x9a,\xe5\xbf\x97\xe9\xa1\x98\xe7\xb5\x84\xe5\x88\xa5\nS01,A,5,G1\nS02,B,4,\n"
    r = _post_run(c, mechanism="M1", csv_bytes=csv)
    assert r.status_code == 200
    # 不應出現填志願頁的標題
    assert "填寫志願" not in r.text
    # 應跳到結果頁
    assert "媒合完成" in r.text or "媒合失敗" in r.text


def test_preferences_form_hidden_inputs_round_trip(tmp_path: Path):
    """T014：hidden inputs 含 base64 + filename 正確。"""
    c = _client(tmp_path)
    r = _post_run(c, mechanism="M1", csv_bytes=_empty_prefs_csv(5), seed=12345)
    hidden = _extract_hidden_inputs(r.text)
    assert hidden["template_id"] == "study-group"
    assert hidden["mechanism"] == "M1"
    assert hidden["seed"] == "12345"
    assert hidden["roster_filename"] == "students.csv"
    assert "roster_bytes_b64" in hidden and len(hidden["roster_bytes_b64"]) > 0
    # base64 decode 應得 CSV 內容
    decoded = base64.b64decode(hidden["roster_bytes_b64"])
    assert b"S01" in decoded
