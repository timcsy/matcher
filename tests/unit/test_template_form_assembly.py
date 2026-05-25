"""Feature 011 Phase 2：template_form.assemble_template_yaml + auto_description 純函式測試。"""

from __future__ import annotations

import pytest

from matcher.template_loader import parse_template
from matcher.web.template_form import (
    SCENARIO_TEMPLATES,
    _auto_description,
    assemble_template_yaml,
)

# 技術詞清單沿用 008/009/010
FORBIDDEN_TOKENS = (
    "preference_rank", "random_index", "processing_order",
    "filter_trace", "allocation_trace", "qualified_set",
    "preferences_schema", "default_targets", "max_choices", "preferred_order",
)


def test_assemble_simple_form_to_yaml_dict():
    """T017：5 attrs + 2 rules + 3 default_targets 表單 → parse_template 通過。"""
    form = {
        "template_id": "my-test",
        "template_name": "測試",
        "template_description": "單元測試",
        "role_attr_0_key": "name", "role_attr_0_type": "str", "role_attr_0_required": "on",
        "role_attr_0_description": "姓名",
        "role_attr_1_key": "grade", "role_attr_1_type": "int", "role_attr_1_required": "on",
        "role_attr_1_description": "年級",
        "target_attr_0_key": "name", "target_attr_0_type": "str", "target_attr_0_required": "on",
        "target_attr_0_description": "對象名",
        "rule_0_id": "R001", "rule_0_type": "ge",
        "rule_0_field": "role.grade", "rule_0_value": "4",
        "target_0_id": "T01", "target_0_capacity": "3", "target_0_name": "甲組",
        "target_1_id": "T02", "target_1_capacity": "3", "target_1_name": "乙組",
        "target_2_id": "T03", "target_2_capacity": "3", "target_2_name": "丙組",
    }
    tpl_dict = assemble_template_yaml(form)
    # parse_template 不應 raise
    tpl = parse_template(tpl_dict)
    assert tpl.id == "my-test"
    assert tpl.name == "測試"
    assert len(tpl.attributes.roles) == 2
    assert len(tpl.ruleset.rules) == 1
    assert len(tpl.default_targets) == 3


def test_auto_description_for_each_rule_type():
    """T018：5 規則類型生成的 description 合理且無技術 token。"""
    attrs = {
        "roles": [
            {"key": "grade", "description": "年級"},
            {"key": "speciality", "description": "專業科目"},
        ],
        "targets": [
            {"key": "subject", "description": "科目"},
            {"key": "required_subjects", "description": "需要科目"},
        ],
    }
    cases = [
        ("ge", {"field": "role.grade", "value": "4"}, "年級 必須 ≥ 4"),
        ("le", {"field": "role.grade", "value": "6"}, "年級 必須 ≤ 6"),
        ("eq", {"field": "role.speciality", "value": "數學"}, "專業科目 必須等於 數學"),
        ("in", {"field": "role.speciality", "set": "國文;數學"}, "專業科目 必須屬於：國文、數學"),
        ("role_in_target_field", {"role_field": "speciality", "target_field": "required_subjects"},
         "專業科目 必須出現在對象的需要科目列表中"),
    ]
    for rule_type, fields, expected_desc in cases:
        desc = _auto_description(rule_type, fields, attrs)
        assert desc == expected_desc, f"{rule_type} → {desc}"
        for tok in FORBIDDEN_TOKENS:
            assert tok not in desc, f"{rule_type}: contains forbidden {tok}"


def test_custom_description_overrides_auto():
    """T019：rule_<i>_custom_description 若提供，使用者版本生效。"""
    form = {
        "template_id": "x", "template_name": "X", "template_description": "X",
        "role_attr_0_key": "grade", "role_attr_0_type": "int", "role_attr_0_required": "on",
        "role_attr_0_description": "年級",
        "target_attr_0_key": "name", "target_attr_0_type": "str", "target_attr_0_required": "on",
        "target_attr_0_description": "對象名",
        "rule_0_id": "R001", "rule_0_type": "ge",
        "rule_0_field": "role.grade", "rule_0_value": "4",
        "rule_0_custom_description": "使用者自己寫的說明",
    }
    tpl_dict = assemble_template_yaml(form)
    assert tpl_dict["rules"][0]["description"] == "使用者自己寫的說明"


def test_scenario_template_constants_all_valid():
    """T020：SCENARIO_TEMPLATES 各預設場景皆能 assemble + parse_template 通過。"""
    for scenario_id, form in SCENARIO_TEMPLATES.items():
        if scenario_id == "blank":
            continue  # 空白模板不期待能 parse
        tpl_dict = assemble_template_yaml(form)
        try:
            parse_template(tpl_dict)
        except Exception as e:
            pytest.fail(f"場景 `{scenario_id}` parse_template 失敗：{e}\nYAML: {tpl_dict}")
