"""過濾階段：規則 + 名單 → 資格集合 + filter_trace。"""

from __future__ import annotations

from matcher.errors import QualifiedSetEmpty
from matcher.roster import Roster
from matcher.rules import Ruleset, evaluate, first_failed_rule, matched_rules


def filter_qualified(ruleset: Ruleset, roster: Roster) -> tuple[dict, list[dict]]:
    """對每個 (role, target) 求值，產生資格集合與 filter_trace。

    若無任何角色擁有資格 → QualifiedSetEmpty。
    """
    qualified_set: dict[str, list[str]] = {r.id: [] for r in roster.roles}
    trace: list[dict] = []

    for role in roster.roles:
        for target in roster.targets:
            ms = matched_rules(ruleset, role.attributes, target.attributes)
            ok = len(ms) == len(ruleset.rules)
            entry: dict = {
                "role_id": role.id,
                "target_id": target.id,
                "qualified": ok,
                "matched_rules": [m.id for m in ms],
            }
            if not ok:
                failed = first_failed_rule(ruleset, role.attributes, target.attributes)
                entry["failed_rule"] = failed.id if failed else None
            trace.append(entry)
            if ok:
                qualified_set[role.id].append(target.id)

    if not any(qualified_set.values()):
        raise QualifiedSetEmpty(
            "資格集合為空：依目前規則，所有 (角色, 對象) 組合皆未通過。"
        )

    return qualified_set, trace
