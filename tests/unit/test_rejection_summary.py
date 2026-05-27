"""Feature 015 Phase 2：rejection_summary 純函式。"""

from __future__ import annotations

from matcher.filter import rejection_summary
from matcher.rules import Rule, Ruleset


def _ruleset(*ids):
    return Ruleset(rules=tuple(Rule(id=i, description=f"規則{i}", expr=None) for i in ids))


def test_counts_each_rule_failures():
    # 3 組；R003 全失敗，R001 失敗 1 組，R002 全過
    trace = [
        {"participant_id": "A", "target_id": "X", "matched_rules": ["R001", "R002"]},
        {"participant_id": "A", "target_id": "Y", "matched_rules": ["R002"]},        # R001 也失敗
        {"participant_id": "B", "target_id": "X", "matched_rules": ["R001", "R002"]},
    ]
    out = rejection_summary(trace, _ruleset("R001", "R002", "R003"))
    assert out["total_pairs"] == 3
    assert out["rule_stats"] == {"R001": 1, "R002": 0, "R003": 3}
    assert out["culprit"] == "R003"  # 失敗最多


def test_all_passed_no_culprit():
    trace = [{"participant_id": "A", "target_id": "X", "matched_rules": ["R001"]}]
    out = rejection_summary(trace, _ruleset("R001"))
    assert out["rule_stats"] == {"R001": 0}
    assert out["culprit"] is None


def test_tie_takes_first_in_rule_order():
    trace = [{"participant_id": "A", "target_id": "X", "matched_rules": []}]  # 兩條都失敗
    out = rejection_summary(trace, _ruleset("R001", "R002"))
    assert out["rule_stats"] == {"R001": 1, "R002": 1}
    assert out["culprit"] == "R001"  # 並列 → 規則順序第一
