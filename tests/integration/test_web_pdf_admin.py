"""Feature 010 US1：admin PDF 端點。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.web.app import create_app
from matcher.web.pdf import _WEASYPRINT_AVAILABLE

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not _WEASYPRINT_AVAILABLE,
    reason="WeasyPrint 系統依賴不可用，跳過 PDF 整合測試",
)


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _run_m2_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": "M2"},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def _run_failed_record(c: TestClient) -> str:
    csv = b"id,\xe5\xa7\x93\xe5\x90\x8d,\xe5\xb9\xb4\xe7\xb4\x9a,\xe5\xbf\x97\xe9\xa1\x98\xe7\xb5\x84\xe5\x88\xa5\nS01,A,5,G1\n"
    r = c.post(
        "/match/run",
        data={"template_id": "study-group", "seed": "1", "mechanism": "M0"},
        files={"roster": ("e.csv", csv, "text/csv")},
    )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def test_download_admin_pdf_returns_pdf_bytes(tmp_path: Path):
    """T020：成功 record → 200 + PDF。"""
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    r = c.get(f"/match/{rid}/report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers.get("content-disposition", "")
    assert f"{rid}.report.pdf" in r.headers["content-disposition"]
    assert r.content[:8].startswith(b"%PDF-")


def test_admin_pdf_contains_record_id_and_mechanism_label(tmp_path: Path):
    """T021：PDF 文字含 record_id 與機制名稱。"""
    import subprocess
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    r = c.get(f"/match/{rid}/report.pdf")
    pdf_path = tmp_path / "out.pdf"
    pdf_path.write_bytes(r.content)
    text = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert rid in text
    assert "M2 Boston 層級填滿" in text


def test_admin_pdf_for_failed_record_shows_error(tmp_path: Path):
    """T022：失敗 record 仍有 PDF（顯示失敗版）。"""
    c = _client(tmp_path)
    rid = _run_failed_record(c)
    r = c.get(f"/match/{rid}/report.pdf")
    assert r.status_code == 200
    assert r.content[:8].startswith(b"%PDF-")


def test_admin_pdf_button_present_in_result_html(tmp_path: Path):
    """T023：結果頁含「下載 PDF 報告」連結。"""
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    r = c.get(f"/match/{rid}")
    assert "下載 PDF 報告" in r.text
    assert f"/match/{rid}/report.pdf" in r.text


def test_admin_pdf_record_not_found(tmp_path: Path):
    """T024：不存在的 record → 404。"""
    c = _client(tmp_path)
    r = c.get("/match/no-such-record/report.pdf")
    assert r.status_code == 404
