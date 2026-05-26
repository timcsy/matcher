"""UI 表單 → CSV bytes / targets sidecar YAML bytes 純函式。

設計策略（research D1/D2）：UI 填寫頁的資料先組成 CSV bytes（in-memory），
透過既有 data_import.load_roster_csv 載入，確保與「使用者直接上傳 CSV」路徑
產出的 audit 100% bytewise 等價，避免重做 id 生成 / aliases 對齊邏輯。
"""

from __future__ import annotations

import csv
import io
from typing import Any

import yaml

from matcher.template import Template


def _collect_indexed_rows(form: dict, prefix: str, fields: list[str]) -> list[dict]:
    """從 form dict 蒐集 `<prefix>_<i>_<field>` 模式的資料 → list of dicts。

    主鍵欄位（fields[0]）為空的列會被過濾。
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
    return [rows[idx] for idx in sorted(rows.keys())]


def _is_empty_row(row: dict, attribute_keys: list[str]) -> bool:
    """行內 attribute 欄位全空 → 視為空白行（id 可空、會被自動生成）。"""
    for k in attribute_keys:
        v = row.get(k, "").strip()
        if v:
            return False
    return True


import re

_MULTI_SEP = re.compile(r"[;；、,，]+")


def _normalize_multi(raw: str) -> str:
    """把使用者可能用的分隔符（；、,，）統一成分號 ;，讓下游 data_import 正確切分。"""
    parts = [p.strip() for p in _MULTI_SEP.split(raw) if p.strip()]
    return ";".join(parts)


def assemble_roster_csv_bytes(form: dict, template: Template) -> bytes:
    """UI 表單 → CSV bytes（與直接上傳 CSV 路徑 bytewise 等價）。

    流程：
    1. 蒐集 role_<i>_<key> 欄位
    2. 過濾「所有 attribute 都空白」的列
    3. 組 CSV header：id + 範本宣告的每個 attribute key（按宣告順序）
    4. 對每位角色寫一行
    5. 回 utf-8-sig bytes（沿用既有 CSV path 的 BOM 處理）
    """
    role_keys = [a.key for a in template.attributes.roles]
    # 若範本有 preferences_schema，加 preferences 欄
    has_prefs = template.preferences_schema is not None

    fields = ["id"] + role_keys + (["preferences"] if has_prefs else [])
    rows = _collect_indexed_rows(form, "role", fields)
    non_empty = [r for r in rows if not _is_empty_row(r, role_keys)]

    # 哪些欄位需要分隔符正規化：list_str 屬性 + preferences
    multi_keys = {a.key for a in template.attributes.roles if a.type == "list_str"}
    if has_prefs:
        multi_keys.add("preferences")

    buf = io.StringIO()
    headers = ["id"] + role_keys + (["preferences"] if has_prefs else [])
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for row in non_empty:
        out = {}
        for h in headers:
            val = (row.get(h, "") or "").strip()
            out[h] = _normalize_multi(val) if h in multi_keys else val
        writer.writerow(out)
    # utf-8-sig 加 BOM 與既有 CSV path 一致（避免 Excel 亂碼）
    return ("﻿" + buf.getvalue()).encode("utf-8")


def assemble_targets_yaml_bytes(form: dict, template: Template) -> bytes | None:
    """UI 表單對象段 → sidecar YAML bytes。

    Feature 013：range 一律由 UI 填或旁檔提供。
    - 未填任何對象 → 回 None（呼叫方依此判斷 400）
    - 有對象資料 → 組成 {targets: [{id, capacity, attributes: {...}}, ...]} bytes
    - 對象空白列自動過濾
    """
    target_keys = [a.key for a in template.attributes.targets]
    fields = ["id", "capacity"] + target_keys
    rows = _collect_indexed_rows(form, "target", fields)

    targets_list = []
    for row in rows:
        tid = (row.get("id") or "").strip()
        if not tid:
            continue
        cap_str = (row.get("capacity") or "").strip()
        if not cap_str:
            continue
        attrs: dict[str, Any] = {}
        for decl in template.attributes.targets:
            raw = (row.get(decl.key) or "").strip()
            if not raw:
                continue
            if decl.type == "int":
                attrs[decl.key] = int(raw)
            elif decl.type == "list_str":
                attrs[decl.key] = [x.strip() for x in _MULTI_SEP.split(raw) if x.strip()]
            else:
                attrs[decl.key] = raw
        targets_list.append({"id": tid, "capacity": int(cap_str), "attributes": attrs})

    if not targets_list:
        return None
    return yaml.safe_dump({"targets": targets_list}, allow_unicode=True, sort_keys=False).encode("utf-8")
