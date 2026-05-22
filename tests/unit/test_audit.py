"""US1：稽核紀錄組裝與序列化。"""

from __future__ import annotations

import json
from pathlib import Path

from matcher.audit import build_audit_record, dump_audit_json
from matcher.roster import Role, Roster, Target
from matcher.rules import Eq, Rule, Ruleset


def _sample_audit():
    rs = Ruleset(rules=(Rule("R001", "x=1", Eq("role.x", 1)),))
    roster = Roster(
        roles=(Role("A", {"x": 1}),),
        targets=(Target("T1", capacity=1, attributes={}),),
    )
    qs = {"A": ["T1"]}
    filter_trace = [{"role_id": "A", "target_id": "T1", "qualified": True, "matched_rules": ["R001"]}]
    allocation_trace = [{
        "step": 1, "role_id": "A", "candidates": ["T1"],
        "random_index": 0, "chosen": "T1",
        "remaining_capacity_after": {"T1": 0},
    }]
    assignment = {"A": "T1"}
    return build_audit_record(
        seed=42,
        ruleset=rs,
        roster=roster,
        qualified_set=qs,
        filter_trace=filter_trace,
        allocation_trace=allocation_trace,
        assignment=assignment,
    )


def test_audit_record_required_fields():
    record = _sample_audit()
    for f in [
        "schema_version", "mechanism", "seed", "rules_snapshot", "roster_snapshot",
        "qualified_set", "filter_trace", "allocation_trace", "assignment", "generated_at",
    ]:
        assert f in record, f"稽核紀錄缺欄位 {f}"
    assert record["schema_version"] == "1.0"
    assert record["mechanism"] == "M0"
    assert record["generated_at"] is None


def test_audit_dump_is_deterministic_bytes(tmp_path: Path):
    record = _sample_audit()
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    dump_audit_json(record, p1)
    dump_audit_json(record, p2)
    assert p1.read_bytes() == p2.read_bytes()


def test_audit_dump_preserves_utf8():
    """ensure_ascii=False 保留繁中。"""
    record = _sample_audit()
    record["rules_snapshot"]["rules"][0]["description"] = "中文說明"
    s = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
    assert "中文說明" in s
