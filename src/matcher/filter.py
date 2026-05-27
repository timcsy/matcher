"""過濾階段：規則 + 名單 → 資格集合 + filter_trace。"""

from __future__ import annotations

from matcher.errors import QualifiedSetEmpty
from matcher.roster import Roster
from matcher.rules import Ruleset, evaluate, first_failed_rule, matched_rules


def filter_qualified(ruleset: Ruleset, roster: Roster) -> tuple[dict, list[dict]]:
    """對每個 (participant, target) 求值，產生資格集合與 filter_trace。

    若無任何參與者擁有資格 → QualifiedSetEmpty。
    """
    qualified_set: dict[str, list[str]] = {r.id: [] for r in roster.participants}
    trace: list[dict] = []

    for participant in roster.participants:
        for target in roster.targets:
            ms = matched_rules(ruleset, participant.attributes, target.attributes)
            ok = len(ms) == len(ruleset.rules)
            entry: dict = {
                "participant_id": participant.id,
                "target_id": target.id,
                "qualified": ok,
                "matched_rules": [m.id for m in ms],
            }
            if not ok:
                failed = first_failed_rule(ruleset, participant.attributes, target.attributes)
                entry["failed_rule"] = failed.id if failed else None
            trace.append(entry)
            if ok:
                qualified_set[participant.id].append(target.id)

    if not any(qualified_set.values()):
        summary = rejection_summary(trace, ruleset)
        raise QualifiedSetEmpty(
            "資格集合為空：依目前規則，所有 (參與者, 對象) 組合皆未通過。",
            trace=trace,
            rule_stats=summary["rule_stats"],
            culprit=summary["culprit"],
            total_pairs=summary["total_pairs"],
            rule_descriptions={r.id: r.description for r in ruleset.rules},
        )

    return qualified_set, trace


def rejection_summary(trace: list[dict], ruleset: Ruleset) -> dict:
    """從 filter_trace 算出「每條規則刷掉幾組」與元兇規則（純函式，無副作用）。

    某組「沒過的規則」= 全部規則 − matched_rules（比只看首敗更完整）。
    culprit = 失敗組數最大的規則；並列時取規則順序第一；全過 → None。
    """
    rule_stats: dict[str, int] = {r.id: 0 for r in ruleset.rules}
    for entry in trace:
        matched = set(entry.get("matched_rules", []))
        for r in ruleset.rules:
            if r.id not in matched:
                rule_stats[r.id] += 1
    culprit = None
    best = 0
    for r in ruleset.rules:  # 依規則順序 → 並列取第一
        if rule_stats[r.id] > best:
            best = rule_stats[r.id]
            culprit = r.id
    return {"total_pairs": len(trace), "rule_stats": rule_stats, "culprit": culprit}
