"""規則模型、AST 與求值器。

AST 節點為 frozen dataclass；求值器在過濾期將 participant.X / target.X 欄位取出比對。
表達能力對齊 FR-013：等值、邏輯（AND/OR/NOT）、範圍/集合（≥/≤/IN）、跨側包含。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from matcher.errors import RuleContradiction, RuleTypeError, UnknownAttribute

AttrValue = Union[str, int, bool, list]  # bool 不在 spec 中支援，保留以利錯誤偵測

# participant_in_target_field 的包含模式
_PIT_MODES = {"auto", "equal", "participant_in_target", "target_in_participant", "intersect"}


# ── AST 節點 ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Eq:
    field: str
    value: object


@dataclass(frozen=True)
class In:
    field: str
    set: list


@dataclass(frozen=True)
class Ge:
    field: str
    value: int


@dataclass(frozen=True)
class Le:
    field: str
    value: int


@dataclass(frozen=True)
class ParticipantInTargetField:
    participant_field: str
    target_field: str
    # 包含模式（feature 019）：auto = 依型別自動判斷；其餘為明確覆寫。
    #   equal=兩集合相等、participant_in_target=參與者⊆對象、
    #   target_in_participant=對象⊆參與者、intersect=有交集
    mode: str = "auto"


@dataclass(frozen=True)
class And:
    children: tuple


@dataclass(frozen=True)
class Or:
    children: tuple


@dataclass(frozen=True)
class Not:
    child: object


RuleExpr = Union[Eq, In, Ge, Le, ParticipantInTargetField, And, Or, Not]


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    expr: RuleExpr


@dataclass(frozen=True)
class Ruleset:
    rules: tuple
    version: str = "1.0"


# ── 解析（從 YAML 載入的 dict 轉為 AST）─────────────────────────────────


def parse_expr(node: object) -> RuleExpr:
    """將 YAML 載入的 dict 轉為 AST。"""
    if not isinstance(node, dict) or len(node) != 1:
        raise ValueError(f"規則表達式格式錯誤：每節點必須為單一鍵的 dict，得到 {node!r}")
    (op, body), = node.items()

    if op == "eq":
        return Eq(field=body["field"], value=body["value"])
    if op == "in":
        return In(field=body["field"], set=list(body["set"]))
    if op == "ge":
        return Ge(field=body["field"], value=int(body["value"]))
    if op == "le":
        return Le(field=body["field"], value=int(body["value"]))
    if op == "participant_in_target_field":
        mode = body.get("mode", "auto")
        if mode not in _PIT_MODES:
            raise UnknownAttribute(
                f"participant_in_target_field 的 mode `{mode}` 不支援；"
                f"可用：{', '.join(sorted(_PIT_MODES))}"
            )
        return ParticipantInTargetField(
            participant_field=body["participant_field"],
            target_field=body["target_field"],
            mode=mode,
        )
    if op == "and":
        return And(children=tuple(parse_expr(c) for c in body))
    if op == "or":
        return Or(children=tuple(parse_expr(c) for c in body))
    if op == "not":
        return Not(child=parse_expr(body))
    raise ValueError(f"未知的規則表達式：{op!r}")


def parse_ruleset(data: dict) -> Ruleset:
    rules = []
    for r in data.get("rules", []):
        if "id" not in r or "description" not in r or "expr" not in r:
            raise ValueError(f"規則檔欄位缺失（需 id、description、expr）：{r!r}")
        rules.append(Rule(id=r["id"], description=r["description"], expr=parse_expr(r["expr"])))
    return Ruleset(rules=tuple(rules), version=str(data.get("version", "1.0")))


# ── 求值 ─────────────────────────────────────────────────────────────────


def _resolve(field_ref: str, participant_attrs: dict, target_attrs: dict) -> object:
    """解析 'participant.X' / 'target.X' 形式的欄位引用。"""
    side, _, name = field_ref.partition(".")
    if not name:
        raise UnknownAttribute(f"規則引用了無效欄位 `{field_ref}`：缺少 participant./target. 前綴")
    if side == "participant":
        if name not in participant_attrs:
            raise UnknownAttribute(f"規則引用未定義的參與者屬性：`{field_ref}`")
        return participant_attrs[name]
    if side == "target":
        if name not in target_attrs:
            raise UnknownAttribute(f"規則引用未定義的對象屬性：`{field_ref}`")
        return target_attrs[name]
    raise UnknownAttribute(f"規則引用無效欄位前綴：`{field_ref}`（必須為 participant. 或 target.）")


def _compare_numeric(field_ref: str, actual, op: str, expected) -> bool:
    """ge/le 比較：兩邊都必須是數值（非 bool）。型別不符 → 友善 RuleTypeError，
    而非讓 Python 拋裸 TypeError（後者逃出退出碼表、無法解釋）。"""
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        raise RuleTypeError(
            f"規則對欄位 `{field_ref}` 用了大小比較（{op} {expected!r}），"
            f"但該欄位的值是 {actual!r}（非數字），無法比大小。\n"
            f"建議：把該屬性宣告為數字（int）型別，或改用等值 / 集合（eq / in）規則。"
        )
    return actual >= expected if op == ">=" else actual <= expected


def evaluate(expr: RuleExpr, participant_attrs: dict, target_attrs: dict) -> bool:
    """對單一 (participant, target) 求值單一表達式。"""
    if isinstance(expr, Eq):
        return _resolve(expr.field, participant_attrs, target_attrs) == expr.value
    if isinstance(expr, In):
        return _resolve(expr.field, participant_attrs, target_attrs) in expr.set
    if isinstance(expr, Ge):
        return _compare_numeric(expr.field, _resolve(expr.field, participant_attrs, target_attrs), ">=", expr.value)
    if isinstance(expr, Le):
        return _compare_numeric(expr.field, _resolve(expr.field, participant_attrs, target_attrs), "<=", expr.value)
    if isinstance(expr, ParticipantInTargetField):
        rv = participant_attrs.get(expr.participant_field)
        if expr.participant_field not in participant_attrs:
            raise UnknownAttribute(f"規則引用未定義的參與者屬性：`participant.{expr.participant_field}`")
        if expr.target_field not in target_attrs:
            raise UnknownAttribute(f"規則引用未定義的對象屬性：`target.{expr.target_field}`")
        tv = target_attrs[expr.target_field]
        if expr.mode == "auto":
            # 對稱化（feature 019）：不論哪邊是清單都做合理的包含判斷。
            #   兩邊單值 → 相等；參與者單值＋對象清單 → 參與者值 ∈ 對象清單；
            #   參與者清單＋對象單值 → 對象值 ∈ 參與者清單；兩邊清單 → 交集非空。
            p_list, t_list = isinstance(rv, list), isinstance(tv, list)
            if p_list and t_list:
                return any(x in tv for x in rv)
            if p_list:
                return tv in rv
            if t_list:
                return rv in tv
            return rv == tv
        # 明確模式覆寫：把兩邊都當集合比較
        p_set = set(rv) if isinstance(rv, list) else {rv}
        t_set = set(tv) if isinstance(tv, list) else {tv}
        if expr.mode == "equal":
            return p_set == t_set
        if expr.mode == "participant_in_target":
            return p_set <= t_set
        if expr.mode == "target_in_participant":
            return t_set <= p_set
        if expr.mode == "intersect":
            return bool(p_set & t_set)
        raise UnknownAttribute(f"未知的包含模式：{expr.mode}")
    if isinstance(expr, And):
        return all(evaluate(c, participant_attrs, target_attrs) for c in expr.children)
    if isinstance(expr, Or):
        return any(evaluate(c, participant_attrs, target_attrs) for c in expr.children)
    if isinstance(expr, Not):
        return not evaluate(expr.child, participant_attrs, target_attrs)
    raise TypeError(f"未知表達式型別：{type(expr)!r}")


def matched_rules(ruleset: Ruleset, participant_attrs: dict, target_attrs: dict) -> list[Rule]:
    """回傳所有通過的規則（依出現順序）。"""
    return [r for r in ruleset.rules if evaluate(r.expr, participant_attrs, target_attrs)]


def first_failed_rule(ruleset: Ruleset, participant_attrs: dict, target_attrs: dict) -> Rule | None:
    for r in ruleset.rules:
        if not evaluate(r.expr, participant_attrs, target_attrs):
            return r
    return None


# ── 規則互斥偵測（局部不可滿足）──────────────────────────────────────


def _eq_constraints(expr: RuleExpr) -> list[tuple[str, object, bool]]:
    """收集 expr 中的 Eq 約束。回傳 [(field, value, expected)]，expected=True 為要求等於。

    僅展開 And 與 Not(Eq)，其他結構不處理（避免假陽性）。
    """
    out: list[tuple[str, object, bool]] = []
    if isinstance(expr, Eq):
        out.append((expr.field, expr.value, True))
    elif isinstance(expr, Not) and isinstance(expr.child, Eq):
        out.append((expr.child.field, expr.child.value, False))
    elif isinstance(expr, And):
        for c in expr.children:
            out.extend(_eq_constraints(c))
    return out


def detect_contradictions(ruleset: Ruleset) -> None:
    """偵測規則內部不可滿足。發現即拋 RuleContradiction。

    本階段僅偵測「同一 And 中同時要求 Eq(f,v) 與 Not(Eq(f,v))」。
    """
    for r in ruleset.rules:
        cs = _eq_constraints(r.expr)
        positives = {(f, v) for f, v, exp in cs if exp}
        negatives = {(f, v) for f, v, exp in cs if not exp}
        clash = positives & negatives
        if clash:
            f, v = next(iter(clash))
            raise RuleContradiction(
                f"規則 `{r.id}` 內部矛盾：同時要求 `{f} == {v!r}` 與 `not ({f} == {v!r})`"
            )
