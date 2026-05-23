"""分配機制：M0 純抽籤、M1 RSD、M2 Boston。

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
            # 階段 4b 新增（M0 路徑為 null）
            "tie_break_random_index": None,
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
    """M1 RSD：先 Fisher-Yates 洗牌處理順序、再逐位選最高未滿志願。"""
    processing_order, _shuffle_indices = fisher_yates_shuffle(list(role_order), rng)

    remaining = dict(capacities)
    assignment: dict[str, str | None] = {}
    trace: list[dict] = []
    step = 0

    for role_id in processing_order:
        step += 1
        qualified_for_role = sorted(qualified_set.get(role_id, []))
        candidates = [t for t in qualified_for_role if remaining.get(t, 0) > 0]

        raw_prefs = preferences_map.get(role_id, [])
        preferred_order = _normalize_preferences(list(raw_prefs), qualified_for_role)

        chosen = None
        preference_rank = None
        fallback_random_index = None

        for rank, tid in enumerate(preferred_order, start=1):
            if remaining.get(tid, 0) > 0:
                chosen = tid
                preference_rank = rank
                break

        if chosen is None and candidates:
            fallback_random_index = rng.randrange(len(candidates))
            chosen = candidates[fallback_random_index]

        if chosen is not None:
            remaining[chosen] -= 1
        assignment[role_id] = chosen

        trace.append({
            "step": step,
            "role_id": role_id,
            "candidates": candidates,
            "random_index": step - 1,
            "chosen": chosen,
            "remaining_capacity_after": {t: remaining[t] for t in sorted(remaining)},
            "preferred_order": preferred_order,
            "preference_rank": preference_rank,
            "fallback_random_index": fallback_random_index,
            # 階段 4b 新增（M1 路徑為 null）
            "tie_break_random_index": None,
        })

    return processing_order, assignment, trace


def allocate_m2(
    qualified_set: dict,
    preferences_map: dict,
    capacities: dict,
    rng: SeededRandom,
    role_order: list,
) -> tuple[list, dict, list[dict]]:
    """M2 Boston：先全塞第 1 志願（超額抽籤），剩餘退到第 2 志願。"""
    remaining = dict(capacities)
    assigned: dict[str, str | None] = {}
    trace: list[dict] = []
    step = 0

    # 規範化每位 role 的 preferences
    role_prefs: dict[str, list] = {}
    for role_id in role_order:
        qualified_for_role = sorted(qualified_set.get(role_id, []))
        role_prefs[role_id] = _normalize_preferences(
            list(preferences_map.get(role_id, [])),
            qualified_for_role,
        )

    # 依層級逐次處理
    max_level = max((len(p) for p in role_prefs.values()), default=0)
    unassigned = sorted(role_order)  # 依 role_id 字母序

    for level in range(1, max_level + 1):
        # 收集本層各 target 的競爭者（role_id 依字母序）
        groups: dict[str, list[str]] = {}
        for role_id in unassigned:
            prefs = role_prefs[role_id]
            if level <= len(prefs):
                target = prefs[level - 1]
                if remaining.get(target, 0) > 0:
                    groups.setdefault(target, []).append(role_id)

        # 依 target_id 字母序處理同層各 target
        winners_this_level: list = []
        for target_id in sorted(groups.keys()):
            competitors = groups[target_id]
            cap = remaining.get(target_id, 0)
            if len(competitors) <= cap:
                winners = competitors
                tie_break_indices = {r: None for r in competitors}
            else:
                # 超額：Fisher-Yates 洗牌取前 N
                shuffled, _ = fisher_yates_shuffle(competitors, rng)
                winners = shuffled[:cap]
                tie_break_indices = {r: shuffled.index(r) for r in competitors}

            for role_id in winners:
                step += 1
                remaining[target_id] -= 1
                assigned[role_id] = target_id
                qualified_for_role = sorted(qualified_set.get(role_id, []))
                candidates = [t for t in qualified_for_role if remaining.get(t, 0) >= 0]
                trace.append({
                    "step": step,
                    "role_id": role_id,
                    "candidates": candidates,
                    "random_index": step - 1,
                    "chosen": target_id,
                    "remaining_capacity_after": {t: remaining[t] for t in sorted(remaining)},
                    "preferred_order": role_prefs[role_id],
                    "preference_rank": level,
                    "fallback_random_index": None,
                    "tie_break_random_index": tie_break_indices[role_id],
                })
                winners_this_level.append(role_id)

        unassigned = [r for r in unassigned if r not in winners_this_level]

    # Fallback：所有層級處理完仍未分配
    for role_id in unassigned:
        step += 1
        qualified_for_role = sorted(qualified_set.get(role_id, []))
        candidates = [t for t in qualified_for_role if remaining.get(t, 0) > 0]

        chosen = None
        fallback_random_index = None
        if candidates:
            fallback_random_index = rng.randrange(len(candidates))
            chosen = candidates[fallback_random_index]
            remaining[chosen] -= 1

        assigned[role_id] = chosen
        trace.append({
            "step": step,
            "role_id": role_id,
            "candidates": candidates,
            "random_index": step - 1,
            "chosen": chosen,
            "remaining_capacity_after": {t: remaining[t] for t in sorted(remaining)},
            "preferred_order": role_prefs[role_id],
            "preference_rank": None,
            "fallback_random_index": fallback_random_index,
            "tie_break_random_index": None,
        })

    processing_order = [entry["role_id"] for entry in trace]
    return processing_order, assigned, trace
