"""Feature 009 US2：跳過按鈕 + 路徑分流。"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _empty_prefs_csv(n: int = 3) -> bytes:
    lines = ["id,姓名,年級,志願組別"]
    for i in range(1, n + 1):
        lines.append(f"S{i:02d},S{i},5,")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _get_hidden(c: TestClient, *, mechanism: str = "M1") -> dict:
    r = c.post(
        "/match/run",
        data={"template_id": "study-group", "seed": "1", "mechanism": mechanism},
        files={"roster": ("e.csv", _empty_prefs_csv(3), "text/csv")},
    )
    out = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', r.text):
        out[m.group(1)] = m.group(2)
    return out


def test_skip_button_triggers_mechanism_requires_preferences_m1(tmp_path: Path):
    """T020：M1 + skip → 失敗結果頁含 M1 訊息。"""
    c = _client(tmp_path)
    hidden = _get_hidden(c, mechanism="M1")
    r = c.post("/match/preferences", data={**hidden, "_action": "skip"})
    assert r.status_code == 200
    assert "媒合失敗" in r.text
    assert "M1 需要至少一位角色提供志願" in r.text


def test_skip_button_m2_message(tmp_path: Path):
    """T021：M2 + skip → 訊息含 M2。"""
    c = _client(tmp_path)
    hidden = _get_hidden(c, mechanism="M2")
    r = c.post("/match/preferences", data={**hidden, "_action": "skip"})
    assert r.status_code == 200
    assert "媒合失敗" in r.text
    assert "M2 需要至少一位角色提供志願" in r.text


def test_m0_with_empty_prefs_does_not_jump_to_form(tmp_path: Path):
    """T022：M0 + 全空 prefs → 不跳填志願頁、直接 M0 成功。"""
    c = _client(tmp_path)
    r = c.post(
        "/match/run",
        data={"template_id": "study-group", "seed": "1", "mechanism": "M0"},
        files={"roster": ("e.csv", _empty_prefs_csv(3), "text/csv")},
    )
    assert r.status_code == 200
    assert "填寫志願" not in r.text  # 沒跳填志願頁
    # M0 應成功完成
    assert "媒合完成" in r.text


def test_teacher_class_template_does_not_jump_to_form(tmp_path: Path):
    """T023：teacher-class（無 schema）+ M1 → 不跳填志願頁、走既有 reject。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "1", "mechanism": "M1"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    assert r.status_code == 200
    assert "填寫志願" not in r.text
    # teacher-class 無 schema，M1 不能跑 → reject
    assert "媒合失敗" in r.text
