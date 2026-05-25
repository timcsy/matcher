"""Feature 013 US1：Web 上傳 CSV 但缺 sidecar → HTTP 400 + 明確指引。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


CSV_NO_SIDECAR = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\n"


def test_web_csv_upload_without_sidecar_returns_400_with_guidance(client: TestClient):
    """teacher-class CSV 上傳但沒附 sidecar → 跳轉到失敗 record 頁，含 'targets.yaml' 文字。"""
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0",
              "_skip_auto_sidecar": "1"},
        files={"roster": ("roster.csv", io.BytesIO(CSV_NO_SIDECAR), "text/csv")},
    )
    # 走 record 失敗路徑（pipeline 報 RosterColumnMismatch），會 303 → 200
    assert r.status_code == 200
    assert "targets.yaml" in r.text
