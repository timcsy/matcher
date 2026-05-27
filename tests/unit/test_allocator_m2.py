"""US1：allocate_m2 純函式測試。"""

from __future__ import annotations

from matcher.allocator import allocate_m2
from matcher.rng import SeededRandom


def test_m2_no_oversubscription_all_get_first_pref():
    """無超額情境：所有人都拿到第 1 志願。"""
    qs = {"A": ["X", "Y"], "B": ["X", "Y"]}
    prefs = {"A": ["X"], "B": ["Y"]}
    caps = {"X": 1, "Y": 1}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(1), role_order=["A", "B"],
    )
    assert assignment["A"] == "X"
    assert assignment["B"] == "Y"
    a_trace = next(t for t in trace if t["role_id"] == "A")
    b_trace = next(t for t in trace if t["role_id"] == "B")
    assert a_trace["preference_rank"] == 1
    assert b_trace["preference_rank"] == 1
    # 無超額 → tie_break_random_index 為 None
    assert a_trace["tie_break_random_index"] is None
    assert b_trace["tie_break_random_index"] is None


def test_m2_oversubscription_first_level():
    """同 target 第 1 志願超額：Fisher-Yates 取前 N，落選下層。"""
    qs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    # 3 人同搶 X（cap 1）；落選 2 人退第 2 志願 Y（cap 2 → 全進）
    prefs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    caps = {"X": 1, "Y": 2}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(42), role_order=["A", "B", "C"],
    )
    # 一人到 X、兩人到 Y
    x_winners = [r for r, t in assignment.items() if t == "X"]
    y_winners = [r for r, t in assignment.items() if t == "Y"]
    assert len(x_winners) == 1
    assert len(y_winners) == 2

    # X 的勝者 preference_rank 為 1；Y 的勝者 preference_rank 為 2
    for entry in trace:
        if entry["chosen"] == "X":
            assert entry["preference_rank"] == 1
        elif entry["chosen"] == "Y":
            assert entry["preference_rank"] == 2


def test_m2_tie_break_random_index_for_competitors():
    """超額情境：所有競爭者的 tie_break_random_index 為非 null。"""
    qs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    prefs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    caps = {"X": 2}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(7), role_order=["A", "B", "C"],
    )
    # 兩人到 X，一人未分配（無 fallback 目標）
    x_winners = [r for r, t in assignment.items() if t == "X"]
    assert len(x_winners) == 2

    # 兩位 X 勝者的 trace 條目應該有 tie_break_random_index
    for entry in trace:
        if entry["chosen"] == "X":
            assert entry["tie_break_random_index"] is not None
            assert isinstance(entry["tie_break_random_index"], int)


def test_m2_fallback_when_all_preferences_exhausted():
    """所有志願都被擠掉但有非志願 target 仍有名額 → fallback 抽籤。"""
    # qs 讓所有人都合格 Y，這樣志願落選後可走 fallback 到 Y
    qs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    prefs = {"A": ["X", "Y"], "B": ["X"], "C": []}
    caps = {"X": 1, "Y": 2}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(99), role_order=["A", "B", "C"],
    )
    # 應有至少一位透過 fallback 抽中
    fallback_entries = [t for t in trace if t.get("fallback_random_index") is not None]
    assert len(fallback_entries) >= 1
    # fallback 抽中者 preference_rank 為 None
    for entry in fallback_entries:
        assert entry["preference_rank"] is None


def test_m2_unassigned_role_has_trace_entry():
    """完全沒對象的參與者也有 trace 條目（chosen=null）。"""
    qs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    prefs = {"A": ["X"], "B": ["X"], "C": ["X"]}
    caps = {"X": 2}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(7), role_order=["A", "B", "C"],
    )
    # 應有 3 筆 trace 條目（含未分配者）
    assert len(trace) == 3
    unassigned_entries = [t for t in trace if t["chosen"] is None]
    assert len(unassigned_entries) == 1


def test_m2_deterministic_same_seed():
    qs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    prefs = {"A": ["X", "Y"], "B": ["X", "Y"], "C": ["X", "Y"]}
    caps = {"X": 1, "Y": 2}
    o1, a1, t1 = allocate_m2(qs, prefs, caps, SeededRandom(123), role_order=["A", "B", "C"])
    o2, a2, t2 = allocate_m2(qs, prefs, caps, SeededRandom(123), role_order=["A", "B", "C"])
    assert o1 == o2
    assert a1 == a2
    assert t1 == t2


def test_m2_empty_preferences_falls_back():
    """preferences 空但有資格 target → fallback 抽籤。"""
    qs = {"A": ["X"]}
    prefs = {"A": []}
    caps = {"X": 1}
    _, assignment, trace = allocate_m2(
        qs, prefs, caps, SeededRandom(1), role_order=["A"],
    )
    assert assignment["A"] == "X"
    a_trace = trace[0]
    assert a_trace["fallback_random_index"] is not None
    assert a_trace["preference_rank"] is None
