"""Feature：從過去紀錄沿用清單（預填填清單頁）。"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.template_loader import TemplateRegistry
from matcher.web.app import create_app

ROSTER = b"id,name,speciality,seniority\nT01,\xe7\x8e\x8b,\xe5\x9c\x8b\xe6\x96\x87,8\n"
TARGETS = ("編號,容量,班級名稱,班級需要的科目清單,班級特色\nC01,2,三年甲班,國文,雙語\n").encode("utf-8")


@pytest.fixture
def client(tmp_path: Path):
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    import matcher.web.routes.pages as pages_mod
    pages_mod._registry = TemplateRegistry(custom_dir=tmp_path / "templates")
    return TestClient(create_app())


def _csrf(c):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get("/match/new").text).group(1)


def _run(client) -> str:
    r = client.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "2026", "mechanism": "M0", "csrf_token": _csrf(client)},
        files={"roster": ("r.csv", io.BytesIO(ROSTER), "text/csv"),
               "targets_yaml": ("t.csv", io.BytesIO(TARGETS), "text/csv")},
        follow_redirects=True,
    )
    return re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text).group(1)


def test_records_list_has_reuse_link(client):
    rid = _run(client)
    body = client.get("/matches").text
    assert "用這份清單再配對" in body
    assert f"from_record={rid}" in body


def test_reuse_prefills_fill_form(client):
    rid = _run(client)
    r = client.get(f"/match/new/fill?template_id=teacher-class&from_record={rid}")
    assert r.status_code == 200
    # 角色與對象都被預填
    assert "王" in r.text
    assert "三年甲班" in r.text
    assert "沿用過去紀錄的清單" in r.text


def test_reuse_unknown_record_404(client):
    r = client.get("/match/new/fill?template_id=teacher-class&from_record=no-such")
    assert r.status_code == 404
