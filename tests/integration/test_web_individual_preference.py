"""Feature 008 US2：個別查詢頁的志願滿足度三分支。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_TECHNICAL_TOKENS = (
    "preference_rank", "processing_order", "tie_break_random_index",
    "fallback_random_index", "preferred_order",
)


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _make_m_record(c: TestClient, mechanism: str) -> tuple[str, dict]:
    """跑 study-group + roster-m1.csv 並回 (record_id, audit)。"""
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": mechanism},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    assert r.status_code == 200
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text)
    rid = m.group(1)
    audit = json.loads(c.get(f"/match/{rid}/audit").content)
    return rid, audit


def _make_m0_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def test_shows_preference_rank_when_assigned_to_preferred(tmp_path: Path):
    """T030：M1 + 第 N 志願文案。"""
    c = _client(tmp_path)
    rid, audit = _make_m_record(c, "M1")
    # 找一位 preference_rank 非 null 的參與者
    participant_id = None
    for entry in audit["allocation_trace"]:
        if entry.get("preference_rank") is not None:
            participant_id = entry["participant_id"]
            break
    assert participant_id is not None, "M1 跑出來竟然完全沒有按志願分到的參與者"
    r = c.get(f"/match/{rid}/participant/{participant_id}")
    assert r.status_code == 200
    rank = next(e["preference_rank"] for e in audit["allocation_trace"] if e["participant_id"] == participant_id)
    assert f"您被分到第 {rank} 志願" in r.text


def test_shows_fallback_with_preferences_text_or_skip(tmp_path: Path):
    """T031：fallback + 有志願 文案（若 roster-m1 全部命中志願，跳過此測試）。"""
    import pytest
    c = _client(tmp_path)
    rid, audit = _make_m_record(c, "M1")
    participant_id = None
    for entry in audit["allocation_trace"]:
        if entry.get("preference_rank") is None and entry.get("fallback_random_index") is not None:
            rid_in_roster = next(
                (r for r in audit["roster_snapshot"]["participants"] if r["id"] == entry["participant_id"]),
                None,
            )
            if rid_in_roster and len(rid_in_roster.get("preferences", [])) > 0:
                participant_id = entry["participant_id"]
                break
    if participant_id is None:
        pytest.skip("roster-m1.csv 中無 fallback 且有志願 的參與者（資料相依）")
    r = c.get(f"/match/{rid}/participant/{participant_id}")
    assert r.status_code == 200
    assert "您原本的志願已被分配給其他人" in r.text
    assert "由公平抽籤分到" in r.text


def test_shows_fallback_without_preferences_text_or_skip(tmp_path: Path):
    """T032：fallback + 無志願 文案（若 roster-m1 所有參與者皆有志願，跳過）。"""
    import pytest
    c = _client(tmp_path)
    rid, audit = _make_m_record(c, "M1")
    participant_id = None
    for entry in audit["allocation_trace"]:
        if entry.get("preference_rank") is None and entry.get("fallback_random_index") is not None:
            rid_in_roster = next(
                (r for r in audit["roster_snapshot"]["participants"] if r["id"] == entry["participant_id"]),
                None,
            )
            if rid_in_roster and len(rid_in_roster.get("preferences", [])) == 0:
                participant_id = entry["participant_id"]
                break
    if participant_id is None:
        pytest.skip("roster-m1.csv 中無 fallback 且無志願 的參與者（資料相依）")
    r = c.get(f"/match/{rid}/participant/{participant_id}")
    assert r.status_code == 200
    assert "您未在志願清單中" in r.text


def test_m0_individual_page_omits_preference_section(tmp_path: Path):
    """T033：M0 路徑不顯示三分支文案。"""
    c = _client(tmp_path)
    rid = _make_m0_record(c)
    r = c.get(f"/match/{rid}/participant/T01")
    assert r.status_code == 200
    assert "您被分到第" not in r.text
    assert "由公平抽籤分到" not in r.text
    # 但既有的「您被分到：」應仍在
    assert "您被分到" in r.text


def test_no_technical_tokens_in_individual_html(tmp_path: Path):
    """T034：個別頁不含 feature 008 相關技術 token。"""
    c = _client(tmp_path)
    rid, audit = _make_m_record(c, "M2")
    # 多看幾位
    for participant in audit["roster_snapshot"]["participants"][:3]:
        r = c.get(f"/match/{rid}/participant/{participant['id']}")
        for token in FORBIDDEN_TECHNICAL_TOKENS:
            assert token not in r.text, f"token {token} 出現於 participant {participant['id']}"
