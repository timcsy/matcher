"""Foundational：humanize_rule_description 純函式測試（先紅）。"""

from __future__ import annotations

from matcher.template import (
    AttributeDecl,
    AttributeSchema,
    PreferencesSchema,
    Template,
)
from matcher.rules import Eq, Rule, Ruleset
from matcher.web.humanize import humanize_rule_description


def _make_template() -> Template:
    return Template(
        schema_version="1.0",
        id="tc",
        name="教師-班級配對",
        description="說明",
        attributes=AttributeSchema(
            participants=(
                AttributeDecl(key="speciality", type="str", description="老師專業科目"),
                AttributeDecl(key="seniority", type="int", description="年資"),
            ),
            targets=(
                AttributeDecl(key="required_subjects", type="list_str", description="班級需要科目"),
                AttributeDecl(key="feature", type="str", description="班級特色"),
            ),
        ),
        ruleset=Ruleset(rules=()),
    )


def test_participant_substitution():
    out = humanize_rule_description("participant.speciality 必須是國文", _make_template())
    assert "您的 老師專業科目" in out
    assert "participant.speciality" not in out


def test_target_substitution():
    out = humanize_rule_description("target.feature 屬於核心三類", _make_template())
    assert "該對象的 班級特色" in out
    assert "target.feature" not in out


def test_multiple_substitutions_in_one_line():
    out = humanize_rule_description(
        "participant.speciality 必須在 target.required_subjects 中",
        _make_template(),
    )
    assert "您的 老師專業科目" in out
    assert "該對象的 班級需要科目" in out
    assert "participant." not in out
    assert "target." not in out


def test_unknown_key_falls_back_to_key():
    out = humanize_rule_description("participant.unknown_field 大於 5", _make_template())
    assert "您的 unknown_field" in out


def test_no_token_returns_original():
    out = humanize_rule_description("這是純中文說明，無技術詞。", _make_template())
    assert out == "這是純中文說明，無技術詞。"


def test_target_unknown_key_falls_back():
    out = humanize_rule_description("target.no_such", _make_template())
    assert "該對象的 no_such" in out


def test_empty_description():
    out = humanize_rule_description("", _make_template())
    assert out == ""
