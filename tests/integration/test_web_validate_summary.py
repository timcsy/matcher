"""回歸：範本檢查通過訊息不可再引用已移除的 default_targets（feature 013 拔除）。"""

from __future__ import annotations

from pathlib import Path


def test_template_form_js_no_default_target_count():
    js = (Path(__file__).resolve().parents[2]
          / "src" / "matcher" / "web" / "static" / "template_form.js").read_text(encoding="utf-8")
    # showResult 曾引用 summary.default_target_count → 顯示「預設對象 undefined 個」
    assert "default_target_count" not in js


def test_validate_summary_has_no_default_target():
    import re

    from fastapi.testclient import TestClient

    from matcher.web.app import create_app

    c = TestClient(create_app())
    html = c.get("/templates/new").text
    csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    r = c.post("/templates/validate", data={
        "mode": "simple", "csrf_token": csrf,
        "template_id": "x-ok", "template_name": "n", "template_description": "d",
        "participant_attr_0_key": "name", "participant_attr_0_type": "str",
        "target_attr_0_key": "cls", "target_attr_0_type": "str",
        "rule_0_id": "R001", "rule_0_type": "eq",
        "rule_0_field": "participant.name", "rule_0_value": "x",
    })
    body = r.json()
    assert body["ok"] is True, body
    assert "default_target_count" not in body["summary"]
    assert set(body["summary"]["attribute_count"]) == {"participants", "targets"}
