"""主管線：validate → filter → capacity check → allocate → audit。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from matcher.allocator import allocate_m0, allocate_m1, allocate_m2
from matcher.audit import build_audit_record
from matcher.errors import (
    CapacityShortage,
    MechanismRequiresPreferences,
    PreferencesNotSupported,
    SeedMissing,
    UnknownAttribute,
)
from matcher.filter import filter_qualified
from matcher.rng import SeededRandom
from matcher.roster import Roster
from matcher.rules import (
    And,
    Eq,
    Ge,
    In,
    Le,
    Not,
    Or,
    RoleInTargetField,
    Ruleset,
    detect_contradictions,
)


@dataclass
class MatcherInput:
    ruleset: Ruleset
    roster: Roster
    seed: Optional[int]
    preferences: Optional[dict] = None
    mechanism: str = "M0"
    template: object = None  # Template | None；不引入 import 循環
    import_metadata: Optional[dict] = None


@dataclass
class MatcherResult:
    qualified_set: dict
    assignment: dict
    audit: dict


# ── 屬性靜態檢查 ─────────────────────────────────────────────────────


def _collect_referenced_fields(expr) -> list[tuple[str, str]]:
    """收集表達式引用的 (side, name)。side ∈ {role, target}。"""
    refs: list[tuple[str, str]] = []
    if isinstance(expr, (Eq, In, Ge, Le)):
        side, _, name = expr.field.partition(".")
        refs.append((side, name))
    elif isinstance(expr, RoleInTargetField):
        refs.append(("role", expr.role_field))
        refs.append(("target", expr.target_field))
    elif isinstance(expr, (And, Or)):
        for c in expr.children:
            refs.extend(_collect_referenced_fields(c))
    elif isinstance(expr, Not):
        refs.extend(_collect_referenced_fields(expr.child))
    return refs


def _validate_attribute_references(ruleset: Ruleset, roster: Roster) -> None:
    role_attrs = set()
    for r in roster.roles:
        role_attrs.update(r.attributes.keys())
    target_attrs = set()
    for t in roster.targets:
        target_attrs.update(t.attributes.keys())

    for rule in ruleset.rules:
        for side, name in _collect_referenced_fields(rule.expr):
            if side == "role" and name not in role_attrs:
                raise UnknownAttribute(
                    f"規則 `{rule.id}` 引用未定義的參與者屬性 `role.{name}`；"
                    f"目前名單中所有參與者屬性：{sorted(role_attrs)}"
                )
            if side == "target" and name not in target_attrs:
                raise UnknownAttribute(
                    f"規則 `{rule.id}` 引用未定義的對象屬性 `target.{name}`；"
                    f"目前名單中所有對象屬性：{sorted(target_attrs)}"
                )
            if side not in ("role", "target"):
                raise UnknownAttribute(
                    f"規則 `{rule.id}` 的欄位引用 `{side}.{name}` 缺少 role./target. 前綴"
                )


# ── 主流程 ─────────────────────────────────────────────────────────────


def run_match(inp: MatcherInput) -> MatcherResult:
    # 1. seed 必填
    if inp.seed is None:
        raise SeedMissing(
            "seed 未提供。\n建議：以 --seed <整數> 提供隨機種子。"
        )

    _FRIENDLY = {"M0": "純抽籤", "M1": "輪流挑", "M2": "依志願先後填滿"}

    # 2. preferences 在純抽籤模式下不接受
    if inp.mechanism == "M0" and inp.preferences:
        raise PreferencesNotSupported(
            "「純抽籤」不接受志願輸入。\n"
            "建議：若需要使用志願，請改用「輪流挑」或「依志願先後填滿」。"
        )

    # 2b. 名單中內嵌的 preferences 在純抽籤模式下也不接受
    if inp.mechanism == "M0" and any(role.preferences for role in inp.roster.roles):
        raise PreferencesNotSupported(
            "「純抽籤」不接受志願輸入。\n"
            "原因：名單中有人填了志願。\n"
            "建議：清空名單中的志願欄，或改用「輪流挑」或「依志願先後填滿」。"
        )

    # 2c. 輪流挑 / 依志願先後填滿 需要至少一位參與者提供志願
    if inp.mechanism in ("M1", "M2") and not any(role.preferences for role in inp.roster.roles):
        friendly = _FRIENDLY.get(inp.mechanism, inp.mechanism)
        raise MechanismRequiresPreferences(
            f"「{friendly}」需要至少一位填了志願；若所有人都沒志願，請改用「純抽籤」。\n"
            f"建議：CSV「志願組別」欄填分號分隔的對象代號（如 G1;G2;G3），或改用「純抽籤」。"
        )

    # 3. 規則層靜態檢查
    detect_contradictions(inp.ruleset)
    _validate_attribute_references(inp.ruleset, inp.roster)

    # 4. 過濾
    qualified_set, filter_trace = filter_qualified(inp.ruleset, inp.roster)

    # 5. 容量預檢：每位參與者的資格 target 都因容量耗盡而無分配 → 容量不足
    total_capacity = sum(t.capacity for t in inp.roster.targets)
    n_roles = len(inp.roster.roles)
    if n_roles > total_capacity:
        raise CapacityShortage(
            f"容量不足以容納所有參與者。\n"
            f"細節：參與者 {n_roles} 人，所有對象總容量 {total_capacity}；超額 {n_roles - total_capacity} 人。\n"
            f"建議：增加對象容量、減少參與者，或調整資格條件以排除部分參與者。"
        )

    # 6. 分配
    capacities = {t.id: t.capacity for t in inp.roster.targets}
    rng = SeededRandom(inp.seed)
    processing_order: list | None = None

    if inp.mechanism == "M0":
        assignment, allocation_trace = allocate_m0(qualified_set, capacities, rng)
    elif inp.mechanism == "M1":
        preferences_map = {role.id: list(role.preferences) for role in inp.roster.roles}
        processing_order, assignment, allocation_trace = allocate_m1(
            qualified_set, preferences_map, capacities, rng,
            role_order=[role.id for role in inp.roster.roles],
        )
    elif inp.mechanism == "M2":
        preferences_map = {role.id: list(role.preferences) for role in inp.roster.roles}
        processing_order, assignment, allocation_trace = allocate_m2(
            qualified_set, preferences_map, capacities, rng,
            role_order=[role.id for role in inp.roster.roles],
        )
    else:
        raise ValueError(f"不支援的機制 `{inp.mechanism}`；支援：M0、M1、M2")

    # 7. 稽核紀錄
    audit = build_audit_record(
        seed=inp.seed,
        ruleset=inp.ruleset,
        roster=inp.roster,
        qualified_set=qualified_set,
        filter_trace=filter_trace,
        allocation_trace=allocation_trace,
        assignment=assignment,
        mechanism=inp.mechanism,
        template=inp.template,
        import_metadata=inp.import_metadata,
        processing_order=processing_order,
    )

    return MatcherResult(
        qualified_set=qualified_set,
        assignment=assignment,
        audit=audit,
    )


def run_filter_only(ruleset: Ruleset, roster: Roster) -> tuple[dict, list[dict]]:
    """只執行過濾階段（FR-005）。"""
    detect_contradictions(ruleset)
    _validate_attribute_references(ruleset, roster)
    return filter_qualified(ruleset, roster)
