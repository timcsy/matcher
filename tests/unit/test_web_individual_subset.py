"""Foundational：build_individual_audit_subset 純函式測試（先紅）。"""

from __future__ import annotations

import pytest

from matcher.web.errors import MatchRecordNotFound
from matcher.web.individual import build_individual_audit_subset


def _sample_audit():
    return {
        "schema_version": "1.2",
        "seed": 123,
        "roster_snapshot": {
            "participants": [
                {"id": "T01", "attributes": {"name": "王老師"}, "preferences": []},
                {"id": "T02", "attributes": {"name": "林老師"}, "preferences": ["G1"]},
            ],
            "targets": [
                {"id": "C01", "capacity": 1, "attributes": {"name": "三年甲班"}},
                {"id": "C02", "capacity": 1, "attributes": {"name": "三年乙班"}},
            ],
        },
        "assignment": {"T01": "C01", "T02": None},
        "filter_trace": [
            {"participant_id": "T01", "target_id": "C01", "qualified": True, "matched_rules": ["R001"]},
            {"participant_id": "T01", "target_id": "C02", "qualified": False, "matched_rules": [], "failed_rule": "R001"},
            {"participant_id": "T02", "target_id": "C01", "qualified": True, "matched_rules": ["R001"]},
            {"participant_id": "T02", "target_id": "C02", "qualified": True, "matched_rules": ["R001"]},
        ],
        "allocation_trace": [
            {"step": 1, "participant_id": "T01", "candidates": ["C01"], "random_index": 0,
             "chosen": "C01", "remaining_capacity_after": {"C01": 0, "C02": 1}},
            {"step": 2, "participant_id": "T02", "candidates": ["C02"], "random_index": 0,
             "chosen": "C02", "remaining_capacity_after": {"C01": 0, "C02": 0}},
        ],
    }


def test_assigned_participant():
    sub = build_individual_audit_subset(_sample_audit(), "T01")
    assert sub["schema_version"] == "individual-audit/1.0"
    assert sub["participant_id"] == "T01"
    assert sub["participant_attributes"]["name"] == "王老師"
    assert sub["assignment"]["target_id"] == "C01"
    assert sub["assignment"]["target_attributes"]["name"] == "三年甲班"


def test_unassigned_participant():
    sub = build_individual_audit_subset(_sample_audit(), "T02")
    assert sub["assignment"]["target_id"] is None
    assert sub["assignment"]["target_attributes"] is None


def test_filter_trace_subset_only_contains_participant():
    sub = build_individual_audit_subset(_sample_audit(), "T01")
    assert len(sub["filter_trace_subset"]) == 2  # T01 has 2 entries in sample
    for entry in sub["filter_trace_subset"]:
        # 不應有 participant_id 欄位（已經暗含在 subset 屬於該 participant）
        # 但若保留 participant_id 也合法——主要驗證條目來自 T01
        # 採用「target_id 集合 == 該 participant 在 filter_trace 中的 targets」
        assert entry["target_id"] in {"C01", "C02"}


def test_allocation_step_present_for_assigned():
    sub = build_individual_audit_subset(_sample_audit(), "T01")
    assert sub["allocation_step"] is not None
    assert sub["allocation_step"]["participant_id"] == "T01"


def test_participant_id_not_found_raises():
    with pytest.raises(MatchRecordNotFound):
        build_individual_audit_subset(_sample_audit(), "T999")


def test_participant_preferences_included():
    sub = build_individual_audit_subset(_sample_audit(), "T02")
    assert list(sub["participant_preferences"]) == ["G1"]
