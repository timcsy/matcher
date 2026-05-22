"""M0 純抽籤分配。

演算法：以資格集合的 role.id 字母順序逐位處理；每位角色在其資格 target 清單中
（同樣以字母順序固定起始順序），用 SeededRandom.randrange 抽出一位，扣減該對象容量。
此寫法符合 research.md R-002 的「僅用 randrange + 顯式選擇」原則。
"""

from __future__ import annotations

from matcher.rng import SeededRandom


def allocate_m0(
    qualified_set: dict,
    capacities: dict,
    rng: SeededRandom,
) -> tuple[dict, list[dict]]:
    """純抽籤分配。

    回傳：(assignment, allocation_trace)
    - assignment: role_id → target_id（無可分配時為 None）
    - allocation_trace: 每步隨機決策的完整紀錄
    """
    # 為決定性，按 role_id 排序處理
    remaining = dict(capacities)
    assignment: dict[str, str | None] = {}
    trace: list[dict] = []
    step = 0

    for role_id in sorted(qualified_set.keys()):
        candidates = [t for t in sorted(qualified_set[role_id]) if remaining.get(t, 0) > 0]
        if not candidates:
            assignment[role_id] = None
            continue

        step += 1
        idx = rng.randrange(len(candidates))
        chosen = candidates[idx]
        remaining[chosen] -= 1
        assignment[role_id] = chosen

        trace.append({
            "step": step,
            "role_id": role_id,
            "candidates": candidates,
            "random_index": idx,
            "chosen": chosen,
            "remaining_capacity_after": {t: remaining[t] for t in sorted(remaining)},
        })

    return assignment, trace
