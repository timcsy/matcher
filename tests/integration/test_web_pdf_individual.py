"""Feature 010 US2：individual PDF 端點。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.web.app import create_app
from matcher.web.pdf import _WEASYPRINT_AVAILABLE

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not _WEASYPRINT_AVAILABLE,
    reason="WeasyPrint 系統依賴不可用",
)


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _run_m1_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": "M1"},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def _run_failed_record(c: TestClient) -> str:
    # 缺欄位的 CSV → teacher-class 失敗
    bad = "姓名,年資\n王老師,8\n".encode("utf-8")
    r = c.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "1", "mechanism": "M0"},
        files={"roster": ("bad.csv", bad, "text/csv")},
    )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def _pdf_text(content: bytes, tmp_path: Path) -> str:
    p = tmp_path / "x.pdf"
    p.write_bytes(content)
    return subprocess.run(
        ["pdftotext", str(p), "-"],
        capture_output=True, text=True, check=True,
    ).stdout


def test_download_individual_pdf_only_contains_own_data(tmp_path: Path):
    """T030：individual PDF 含自己姓名、不含其他學生姓名。"""
    c = _client(tmp_path)
    rid = _run_m1_record(c)
    r = c.get(f"/match/{rid}/role/S01/report.pdf")
    assert r.status_code == 200
    text = _pdf_text(r.content, tmp_path)
    assert "S01" in text
    assert "小明" in text  # roster-m1.csv 的 S01 是小明
    # 不應出現其他學生姓名
    assert "小華" not in text
    assert "小美" not in text


def test_individual_pdf_button_present_in_individual_view(tmp_path: Path):
    """T031：個別查詢頁含「下載 PDF 報告」連結。"""
    c = _client(tmp_path)
    rid = _run_m1_record(c)
    r = c.get(f"/match/{rid}/role/S01")
    assert "下載 PDF 報告" in r.text
    assert f"/match/{rid}/role/S01/report.pdf" in r.text


def test_individual_pdf_404_on_failed_record(tmp_path: Path):
    """T032：failed record → 404。"""
    c = _client(tmp_path)
    rid = _run_failed_record(c)
    r = c.get(f"/match/{rid}/role/S01/report.pdf")
    assert r.status_code == 404


def test_individual_pdf_404_on_unknown_role(tmp_path: Path):
    """T033：role_id 不在 roster → 404。"""
    c = _client(tmp_path)
    rid = _run_m1_record(c)
    r = c.get(f"/match/{rid}/role/S99/report.pdf")
    assert r.status_code == 404
