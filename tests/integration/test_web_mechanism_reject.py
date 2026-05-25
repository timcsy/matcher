"""Feature 008 US3：Web 路徑的 M1/M2 拒絕與錯誤回應。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _post_yaml_roster(c: TestClient, mechanism: str, template_id: str = "study-group"):
    # 用 study-group 沒有 prefs 的 roster.yaml；但 yaml mime 不在允許清單
    # → 改為構造一個無 prefs 欄的 CSV
    csv = "id,姓名,年級,志願組別\nS01,小明,5,\nS02,小華,4,\n"
    return c.post(
        "/match/run",
        data={"template_id": template_id, "seed": "1", "mechanism": mechanism},
        files={"roster": ("empty_prefs.csv", csv.encode("utf-8"), "text/csv")},
    )


def _hidden_from(html: str) -> dict:
    import re
    out = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', html):
        out[m.group(1)] = m.group(2)
    return out


def test_m1_with_empty_prefs_failed_record(tmp_path: Path):
    """T040：Web M1 + 空 prefs → feature 009 後跳填志願頁；按「跳過」→ 失敗訊息。"""
    c = _client(tmp_path)
    r1 = _post_yaml_roster(c, "M1")
    assert r1.status_code == 200, r1.text
    assert "填寫志願" in r1.text  # 跳到填志願頁（feature 009 行為）
    # 模擬使用者點「跳過此步驟」
    hidden = _hidden_from(r1.text)
    r2 = c.post("/match/preferences", data={**hidden, "_action": "skip"})
    assert r2.status_code == 200
    assert "配對失敗" in r2.text
    assert "「輪流挑」需要至少一位填了志願" in r2.text
    assert "MechanismRequiresPreferences" in r2.text


def test_m2_with_empty_prefs_failed_record(tmp_path: Path):
    """T041：Web M2 + 空 prefs → 跳填志願頁 + 跳過 → 失敗 M2 訊息。"""
    c = _client(tmp_path)
    r1 = _post_yaml_roster(c, "M2")
    assert r1.status_code == 200
    assert "填寫志願" in r1.text
    hidden = _hidden_from(r1.text)
    r2 = c.post("/match/preferences", data={**hidden, "_action": "skip"})
    assert r2.status_code == 200
    assert "配對失敗" in r2.text
    assert "「依志願先後填滿」需要至少一位填了志願" in r2.text


def test_m0_with_prefs_failed_record(tmp_path: Path):
    """T042：Web M0 + 有 prefs CSV → 失敗 + PreferencesNotSupported。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "1", "mechanism": "M0"},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    assert r.status_code == 200
    assert "配對失敗" in r.text
    assert "PreferencesNotSupported" in r.text
