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


def test_m1_with_empty_prefs_failed_record(tmp_path: Path):
    """T040：Web M1 + 空 prefs → 結果頁顯示失敗 + M1 訊息。"""
    c = _client(tmp_path)
    r = _post_yaml_roster(c, "M1")
    assert r.status_code == 200, r.text
    assert "媒合失敗" in r.text
    assert "M1 需要至少一位角色提供志願" in r.text
    assert "MechanismRequiresPreferences" in r.text


def test_m2_with_empty_prefs_failed_record(tmp_path: Path):
    """T041：Web M2 + 空 prefs → 訊息「M2 需要至少一位角色提供志願」。"""
    c = _client(tmp_path)
    r = _post_yaml_roster(c, "M2")
    assert r.status_code == 200
    assert "媒合失敗" in r.text
    assert "M2 需要至少一位角色提供志願" in r.text


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
    assert "媒合失敗" in r.text
    assert "PreferencesNotSupported" in r.text
