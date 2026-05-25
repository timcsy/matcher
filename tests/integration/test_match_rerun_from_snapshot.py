"""Feature 011 US4：以此版本再執行——從 audit.template_snapshot 還原。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def _run_match(c: TestClient) -> str:
    """跑一次 M0 配對，回 record_id。"""
    csv_path = ROOT / "examples" / "teacher-class" / "roster.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "teacher-class", "seed": "123456", "mechanism": "M0"},
            files={"roster": ("roster.csv", f, "text/csv")},
        )
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text)
    return m.group(1)


def test_match_result_has_rerun_button(client: TestClient):
    """T080：結果頁含「用當時的範本版本再跑一次」按鈕。"""
    rid = _run_match(client)
    r = client.get(f"/match/{rid}")
    assert r.status_code == 200
    assert "用當時的範本版本再跑一次" in r.text
    assert f"/match/new?template_snapshot={rid}" in r.text


def test_match_new_with_template_snapshot_param(client: TestClient):
    """T081：GET /match/new?template_snapshot=<rid> 200 + 含「已預載」提示。"""
    rid = _run_match(client)
    r = client.get(f"/match/new?template_snapshot={rid}")
    assert r.status_code == 200
    assert "已預載" in r.text
    assert rid in r.text


def test_match_new_snapshot_for_unknown_record_returns_404(client: TestClient):
    """T083：未知 record id → 404。"""
    r = client.get("/match/new?template_snapshot=no-such-rid")
    assert r.status_code == 404


def test_match_new_snapshot_pre_selects_template(client: TestClient):
    """T082：snapshot 路徑下，下拉預選對應範本。"""
    rid = _run_match(client)
    r = client.get(f"/match/new?template_snapshot={rid}")
    # 範本下拉預選 teacher-class（snapshot 來自 teacher-class）
    assert 'value="teacher-class" selected' in r.text or '"teacher-class" selected' in r.text
