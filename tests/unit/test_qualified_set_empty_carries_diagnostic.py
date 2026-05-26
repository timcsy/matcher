"""Feature 015 Phase 2：QualifiedSetEmpty 攜帶診斷。"""

from __future__ import annotations

import pytest

from matcher.errors import QualifiedSetEmpty
from matcher.filter import filter_qualified
from matcher.roster import Roster, Role, Target
from matcher.rules import Rule, Ruleset
from matcher.rules import parse_expr


def _ruleset_never_pass():
    # role.x 必須等於 "impossible"
    expr = parse_expr({"eq": {"field": "role.x", "value": "impossible"}})
    return Ruleset(rules=(Rule(id="R001", description="x 必須等於 impossible", expr=expr),))


def _roster():
    roles = (Role(id="A", attributes={"x": "foo"}, preferences=()),)
    targets = (Target(id="T1", capacity=1, attributes={}),)
    return Roster(roles=roles, targets=targets)


def test_empty_set_raises_with_diagnostic():
    with pytest.raises(QualifiedSetEmpty) as ei:
        filter_qualified(_ruleset_never_pass(), _roster())
    err = ei.value
    assert err.exit_code == 10
    assert err.total_pairs == 1
    assert err.rule_stats == {"R001": 1}
    assert err.culprit == "R001"
    assert len(err.trace) == 1
    # 原訊息不變（向後相容）
    assert "資格集合為空" in str(err)


def test_qualified_set_empty_still_constructible_plainly():
    """不帶診斷時仍可建（向後相容）。"""
    e = QualifiedSetEmpty("訊息")
    assert e.exit_code == 10
    assert e.rule_stats == {}
    assert e.culprit is None
