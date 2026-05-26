"""Feature 015 US1+US2：Web 空資格集合診斷（CSV 上傳 record + UI 填回填）。"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app

BAD_SIDECAR = b"""targets:
  - id: C01
    capacity: 2
    attributes: {name: "\xe7\x94\xb2\xe7\x8f\xad", required_subjects: ["\xe5\x9c\x8b\xe6\x96\x87"], feature: "\xe7\x84\xa1\xe6\x95\x88"}
"""
CSV = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\n"

FORBIDDEN = ("filter_trace", "qualified_set", "exit_code", "role.", "target.")


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def test_csv_upload_empty_set_shows_culprit(client: TestClient):
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "1", "mechanism": "M0"},
        files={"roster": ("r.csv", io.BytesIO(CSV), "text/csv"),
               "targets_yaml": ("r.targets.yaml", io.BytesIO(BAD_SIDECAR), "application/x-yaml")},
        follow_redirects=True,
    )
    assert r.status_code == 200
    # 失敗頁顯示元兇規則 R003 描述 + 卡住組數，無技術 token
    assert "班級特色" in r.text
    assert "最可能的原因" in r.text
    for tok in FORBIDDEN:
        assert tok not in r.text, f"失敗頁含技術 token: {tok}"


def test_fill_form_empty_set_refills_with_diagnostic(client: TestClient):
    """US2：UI 填名單觸發空集合 → 回填名單頁、保留輸入 + 診斷。"""
    form = {
        "template_id": "teacher-class", "seed": "1", "mechanism": "M0",
        "role_0_name": "王老師", "role_0_speciality": "國文", "role_0_seniority": "8",
        # 班級特色填無效 → R003 全失敗
        "target_0_id": "C01", "target_0_capacity": "2", "target_0_name": "甲班",
        "target_0_required_subjects": "國文", "target_0_feature": "無效",
    }
    r = client.post("/match/run-from-form", data=form, follow_redirects=False)
    assert r.status_code == 400  # 回填頁（非 303 跳走存死 record）
    assert "填名單" in r.text
    # 保留輸入
    assert "王老師" in r.text
    # 診斷（元兇規則描述）
    assert "班級特色" in r.text
    for tok in FORBIDDEN:
        assert tok not in r.text
