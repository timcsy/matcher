"""Feature 009 US3：透明度 + 驗證 + 邊界。"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_TOKENS = (
    "default_targets", "preferences_schema", "max_choices",
    "preference_rank", "preferred_order",
)


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _empty_prefs_csv(n: int = 3) -> bytes:
    lines = ["id,姓名,年級,志願組別"]
    for i in range(1, n + 1):
        lines.append(f"S{i:02d},S{i},5,")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _get_form_page(c: TestClient, mechanism: str = "M1"):
    return c.post(
        "/match/run",
        data={"template_id": "study-group", "seed": "1", "mechanism": mechanism},
        files={"roster": ("e.csv", _empty_prefs_csv(3), "text/csv")},
    )


def _get_hidden(html: str) -> dict:
    out = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', html):
        out[m.group(1)] = m.group(2)
    return out


def test_no_technical_tokens_in_preferences_form(tmp_path: Path):
    """T030：填志願頁 HTML 無技術 token。"""
    c = _client(tmp_path)
    r = _get_form_page(c)
    for token in FORBIDDEN_TOKENS:
        assert token not in r.text, f"頁面含禁用 token: {token}"


def test_post_preferences_rejects_duplicate_in_same_row(tmp_path: Path):
    """T031：同列重複 → 回填志願頁 + 錯誤訊息。"""
    c = _client(tmp_path)
    r1 = _get_form_page(c)
    hidden = _get_hidden(r1.text)
    data = {**hidden, "_action": "submit",
            "pref_S01_1": "G1", "pref_S01_2": "G1", "pref_S01_3": ""}
    r = c.post("/match/preferences", data=data)
    assert r.status_code == 200
    assert "填寫志願" in r.text  # 回到填志願頁
    assert "重複" in r.text


def test_post_preferences_rejects_unknown_target_id(tmp_path: Path):
    """T032：選了不存在 id → 錯誤訊息。"""
    c = _client(tmp_path)
    r1 = _get_form_page(c)
    hidden = _get_hidden(r1.text)
    data = {**hidden, "_action": "submit", "pref_S01_1": "G99"}
    r = c.post("/match/preferences", data=data)
    assert r.status_code == 200
    assert "填寫志願" in r.text
    assert "無效的對象" in r.text


def test_post_preferences_all_empty_shows_error(tmp_path: Path):
    """T033：全空 prefs + submit → 回填志願頁 + 「請至少為一位參與者填」訊息。"""
    c = _client(tmp_path)
    r1 = _get_form_page(c)
    hidden = _get_hidden(r1.text)
    r = c.post("/match/preferences", data={**hidden, "_action": "submit"})
    assert r.status_code == 200
    assert "填寫志願" in r.text
    assert "請至少為一位參與者填" in r.text


def test_preferences_form_shows_target_summary_with_capacity(tmp_path: Path):
    """T035：候選對象段顯示「程式組（容量 3 人）」等。"""
    c = _client(tmp_path)
    r = _get_form_page(c)
    assert "程式組（容量 3 人）" in r.text
    assert "自然組（容量 3 人）" in r.text
    assert "人文組（容量 3 人）" in r.text


def test_render_preferences_form_with_empty_targets_renders_friendly_error_block():
    """Feature 013 後：targets 為空 tuple → 樣板顯示友善錯誤段。"""
    from unittest.mock import MagicMock
    from matcher.web.routes.match import _render_preferences_form

    request = MagicMock()
    request.app.state.templates = MagicMock()

    class _FakeRole:
        id = "S01"
        attributes = {"name": "A"}

    _render_preferences_form(
        request,
        template_id="x", template_name="X",
        mechanism="M1", seed=1,
        roster_bytes=b"", roster_filename="x.csv",
        roles=[_FakeRole()], targets=tuple(),
        max_choices=3,
    )
    # 驗證 TemplateResponse 被呼叫且 targets_for_options 為 None
    call = request.app.state.templates.TemplateResponse.call_args
    context = call.args[2] if len(call.args) >= 3 else call.kwargs["context"]
    assert context["targets_for_options"] is None
    assert context["roles_for_form"] == [{"id": "S01", "display_name": "A"}]
