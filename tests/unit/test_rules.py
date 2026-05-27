"""US1：規則表達式求值與規則互斥偵測。"""

from __future__ import annotations

import pytest

from matcher.errors import RuleContradiction, UnknownAttribute
from matcher.rules import (
    And,
    Eq,
    Ge,
    In,
    Le,
    Not,
    Or,
    ParticipantInTargetField,
    Rule,
    Ruleset,
    detect_contradictions,
    evaluate,
    first_failed_rule,
    matched_rules,
    parse_expr,
    parse_ruleset,
)


# ── 各 AST 節點求值 ─────────────────────────────────────────────────


def test_eq_true():
    assert evaluate(Eq("participant.speciality", "國文"), {"speciality": "國文"}, {}) is True


def test_eq_false():
    assert evaluate(Eq("participant.speciality", "國文"), {"speciality": "數學"}, {}) is False


def test_in_passes():
    assert evaluate(In("target.feature", ["bilingual", "stem"]), {}, {"feature": "stem"}) is True


def test_in_fails():
    assert evaluate(In("target.feature", ["bilingual"]), {}, {"feature": "stem"}) is False


def test_ge_and_le():
    assert evaluate(Ge("participant.seniority", 5), {"seniority": 6}, {}) is True
    assert evaluate(Ge("participant.seniority", 5), {"seniority": 5}, {}) is True
    assert evaluate(Ge("participant.seniority", 5), {"seniority": 4}, {}) is False
    assert evaluate(Le("participant.seniority", 5), {"seniority": 5}, {}) is True
    assert evaluate(Le("participant.seniority", 5), {"seniority": 6}, {}) is False


def test_participant_in_target_field_list():
    expr = ParticipantInTargetField(participant_field="speciality", target_field="required_subjects")
    assert evaluate(expr, {"speciality": "國文"}, {"required_subjects": ["國文", "數學"]}) is True
    assert evaluate(expr, {"speciality": "歷史"}, {"required_subjects": ["國文", "數學"]}) is False


def test_and_or_not():
    e1 = Eq("participant.x", 1)
    e2 = Eq("participant.y", 2)
    assert evaluate(And((e1, e2)), {"x": 1, "y": 2}, {}) is True
    assert evaluate(And((e1, e2)), {"x": 1, "y": 3}, {}) is False
    assert evaluate(Or((e1, e2)), {"x": 1, "y": 3}, {}) is True
    assert evaluate(Or((e1, e2)), {"x": 9, "y": 3}, {}) is False
    assert evaluate(Not(e1), {"x": 9}, {}) is True
    assert evaluate(Not(e1), {"x": 1}, {}) is False


def test_unknown_attribute_raises():
    with pytest.raises(UnknownAttribute):
        evaluate(Eq("participant.missing", 1), {"speciality": "國文"}, {})
    with pytest.raises(UnknownAttribute):
        evaluate(Eq("target.missing", 1), {}, {"feature": "stem"})


# ── matched_rules / first_failed_rule ───────────────────────────────


def _ruleset(*rules: Rule) -> Ruleset:
    return Ruleset(rules=tuple(rules))


def test_matched_rules_returns_passing_only():
    rs = _ruleset(
        Rule("R001", "x=1", Eq("participant.x", 1)),
        Rule("R002", "y=2", Eq("participant.y", 2)),
    )
    ms = matched_rules(rs, {"x": 1, "y": 9}, {})
    assert [m.id for m in ms] == ["R001"]


def test_first_failed_rule_picks_first():
    rs = _ruleset(
        Rule("R001", "x=1", Eq("participant.x", 1)),
        Rule("R002", "y=2", Eq("participant.y", 2)),
    )
    assert first_failed_rule(rs, {"x": 1, "y": 9}, {}).id == "R002"
    assert first_failed_rule(rs, {"x": 1, "y": 2}, {}) is None


# ── parse_expr / parse_ruleset ──────────────────────────────────────


def test_parse_expr_all_nodes():
    node = {"and": [
        {"eq": {"field": "participant.x", "value": 1}},
        {"or": [
            {"in": {"field": "target.f", "set": ["a", "b"]}},
            {"not": {"ge": {"field": "participant.y", "value": 3}}},
        ]},
        {"participant_in_target_field": {"participant_field": "s", "target_field": "subs"}},
        {"le": {"field": "participant.z", "value": 10}},
    ]}
    expr = parse_expr(node)
    assert isinstance(expr, And)
    assert len(expr.children) == 4


def test_parse_ruleset_basic():
    data = {
        "version": "1.0",
        "rules": [
            {"id": "R001", "description": "說明", "expr": {"eq": {"field": "participant.x", "value": 1}}}
        ],
    }
    rs = parse_ruleset(data)
    assert len(rs.rules) == 1
    assert rs.rules[0].id == "R001"


# ── 規則互斥偵測（US2 預先放在此模組內，但僅在規則層）──────────


def test_detect_contradictions_clean():
    rs = _ruleset(Rule("R001", "x=1", Eq("participant.x", 1)))
    detect_contradictions(rs)  # 無異常


def test_detect_contradictions_clash():
    rs = _ruleset(
        Rule("R001", "矛盾", And((
            Eq("participant.x", 1),
            Not(Eq("participant.x", 1)),
        )))
    )
    with pytest.raises(RuleContradiction):
        detect_contradictions(rs)
