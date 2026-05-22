"""US1：TemplateRegistry 與外部模板檔載入。"""

from __future__ import annotations

from pathlib import Path

import pytest

from matcher.errors import TemplateNotFound
from matcher.template_loader import TemplateRegistry, dump_template_yaml, load_template_file


def test_registry_lists_builtin_templates():
    reg = TemplateRegistry()
    ids = reg.list_ids()
    assert "teacher-class" in ids
    assert "study-group" in ids


def test_registry_get_teacher_class():
    reg = TemplateRegistry()
    tpl = reg.get("teacher-class")
    assert tpl.id == "teacher-class"
    assert tpl.schema_version == "1.0"
    assert len(tpl.ruleset.rules) >= 1


def test_registry_get_study_group_has_preferences_schema():
    reg = TemplateRegistry()
    tpl = reg.get("study-group")
    assert tpl.preferences_schema is not None
    assert tpl.preferences_schema.max_choices >= 1


def test_registry_get_not_found():
    reg = TemplateRegistry()
    with pytest.raises(TemplateNotFound):
        reg.get("no-such")


def test_registry_has():
    reg = TemplateRegistry()
    assert reg.has("teacher-class")
    assert not reg.has("no-such")


def test_dump_and_load_template_roundtrip(tmp_path: Path):
    reg = TemplateRegistry()
    tpl = reg.get("teacher-class")
    p = tmp_path / "exported.yaml"
    dump_template_yaml(tpl, p)
    reloaded = load_template_file(p)
    assert reloaded.id == tpl.id
    assert reloaded.schema_version == tpl.schema_version
    assert len(reloaded.ruleset.rules) == len(tpl.ruleset.rules)
    assert len(reloaded.ui_fields) == len(tpl.ui_fields)
