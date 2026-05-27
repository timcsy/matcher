"""依範本 schema 動態產生範例試算表（feature 016）。

範例定位：教使用者「這個範本要填哪些欄、什麼格式」，不保證原樣可跑。
表頭用中文顯示名稱；第二列為格式提示（數字／多筆用分號隔開／文字）。
涵蓋自訂範本、永遠與範本同步。
"""

from __future__ import annotations

import csv
import io

from matcher.template import Template

_TYPE_HINT = {
    "int": "（數字）",
    "list_str": "（多筆用分號隔開，如 國文;數學）",
    "str": "（文字）",
}


def _role_columns(template: Template) -> tuple[list[str], list[str]]:
    """回 (表頭, 提示列)。角色：編號 + 各角色屬性。"""
    headers = ["編號"]
    hints = ["（可留空，系統自動編號）"]
    for a in template.attributes.roles:
        headers.append(a.description or a.key)
        hints.append(_TYPE_HINT.get(a.type, "（文字）"))
    if template.preferences_schema is not None:
        headers.append("志願")
        hints.append("（多筆用分號隔開，依序填志願）")
    return headers, hints


def _target_columns(template: Template) -> tuple[list[str], list[str]]:
    """回 (表頭, 提示列)。對象：編號 + 容量 + 各對象屬性。"""
    headers = ["編號", "容量"]
    hints = ["（可留空，系統自動編號）", "（數字，最多容納幾位）"]
    for a in template.attributes.targets:
        headers.append(a.description or a.key)
        hints.append(_TYPE_HINT.get(a.type, "（文字）"))
    return headers, hints


def _csv_bytes(headers: list[str], hints: list[str]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerow(hints)
    return ("﻿" + buf.getvalue()).encode("utf-8")  # utf-8-sig，Excel 開不亂碼


def _xlsx_bytes(headers: list[str], hints: list[str]) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    ws.append(hints)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def role_example_bytes(template: Template, fmt: str) -> bytes:
    headers, hints = _role_columns(template)
    return _xlsx_bytes(headers, hints) if fmt == "xlsx" else _csv_bytes(headers, hints)


def target_example_bytes(template: Template, fmt: str) -> bytes:
    headers, hints = _target_columns(template)
    return _xlsx_bytes(headers, hints) if fmt == "xlsx" else _csv_bytes(headers, hints)
