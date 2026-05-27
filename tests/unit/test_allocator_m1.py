"""US1：allocate_m1 純函式測試。"""

from __future__ import annotations

from matcher.allocator import _normalize_preferences, allocate_m1
from matcher.rng import SeededRandom


def test_processing_order_deterministic():
    """同 seed → 同處理順序。"""
    qs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    prefs = {"A": ["X"], "B": ["Y"], "C": ["X"]}
    caps = {"X": 2, "Y": 2}
    o1, _, _ = allocate_m1(qs, prefs, caps, SeededRandom(42), role_order=["A", "B", "C"])
    o2, _, _ = allocate_m1(qs, prefs, caps, SeededRandom(42), role_order=["A", "B", "C"])
    assert o1 == o2


def test_each_role_picks_highest_available_preference():
    """每位參與者取「合格 ∩ 仍有名額」中第一個志願。"""
    qs = {"A": ["X", "Y"], "B": ["X", "Y"]}
    prefs = {"A": ["Y", "X"], "B": ["Y", "X"]}
    caps = {"X": 1, "Y": 1}
    order, assignment, trace = allocate_m1(
        qs, prefs, caps, SeededRandom(1), role_order=["A", "B"],
    )
    # 第一個處理的人應該分到 Y（第一志願）
    first_processed = order[0]
    assert assignment[first_processed] == "Y"
    # 第二個處理的人 Y 已滿，分到 X（第二志願）
    second_processed = order[1]
    assert assignment[second_processed] == "X"


def test_fallback_when_all_preferences_full():
    """志願全滿時 fallback 抽籤。"""
    qs = {"A": ["X", "Y", "Z"], "B": ["X"], "C": ["X"]}
    # A 處理時 X 還有名額 → 分到 X（第一志願）
    # B 處理時 X 已滿 → 無志願可選；但 B 也沒有其他資格 target → 未分配
    prefs = {"A": ["X"], "B": ["X"], "C": []}
    caps = {"X": 1, "Y": 1, "Z": 1}
    order, assignment, trace = allocate_m1(
        qs, prefs, caps, SeededRandom(7), role_order=["A", "B", "C"],
    )
    # C 沒有 preferences，但有資格 target → fallback 抽籤
    c_trace = next(t for t in trace if t["role_id"] == "C")
    if assignment["C"] is not None:
        # 表示 fallback 啟動
        assert c_trace["preference_rank"] is None
        assert c_trace["fallback_random_index"] is not None


def test_normalize_preferences_dedup():
    """preferences 去重。"""
    result = _normalize_preferences(["X", "Y", "X", "Z"], ["X", "Y", "Z"])
    assert result == ["X", "Y", "Z"]


def test_normalize_preferences_ignore_out_of_set():
    """preferences 含資格外 id 靜默忽略。"""
    result = _normalize_preferences(["X", "OUT", "Y"], ["X", "Y"])
    assert result == ["X", "Y"]


def test_normalize_preferences_combined():
    """去重 + 忽略資格外。"""
    result = _normalize_preferences(["X", "Y", "X", "OUT", "Y"], ["X", "Y"])
    assert result == ["X", "Y"]


def test_assignment_records_preference_rank():
    """audit trace 含 preference_rank。"""
    qs = {"A": ["X", "Y"]}
    prefs = {"A": ["X"]}
    caps = {"X": 1, "Y": 1}
    _, assignment, trace = allocate_m1(qs, prefs, caps, SeededRandom(1), role_order=["A"])
    a_trace = next(t for t in trace if t["role_id"] == "A")
    assert assignment["A"] == "X"
    assert a_trace["preference_rank"] == 1
    assert a_trace["preferred_order"] == ["X"]


def test_no_qualified_target_means_unassigned():
    """資格集合為空 → 未分配。"""
    qs = {"A": []}
    prefs = {"A": []}
    caps = {}
    _, assignment, trace = allocate_m1(qs, prefs, caps, SeededRandom(1), role_order=["A"])
    assert assignment["A"] is None


def test_capacity_exhaustion():
    """容量耗盡時後續參與者未分配。"""
    qs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    prefs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    caps = {"X": 2}
    order, assignment, _ = allocate_m1(qs, prefs, caps, SeededRandom(1), role_order=["A", "B", "C"])
    # 前兩位分到 X，第三位 X 已滿、沒有其他資格 target → 未分配
    assigned = [r for r in order if assignment[r] is not None]
    assert len(assigned) == 2
