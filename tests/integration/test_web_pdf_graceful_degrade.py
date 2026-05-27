"""Feature 010 Phase 6：graceful degrade。"""

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


def _run_m0_record(c: TestClient) -> str:
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def test_web_pdf_503_when_weasyprint_unavailable(tmp_path: Path, monkeypatch):
    """T050：WeasyPrint 不可用時 → 503 + 友善訊息。"""
    monkeypatch.setattr("matcher.web.pdf._WEASYPRINT_AVAILABLE", False)
    c = _client(tmp_path)
    rid = _run_m0_record(c)
    r = c.get(f"/match/{rid}/report.pdf")
    assert r.status_code == 503
    assert "WeasyPrint" in r.text
    assert "README" in r.text


def test_other_endpoints_still_work_without_weasyprint(tmp_path: Path, monkeypatch):
    """T051：缺 WeasyPrint 不影響既有功能。"""
    monkeypatch.setattr("matcher.web.pdf._WEASYPRINT_AVAILABLE", False)
    c = _client(tmp_path)
    rid = _run_m0_record(c)
    assert c.get(f"/match/{rid}").status_code == 200
    assert c.get(f"/match/{rid}/audit").status_code == 200
    assert c.get(f"/match/{rid}/participant/T01").status_code == 200
