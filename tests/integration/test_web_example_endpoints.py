"""Feature 016 US2：範例下載端點。"""

from __future__ import annotations

import csv
import io
import re
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


def test_download_target_example_csv(client):
    r = client.get("/templates/teacher-class/example/targets.csv")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[0] == ["編號", "容量", "班級名稱", "班級需要的科目清單", "班級特色"]


def test_download_participant_example_xlsx(client):
    r = client.get("/templates/teacher-class/example/participants.xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")


def test_example_syncs_with_custom_template(client):
    # 建一個自訂範本，對象屬性含「場地」
    yaml_tpl = """
schema_version: "1.0"
id: my-tpl
name: 我的
description: x
attributes:
  participants:
    - {key: name, type: str, required: true, description: 姓名}
  targets:
    - {key: name, type: str, required: true, description: 組名}
    - {key: venue, type: str, required: true, description: 場地}
rules:
  - {id: R001, description: 規則, expr: {eq: {field: participant.name, value: x}}}
"""
    r = client.post("/templates/save", data={"mode": "advanced", "raw_yaml": yaml_tpl})
    assert r.json().get("ok"), r.text
    rows = list(csv.reader(io.StringIO(
        client.get("/templates/my-tpl/example/targets.csv").content.decode("utf-8-sig"))))
    assert "組名" in rows[0] and "場地" in rows[0]  # 與自訂範本同步


def test_example_unknown_template_404(client):
    assert client.get("/templates/no-such/example/targets.csv").status_code == 404
