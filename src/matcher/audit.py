"""稽核紀錄組裝與 JSON 序列化。

序列化參數：ensure_ascii=False, sort_keys=True, indent=2
→ 跨平台逐位元組相同（SC-001）、保留繁中。
"""

from __future__ import annotations

import json
from pathlib import Path

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
    Rule,
    Ruleset,
)


def _expr_to_dict(expr) -> dict:
    if isinstance(expr, Eq):
        return {"eq": {"field": expr.field, "value": expr.value}}
    if isinstance(expr, In):
        return {"in": {"field": expr.field, "set": list(expr.set)}}
    if isinstance(expr, Ge):
        return {"ge": {"field": expr.field, "value": expr.value}}
    if isinstance(expr, Le):
        return {"le": {"field": expr.field, "value": expr.value}}
    if isinstance(expr, RoleInTargetField):
        return {"role_in_target_field": {
            "role_field": expr.role_field,
            "target_field": expr.target_field,
        }}
    if isinstance(expr, And):
        return {"and": [_expr_to_dict(c) for c in expr.children]}
    if isinstance(expr, Or):
        return {"or": [_expr_to_dict(c) for c in expr.children]}
    if isinstance(expr, Not):
        return {"not": _expr_to_dict(expr.child)}
    raise TypeError(f"未知表達式：{type(expr)!r}")


def _ruleset_to_dict(rs: Ruleset) -> dict:
    return {
        "version": rs.version,
        "rules": [
            {"id": r.id, "description": r.description, "expr": _expr_to_dict(r.expr)}
            for r in rs.rules
        ],
    }


def _roster_to_dict(roster: Roster) -> dict:
    return {
        "roles": [{"id": r.id, "attributes": r.attributes} for r in roster.roles],
        "targets": [
            {"id": t.id, "capacity": t.capacity, "attributes": t.attributes}
            for t in roster.targets
        ],
    }


def build_audit_record(
    *,
    seed: int,
    ruleset: Ruleset,
    roster: Roster,
    qualified_set: dict,
    filter_trace: list[dict],
    allocation_trace: list[dict],
    assignment: dict,
    mechanism: str = "M0",
) -> dict:
    return {
        "schema_version": "1.0",
        "mechanism": mechanism,
        "seed": seed,
        "rules_snapshot": _ruleset_to_dict(ruleset),
        "roster_snapshot": _roster_to_dict(roster),
        "qualified_set": qualified_set,
        "filter_trace": filter_trace,
        "allocation_trace": allocation_trace,
        "assignment": assignment,
        "generated_at": None,
    }


def dump_audit_json(record: dict, path: str | Path) -> None:
    s = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
    Path(path).write_text(s + "\n", encoding="utf-8")
