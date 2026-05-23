"""分配機制：M0 純抽籤、M1 RSD（隨機輪流挑）。

演算法皆僅用 SeededRandom.randrange + 顯式 Fisher-Yates，
不使用 random.shuffle/sample/choices（符合 research.md R-002）。
"""

from __future__ import annotations

from matcher.rng import SeededRandom, fisher_yates_shuffle


def allocate_m0(
    qualified_set: dict,
    capacities: dict,
    rng: SeededRandom,
) -> tuple[dict, list[dict]]:
    """純抽籤分配。"""
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
            # v1.3 新增欄位（M0 路徑皆 null）
            "preferred_order": None,
            "preference_rank": None,
            "fallback_random_index": None,
        })

    return assignment, trace


def _normalize_preferences(role_prefs: list, qualified_for_role: list) -> list:
    """去重 + 忽略不在 qualified set 內的 target id。"""
    qualified_set_local = set(qualified_for_role)
    seen: set = set()
    out: list = []
    for tid in role_prefs:
        if tid in seen:
            continue
        seen.add(tid)
        if tid not in qualified_set_local:
            continue
        out.append(tid)
    return out


def allocate_m1(
    qualified_set: dict,
    preferences_map: dict,
    capacities: dict,
    rng: SeededRandom,
    role_order: list,
) -> tuple[list, dict, list[dict]]:
    """M1 RSD：先 Fisher-Yates 洗牌處理順序、再逐位選最高未滿志願。

    回傳：(processing_order, assignment, allocation_trace)
    - role_order：roster 中的原始角色順序（用於洗牌的輸入）
    """
    # 步驟 1：Fisher-Yates 洗牌得處理順序
    processing_order, _shuffle_indices = fisher_yates_shuffle(list(role_order), rng)

    remaining = dict(capacities)
    assignment: dict[str, str | None] = {}
    trace: list[dict] = []
    step = 0

    for role_id in processing_order:
        step += 1
        qualified_for_role = sorted(qualified_set.get(role_id, []))
        candidates = [t for t in qualified_for_role if remaining.get(t, 0) > 0]

        # 規範化 preferences
        raw_prefs = preferences_map.get(role_id, [])
        preferred_order = _normalize_preferences(list(raw_prefs), qualified_for_role)

        # 取第一個仍有名額的志願
        chosen = None
        preference_rank = None
        fallback_random_index = None

        for rank, tid in enumerate(preferred_order, start=1):
            if remaining.get(tid, 0) > 0:
                chosen = tid
                preference_rank = rank
                break

        if chosen is None and candidates:
            # Fallback：從合格 ∩ 仍有名額中抽一
            fallback_random_index = rng.randrange(len(candidates))
            chosen = candidates[fallback_random_index]

        if chosen is not None:
            remaining[chosen] -= 1
        assignment[role_id] = chosen

        trace.append({
            "step": step,
            "role_id": role_id,
            "candidates": candidates,
            "random_index": step - 1,  # 在 processing_order 中的位置
            "chosen": chosen,
            "remaining_capacity_after": {t: remaining[t] for t in sorted(remaining)},
            "preferred_order": preferred_order,
            "preference_rank": preference_rank,
            "fallback_random_index": fallback_random_index,
        })

    return processing_order, assignment, trace
