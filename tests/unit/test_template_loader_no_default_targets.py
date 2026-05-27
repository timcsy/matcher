"""Feature 013 US1：template_loader 不再產生 default_targets。"""

from __future__ import annotations

import pytest

from pathlib import Path

from matcher.template_loader import parse_template, dump_template_yaml


VALID_YAML_DICT_WITH_LEGACY_FIELD = {
    "schema_version": "1.0",
    "id": "legacy-tpl",
    "name": "舊範本",
    "description": "舊版本的範本，含已廢棄欄位",
    "attributes": {
        "participants": [{"key": "name", "type": "str", "required": True, "description": "姓名"}],
        "targets": [{"key": "name", "type": "str", "required": True, "description": "組名"}],
    },
    "rules": [{"id": "R001", "description": "規則 1", "expr": {"eq": {"field": "participant.name", "value": "x"}}}],
    "default_targets": [  # ← 舊欄位
        {"id": "T1", "capacity": 1, "attributes": {"name": "test"}},
    ],
}


def test_parse_silently_ignores_default_targets_key():
    """含 default_targets 的 YAML 仍可 parse；結果 Template 物件無 default_targets 屬性。"""
    tpl = parse_template(VALID_YAML_DICT_WITH_LEGACY_FIELD)
    assert tpl.id == "legacy-tpl"
    assert not hasattr(tpl, "default_targets"), "Template 應已移除 default_targets 欄位"


def test_dump_never_writes_default_targets(tmp_path: Path):
    """dump_template_yaml 永遠不輸出 default_targets 鍵。"""
    tpl = parse_template(VALID_YAML_DICT_WITH_LEGACY_FIELD)
    out_path = tmp_path / "out.yaml"
    dump_template_yaml(tpl, out_path)
    content = out_path.read_text(encoding="utf-8")
    assert "default_targets" not in content
