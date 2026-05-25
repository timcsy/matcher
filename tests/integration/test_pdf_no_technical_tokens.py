"""Feature 010 SC-004：PDF 文字技術詞零容忍。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.web.app import create_app
from matcher.web.pdf import _WEASYPRINT_AVAILABLE

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint 不可用")

FORBIDDEN = (
    "preference_rank", "random_index", "processing_order", "filter_trace",
    "allocation_trace", "qualified_set", "preferences_schema",
    "default_targets", "max_choices", "preferred_order",
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


def _pdf_text(content: bytes, tmp_path: Path) -> str:
    p = tmp_path / "x.pdf"
    p.write_bytes(content)
    return subprocess.run(
        ["pdftotext", str(p), "-"],
        capture_output=True, text=True, check=True,
    ).stdout


def test_admin_pdf_no_forbidden_tokens(tmp_path: Path):
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    text = _pdf_text(c.get(f"/match/{rid}/report.pdf").content, tmp_path)
    for tok in FORBIDDEN:
        assert tok not in text, f"admin PDF 含禁用 token: {tok}"


def test_individual_pdf_no_forbidden_tokens(tmp_path: Path):
    c = _client(tmp_path)
    rid = _run_m2_record(c)
    text = _pdf_text(c.get(f"/match/{rid}/role/S01/report.pdf").content, tmp_path)
    for tok in FORBIDDEN:
        assert tok not in text, f"individual PDF 含禁用 token: {tok}"
