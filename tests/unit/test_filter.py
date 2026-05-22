"""US1：過濾階段。"""

from __future__ import annotations

import pytest

from matcher.errors import QualifiedSetEmpty
from matcher.filter import filter_qualified
from matcher.roster import Role, Roster, Target
from matcher.rules import Eq, Rule, Ruleset


def _make_simple():
    rs = Ruleset(rules=(Rule("R001", "x相符", Eq("role.x", "match")),))
    roster = Roster(
        roles=(
            Role("A", {"x": "match"}),
            Role("B", {"x": "nomatch"}),
        ),
        targets=(Target("T1", capacity=2, attributes={"x": "match"}),),
    )
    return rs, roster


def test_filter_produces_correct_qualified_set():
    rs, roster = _make_simple()
    qs, trace = filter_qualified(rs, roster)
    assert qs == {"A": ["T1"], "B": []}


def test_filter_trace_per_pair():
    rs, roster = _make_simple()
    _, trace = filter_qualified(rs, roster)
    pairs = {(t["role_id"], t["target_id"]): t for t in trace}
    assert pairs[("A", "T1")]["qualified"] is True
    assert pairs[("A", "T1")]["matched_rules"] == ["R001"]
    assert pairs[("B", "T1")]["qualified"] is False
    assert pairs[("B", "T1")]["failed_rule"] == "R001"


def test_filter_raises_when_all_empty():
    rs = Ruleset(rules=(Rule("R001", "永遠不符", Eq("role.x", "no_one_has_this")),))
    roster = Roster(
        roles=(Role("A", {"x": "a"}), Role("B", {"x": "b"})),
        targets=(Target("T1", capacity=1, attributes={"x": "t"}),),
    )
    with pytest.raises(QualifiedSetEmpty):
        filter_qualified(rs, roster)
