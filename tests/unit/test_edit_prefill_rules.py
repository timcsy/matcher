"""Feature 021 #1：編輯範本時，原本的規則要被預填回表單（_template_to_form_dict）。"""

from __future__ import annotations

from matcher.template_loader import TemplateRegistry
from matcher.web.routes.pages import _template_to_form_dict


def test_edit_prefill_includes_rules():
    tpl = TemplateRegistry().get("teacher-class")
    d = _template_to_form_dict(tpl)
    # teacher-class 有 R001(participant_in_target_field)、R002(ge)、R003(in)
    assert d["rule_0_id"] == "R001"
    assert d["rule_0_type"] == "participant_in_target_field"
    assert d["rule_0_participant_field"] == "speciality"
    assert d["rule_0_target_field"] == "required_subjects"

    assert d["rule_1_type"] == "ge"
    assert d["rule_1_field"] == "participant.seniority"
    assert d["rule_1_value"] == "3"

    assert d["rule_2_type"] == "in"
    assert d["rule_2_field"] == "target.feature"
    # set 以分號串接
    assert set(d["rule_2_set"].split(";")) == {"雙語", "stem", "藝術"}


def test_edit_prefill_keeps_existing_description():
    tpl = TemplateRegistry().get("teacher-class")
    d = _template_to_form_dict(tpl)
    # 既有描述要帶回 custom_description，避免重存時被自動描述覆蓋
    assert d["rule_1_custom_description"] == "老師年資至少 3 年（含）以上"
