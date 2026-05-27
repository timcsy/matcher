"""簡單模式表單 → 模板 YAML dict 組裝；含 5 種規則類型自動 description 生成。

Feature 011 D4：純函式集中於此檔，方便單元測試與 jinja2 樣板共用。
"""

from __future__ import annotations

from typing import Any

# ── 規則類型常數 ──────────────────────────────────────────────

RULE_TYPES = (
    ("ge", "參與者屬性 ≥ 數值（int 比較）"),
    ("le", "參與者屬性 ≤ 數值（int 比較）"),
    ("eq", "參與者屬性等於某值"),
    ("in", "參與者屬性屬於集合"),
    ("participant_in_target_field", "參與者與對象欄位互相包含（任一邊可為多筆）"),
)


def _build_expr(rule_type: str, fields: dict) -> dict:
    """依規則類型 + 欄位組 expr dict。"""
    if rule_type == "ge":
        return {"ge": {"field": fields["field"], "value": int(fields["value"])}}
    if rule_type == "le":
        return {"le": {"field": fields["field"], "value": int(fields["value"])}}
    if rule_type == "eq":
        return {"eq": {"field": fields["field"], "value": fields["value"]}}
    if rule_type == "in":
        # set 字串以分號分隔
        items = [x.strip() for x in fields["set"].split(";") if x.strip()]
        return {"in": {"field": fields["field"], "set": items}}
    if rule_type == "participant_in_target_field":
        body = {
            "participant_field": fields["participant_field"],
            "target_field": fields["target_field"],
        }
        mode = (fields.get("mode") or "auto").strip() or "auto"
        if mode != "auto":
            body["mode"] = mode
        if fields.get("empty_ok") in ("true", "on", True, "1"):
            body["empty_ok"] = True
        return {"participant_in_target_field": body}
    raise ValueError(f"未知規則類型：{rule_type}")


def _attr_desc(attributes: dict, field_ref: str) -> str:
    """從 attributes lookup 取繁中 description。`participant.grade` → 「年級」；找不到回原 key。"""
    side, _, key = field_ref.partition(".")
    decls = (attributes.get("participants") or []) if side == "participant" else (attributes.get("targets") or [])
    for d in decls:
        if d.get("key") == key:
            return d.get("description") or key
    return key


def _auto_description(rule_type: str, fields: dict, attributes: dict) -> str:
    """依規則類型 + 欄位 + attributes 自動生成繁中 description（避免技術 token）。"""
    if rule_type == "ge":
        return f"{_attr_desc(attributes, fields['field'])} 必須 ≥ {fields['value']}"
    if rule_type == "le":
        return f"{_attr_desc(attributes, fields['field'])} 必須 ≤ {fields['value']}"
    if rule_type == "eq":
        return f"{_attr_desc(attributes, fields['field'])} 必須等於 {fields['value']}"
    if rule_type == "in":
        items = [x.strip() for x in fields["set"].split(";") if x.strip()]
        return f"{_attr_desc(attributes, fields['field'])} 必須屬於：{ '、'.join(items) }"
    if rule_type == "participant_in_target_field":
        pd = _attr_desc(attributes, f"participant.{fields['participant_field']}")
        td = _attr_desc(attributes, f"target.{fields['target_field']}")
        mode = (fields.get("mode") or "auto").strip() or "auto"
        if mode == "equal":
            return f"{pd} 必須與對象的{td}完全相同"
        if mode == "participant_in_target":
            return f"{pd} 必須都在對象的{td}裡"
        if mode == "target_in_participant":
            return f"對象的{td} 必須都在{pd}裡"
        suffix = "（沒填值的一方視為不設限）" if fields.get("empty_ok") in ("true", "on", True, "1") else ""
        if mode == "intersect":
            return f"{pd} 與對象的{td} 必須有交集{suffix}"
        return f"{pd} 必須對應到對象的{td}（任一邊可多筆，做包含比對）{suffix}"  # auto
    raise ValueError(f"未知規則類型：{rule_type}")


def _collect_indexed_rows(form: dict, prefix: str, fields: list[str]) -> list[dict]:
    """從 form dict 中蒐集 `<prefix>_<i>_<field>` 模式的資料，回傳非空行的 list。

    例：prefix="participant_attr", fields=["key", "type", ...]
    → 找出所有 participant_attr_0_key / participant_attr_0_type / ... participant_attr_N_key /...
    → 每個 i 組為一個 dict；key 為空的行略過。
    """
    rows: dict[int, dict] = {}
    for k, v in form.items():
        for fld in fields:
            suffix = f"_{fld}"
            if k.startswith(f"{prefix}_") and k.endswith(suffix):
                middle = k[len(prefix) + 1 : -len(suffix)]
                if middle.isdigit():
                    idx = int(middle)
                    rows.setdefault(idx, {})[fld] = v
    # 依 idx 排序，過濾掉「key 或主欄位為空」的行
    out = []
    main_key = fields[0]  # 慣例：第一個欄位是主鍵（如 key、id、participant_id）
    for idx in sorted(rows.keys()):
        row = rows[idx]
        if row.get(main_key, "").strip():
            out.append(row)
    return out


def assemble_template_yaml(form: dict) -> dict:
    """把簡單模式表單 dict 組成 parse_template 可接受的 YAML dict。

    form schema 見 specs/011-template-author-ui/data-model.md §3。
    """
    # 1. 基本資訊
    tpl: dict[str, Any] = {
        "schema_version": "1.0",
        "id": (form.get("template_id") or "").strip(),
        "name": (form.get("template_name") or "").strip(),
        "description": (form.get("template_description") or "").strip(),
    }

    # 2. attributes
    participant_attrs = _collect_indexed_rows(
        form, "participant_attr", ["key", "type", "required", "description", "aliases"]
    )
    target_attrs = _collect_indexed_rows(
        form, "target_attr", ["key", "type", "required", "description", "aliases"]
    )
    attributes = {
        "participants": [_attr_dict(r) for r in participant_attrs],
        "targets": [_attr_dict(r) for r in target_attrs],
    }
    tpl["attributes"] = attributes

    # 3. rules
    rule_rows = _collect_indexed_rows(
        form,
        "rule",
        ["id", "type", "field", "value", "set", "participant_field", "target_field", "mode", "empty_ok", "custom_description"],
    )
    rules = []
    for r in rule_rows:
        if not r.get("type"):
            continue
        expr = _build_expr(r["type"], r)
        custom = (r.get("custom_description") or "").strip()
        desc = custom or _auto_description(r["type"], r, attributes)
        rules.append({"id": r["id"], "description": desc, "expr": expr})
    tpl["rules"] = rules

    # 4. preferences_schema（可選）
    if form.get("prefs_enabled") in ("true", "on", True, "1"):
        tpl["preferences_schema"] = {
            "max_choices": int(form.get("prefs_max_choices", 3)),
            "required": form.get("prefs_required") in ("true", "on", True, "1"),
            "description": (form.get("prefs_description") or "").strip(),
        }

    # Feature 013：不再寫 default_targets（範本不內嵌對象資料）

    return tpl


def _attr_dict(row: dict) -> dict:
    """單行 attribute 欄位 → standard dict。"""
    out = {
        "key": row["key"].strip(),
        "type": row.get("type", "str").strip() or "str",
        "required": row.get("required") in ("true", "on", True, "1"),
        "description": (row.get("description") or "").strip(),
    }
    aliases_raw = (row.get("aliases") or "").strip()
    if aliases_raw:
        out["aliases"] = [a.strip() for a in aliases_raw.split(",") if a.strip()]
    return out


def _coerce_value(raw: Any, type_str: str) -> Any:
    raw = str(raw).strip()
    if type_str == "int":
        return int(raw) if raw else 0
    if type_str == "list_str":
        return [x.strip() for x in raw.split(";") if x.strip()]
    return raw


# ── 場景樣板（簡單模式快速起點）────────────────────────────────

SCENARIO_TEMPLATES = {
    "blank": {
        "template_id": "",
        "template_name": "",
        "template_description": "",
    },
    "club-signup": {
        "template_id": "club-signup",
        "template_name": "社團報名",
        "template_description": "依年級與興趣分配學生到社團",
        "participant_attr_0_key": "name", "participant_attr_0_type": "str", "participant_attr_0_required": "on",
        "participant_attr_0_description": "學生姓名", "participant_attr_0_aliases": "姓名",
        "participant_attr_1_key": "grade", "participant_attr_1_type": "int", "participant_attr_1_required": "on",
        "participant_attr_1_description": "年級", "participant_attr_1_aliases": "年級",
        "participant_attr_2_key": "interest", "participant_attr_2_type": "str", "participant_attr_2_required": "on",
        "participant_attr_2_description": "興趣", "participant_attr_2_aliases": "興趣",
        "target_attr_0_key": "name", "target_attr_0_type": "str", "target_attr_0_required": "on",
        "target_attr_0_description": "社團名稱", "target_attr_0_aliases": "社團名稱",
        "target_attr_1_key": "topic", "target_attr_1_type": "str", "target_attr_1_required": "on",
        "target_attr_1_description": "社團主題", "target_attr_1_aliases": "主題",
        "target_attr_2_key": "min_grade", "target_attr_2_type": "int", "target_attr_2_required": "on",
        "target_attr_2_description": "最低年級", "target_attr_2_aliases": "最低年級",
        "rule_0_id": "R001", "rule_0_type": "ge",
        "rule_0_field": "participant.grade", "rule_0_value": "1",
        "rule_1_id": "R002", "rule_1_type": "participant_in_target_field",
        "rule_1_participant_field": "interest", "rule_1_target_field": "topic",
        "target_0_id": "C1", "target_0_capacity": "5",
        "target_0_name": "程式社", "target_0_topic": "program", "target_0_min_grade": "4",
        "target_1_id": "C2", "target_1_capacity": "5",
        "target_1_name": "音樂社", "target_1_topic": "music", "target_1_min_grade": "3",
        "target_2_id": "C3", "target_2_capacity": "4",
        "target_2_name": "美術社", "target_2_topic": "art", "target_2_min_grade": "3",
        "prefs_enabled": "on", "prefs_max_choices": "3", "prefs_description": "每位學生可填 1~3 個社團志願",
    },
    "tutoring": {
        "template_id": "tutoring",
        "template_name": "課輔師生媒合",
        "template_description": "依專業配對課輔老師到學生需求",
        "participant_attr_0_key": "name", "participant_attr_0_type": "str", "participant_attr_0_required": "on",
        "participant_attr_0_description": "老師姓名", "participant_attr_0_aliases": "姓名",
        "participant_attr_1_key": "specialities", "participant_attr_1_type": "list_str", "participant_attr_1_required": "on",
        "participant_attr_1_description": "可教科目", "participant_attr_1_aliases": "可教科目",
        "target_attr_0_key": "name", "target_attr_0_type": "str", "target_attr_0_required": "on",
        "target_attr_0_description": "學生姓名", "target_attr_0_aliases": "學生姓名",
        "target_attr_1_key": "subject", "target_attr_1_type": "str", "target_attr_1_required": "on",
        "target_attr_1_description": "需要輔導的科目", "target_attr_1_aliases": "科目",
        "rule_0_id": "R001", "rule_0_type": "participant_in_target_field",
        "rule_0_participant_field": "specialities", "rule_0_target_field": "subject",
    },
}
