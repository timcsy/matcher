"""US1：M0 純抽籤分配。"""

from __future__ import annotations

from matcher.allocator import allocate_m0
from matcher.rng import SeededRandom


def test_allocation_within_qualified_set():
    qs = {"A": ["T1", "T2"], "B": ["T2"]}
    capacities = {"T1": 1, "T2": 1}
    assignment, trace = allocate_m0(qs, capacities, SeededRandom(1))
    for role, target in assignment.items():
        if target is not None:
            assert target in qs[role], f"{role}→{target} 不在資格集合內"


def test_allocation_respects_capacity():
    qs = {"A": ["T1"], "B": ["T1"], "C": ["T1"]}
    capacities = {"T1": 2}
    assignment, _ = allocate_m0(qs, capacities, SeededRandom(42))
    # 至少有一位未被分配（容量 2 < 參與者 3）
    assigned = [t for t in assignment.values() if t is not None]
    assert len(assigned) == 2
    assert assigned.count("T1") == 2


def test_allocation_is_deterministic():
    qs = {"A": ["T1", "T2"], "B": ["T1", "T2"]}
    capacities = {"T1": 1, "T2": 1}
    a1, t1 = allocate_m0(qs, capacities, SeededRandom(99))
    a2, t2 = allocate_m0(qs, capacities, SeededRandom(99))
    assert a1 == a2
    assert t1 == t2


def test_allocation_trace_structure():
    qs = {"A": ["T1", "T2"]}
    capacities = {"T1": 1, "T2": 1}
    _, trace = allocate_m0(qs, capacities, SeededRandom(7))
    assert len(trace) == 1
    step = trace[0]
    assert step["step"] == 1
    assert step["role_id"] == "A"
    assert set(step["candidates"]) == {"T1", "T2"}
    assert step["chosen"] in {"T1", "T2"}
    assert "random_index" in step
    assert step["remaining_capacity_after"][step["chosen"]] == 0
