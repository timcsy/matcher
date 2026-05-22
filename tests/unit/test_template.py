"""US1：Template 資料模型 + parse_template。"""

from __future__ import annotations

import pytest

from matcher.errors import TemplateMissingField, UnknownSchemaVersion
from matcher.template import Template
from matcher.template_loader import parse_template


def _minimal_data():
    return {
        "schema_version": "1.0",
        "id": "tc",
        "name": "教師-班級",
        "description": "說明",
        "attributes": {
            "roles": [{"key": "speciality", "type": "str"}],
            "targets": [{"key": "required_subjects", "type": "list_str"}],
        },
        "rules": [
            {"id": "R001", "description": "說明", "expr": {
                "role_in_target_field": {
                    "role_field": "speciality",
                    "target_field": "required_subjects",
                },
            }},
        ],
    }


def test_parse_minimal_template():
    tpl = parse_template(_minimal_data())
    assert isinstance(tpl, Template)
    assert tpl.id == "tc"
    assert tpl.schema_version == "1.0"
    assert len(tpl.attributes.roles) == 1
    assert len(tpl.attributes.targets) == 1
    assert len(tpl.ruleset.rules) == 1
    assert tpl.ui_fields == ()
    assert tpl.report_fields == ()
    assert tpl.preferences_schema is None


def test_unknown_schema_version_raises():
    data = _minimal_data()
    data["schema_version"] = "2.0"
    with pytest.raises(UnknownSchemaVersion):
        parse_template(data)


def test_missing_top_level_field_raises():
    for missing in ["id", "name", "description", "attributes", "rules"]:
        data = _minimal_data()
        del data[missing]
        with pytest.raises(TemplateMissingField):
            parse_template(data)


def test_attributes_roles_empty_raises():
    data = _minimal_data()
    data["attributes"]["roles"] = []
    with pytest.raises(TemplateMissingField):
        parse_template(data)


def test_unknown_attribute_type_raises():
    data = _minimal_data()
    data["attributes"]["roles"][0]["type"] = "float"
    with pytest.raises(TemplateMissingField):
        parse_template(data)


def test_ui_select_without_options_raises():
    data = _minimal_data()
    data["ui_fields"] = [{"key": "x", "label": "X", "type": "select"}]
    with pytest.raises(TemplateMissingField):
        parse_template(data)


def test_preferences_schema_parsed():
    data = _minimal_data()
    data["preferences_schema"] = {"max_choices": 3, "required": False, "description": "三志願"}
    tpl = parse_template(data)
    assert tpl.preferences_schema is not None
    assert tpl.preferences_schema.max_choices == 3
    assert tpl.preferences_schema.required is False
