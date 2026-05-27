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
    ParticipantInTargetField,
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
    if isinstance(expr, ParticipantInTargetField):
        return {"participant_in_target_field": {
            "participant_field": expr.participant_field,
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
        "participants": [
            {"id": r.id, "attributes": r.attributes, "preferences": list(r.preferences)}
            for r in roster.participants
        ],
        "targets": [
            {"id": t.id, "capacity": t.capacity, "attributes": t.attributes}
            for t in roster.targets
        ],
    }


def _template_to_dict(tpl) -> dict:
    """將 Template 序列化為可寫入稽核紀錄的 dict。"""
    out = {
        "id": tpl.id,
        "schema_version": tpl.schema_version,
        "name": tpl.name,
        "description": tpl.description,
        "attributes": {
            "participants": [
                {"key": a.key, "type": a.type, "required": a.required, "description": a.description}
                for a in tpl.attributes.participants
            ],
            "targets": [
                {"key": a.key, "type": a.type, "required": a.required, "description": a.description}
                for a in tpl.attributes.targets
            ],
        },
        "rules": [
            {"id": r.id, "description": r.description, "expr": _expr_to_dict(r.expr)}
            for r in tpl.ruleset.rules
        ],
        "ui_fields": [
            {
                "key": u.key, "label": u.label, "type": u.type, "required": u.required,
                "options": list(u.options) if u.options is not None else None,
                "placeholder": u.placeholder, "help": u.help,
            }
            for u in tpl.ui_fields
        ],
        "report_fields": [
            {"key": r.key, "label": r.label, "source": r.source}
            for r in tpl.report_fields
        ],
        "preferences_schema": None if tpl.preferences_schema is None else {
            "max_choices": tpl.preferences_schema.max_choices,
            "required": tpl.preferences_schema.required,
            "description": tpl.preferences_schema.description,
        },
    }
    return out


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
    template=None,
    import_metadata: dict | None = None,
    processing_order: list | None = None,
) -> dict:
    return {
        "schema_version": "1.5",
        "mechanism": mechanism,
        "seed": seed,
        "rules_snapshot": _ruleset_to_dict(ruleset),
        "roster_snapshot": _roster_to_dict(roster),
        "qualified_set": qualified_set,
        "filter_trace": filter_trace,
        "allocation_trace": allocation_trace,
        "assignment": assignment,
        "template_snapshot": None if template is None else _template_to_dict(template),
        "import_metadata": import_metadata,
        "processing_order": processing_order,
        "generated_at": None,
    }


def dump_audit_json(record: dict, path: str | Path) -> None:
    s = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
    Path(path).write_text(s + "\n", encoding="utf-8")
