"""US3：過去紀錄紀錄整合測試。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def test_empty_records_list(tmp_path: Path):
    c = _client(tmp_path)
    r = c.get("/matches")
    assert r.status_code == 200
    assert "還沒做過" in r.text


def test_records_list_after_runs(tmp_path: Path):
    c = _client(tmp_path)
    csv = ROOT / "examples" / "teacher-class" / "roster.csv"
    # 跑兩次成功
    for seed in (123, 456):
        with csv.open("rb") as f:
            c.post("/match/run", data={"template_id": "teacher-class", "seed": str(seed)},
                   files={"roster": ("roster.csv", f, "text/csv")})

    r = c.get("/matches")
    assert r.status_code == 200
    assert r.text.count("教師-班級配對") >= 2
    assert "✅ 成功" in r.text


def test_failed_record_appears_in_list(tmp_path: Path):
    c = _client(tmp_path)
    bad = tmp_path / "bad.csv"
    bad.write_text("姓名,年資\n王老師,8\n", encoding="utf-8")
    with bad.open("rb") as f:
        c.post("/match/run", data={"template_id": "teacher-class", "seed": "1"},
               files={"roster": ("bad.csv", f, "text/csv")})
    r = c.get("/matches")
    assert "RosterColumnMismatch" in r.text


def test_audit_download_404_for_failed(tmp_path: Path):
    c = _client(tmp_path)
    bad = tmp_path / "bad.csv"
    bad.write_text("姓名,年資\n王老師,8\n", encoding="utf-8")
    with bad.open("rb") as f:
        post_r = c.post("/match/run", data={"template_id": "teacher-class", "seed": "1"},
                        files={"roster": ("bad.csv", f, "text/csv")})
    # 從結果頁取 record_id
    import re
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', post_r.text)
    assert m
    record_id = m.group(1)

    r = c.get(f"/match/{record_id}/audit")
    assert r.status_code == 404
