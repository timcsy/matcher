"""Feature 017 regression：範本欄位沒填完整時，/templates/save 回友善 JSON 400，
不可冒泡成 500（前端 fetch 會 JSON.parse 失敗）。"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from matcher.web.app import create_app


def _client():
    return TestClient(create_app())


def _csrf(c) -> str:
    html = c.get("/templates/new").text
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else ""


def test_save_empty_roles_returns_friendly_json_not_500():
    c = _client()
    # 模擬 simple 模式：只填了範本基本資訊，參與者欄位空白（key 未填）
    data = {
        "mode": "simple",
        "csrf_token": _csrf(c),
        "template_id": "x-incomplete",
        "template_name": "未填完整",
        "template_description": "測試",
        "role_attr_0_key": "",            # 空 → attributes.roles 會是空
        "target_attr_0_key": "cls",
        "target_attr_0_type": "str",
    }
    r = c.post("/templates/save", data=data)
    assert r.status_code == 400, r.text
    body = r.json()             # 必須是合法 JSON（非 HTML 500 頁）
    assert body["ok"] is False
    assert body["errors"]
