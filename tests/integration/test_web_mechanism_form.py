"""Feature 008：Web UI 機制選擇相關整合測試。

涵蓋 Phase 2 foundational + US1 表單下拉、結果頁機制名/處理順序/志願排名欄。
"""

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


def _extract_record_id(text: str) -> str:
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', text)
    assert m, "結果頁無 record_id"
    return m.group(1)


# ── Phase 2 Foundational ──────────────────────────────────────────

def test_match_run_accepts_mechanism_m0(tmp_path: Path):
    """T001：M0 顯式傳入，記錄 audit.mechanism == 'M0'。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    assert r.status_code == 200, r.text
    rid = _extract_record_id(r.text)
    audit = json.loads(c.get(f"/match/{rid}/audit").content)
    assert audit["mechanism"] == "M0"


def test_match_run_rejects_invalid_mechanism(tmp_path: Path):
    """T002：非法 mechanism 值回 400。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "1", "mechanism": "M9"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    assert r.status_code == 400, r.text
    assert "不支援的機制" in r.text
    assert "M9" in r.text


def test_match_run_normalizes_lowercase_mechanism(tmp_path: Path):
    """T003：'m1' 規範化為 'M1' 並成功跑 M1。"""
    c = _client(tmp_path)
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": "m1"},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    assert r.status_code == 200, r.text
    rid = _extract_record_id(r.text)
    audit = json.loads(c.get(f"/match/{rid}/audit").content)
    assert audit["mechanism"] == "M1"


# ── US1：表單 + 結果頁 ────────────────────────────────────────────

def test_new_match_form_has_mechanism_select(tmp_path: Path):
    """T010：表單含 3 個 option，M0 為 selected。"""
    c = _client(tmp_path)
    r = c.get("/match/new")
    assert r.status_code == 200
    assert 'name="mechanism"' in r.text
    assert 'value="M0"' in r.text
    assert 'value="M1"' in r.text
    assert 'value="M2"' in r.text
    # M0 應為 selected
    assert re.search(r'<option[^>]*value="M0"[^>]*selected', r.text), r.text


def _run_m2_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": "M2"},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    assert r.status_code == 200, r.text
    return _extract_record_id(r.text)


def _run_m0_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    return _extract_record_id(r.text)


def test_result_page_shows_mechanism_label_m2(tmp_path: Path):
    """T011：M2 結果頁含「M2 Boston 層級填滿」。"""
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    r = c.get(f"/match/{rid}")
    assert r.status_code == 200
    assert "M2 Boston 層級填滿" in r.text


def test_result_page_shows_processing_order_m1m2(tmp_path: Path):
    """T012：M2 結果頁含「處理順序」段；M0 不含。"""
    c = _client(tmp_path)
    rid_m2 = _run_m2_record(c)
    r = c.get(f"/match/{rid_m2}")
    assert "處理順序" in r.text

    rid_m0 = _run_m0_record(c)
    r0 = c.get(f"/match/{rid_m0}")
    assert "處理順序" not in r0.text


def test_result_page_shows_preference_rank_column(tmp_path: Path):
    """T013：M2 結果頁含「志願排名」欄；M0 不含。"""
    c = _client(tmp_path)
    rid_m2 = _run_m2_record(c)
    r = c.get(f"/match/{rid_m2}")
    assert "志願排名" in r.text
    assert ("第 1 志願" in r.text) or ("第 2 志願" in r.text) or ("抽籤" in r.text), r.text

    rid_m0 = _run_m0_record(c)
    r0 = c.get(f"/match/{rid_m0}")
    assert "志願排名" not in r0.text


def test_no_technical_tokens_in_result_html(tmp_path: Path):
    """T016：結果頁 HTML 不含技術 token。"""
    c = _client(tmp_path)
    for rid in (_run_m2_record(c), _run_m0_record(c)):
        r = c.get(f"/match/{rid}")
        for token in FORBIDDEN_TECHNICAL_TOKENS:
            assert token not in r.text, f"頁面含禁用 token: {token}"
