"""代名詞替換：把規則描述中的 role.X / target.X 換成一般教師熟悉的中文用語。"""

from __future__ import annotations

import re
from typing import Any

ROLE_PATTERN = re.compile(r"role\.(\w+)")
TARGET_PATTERN = re.compile(r"target\.(\w+)")


def _attr_display_name(side_attrs: tuple, key: str) -> str:
    """從 attributes 宣告中找 description；無則 fallback 用 key 原樣。"""
    for decl in side_attrs:
        if decl.key == key:
            return decl.description or key
    return key


def humanize_rule_description(description: str, template: Any) -> str:
    """將模板規則描述中的 role.X / target.X 替換為一般人用語。

    - `role.<key>` → 「您的 <顯示名>」
    - `target.<key>` → 「該對象的 <顯示名>」
    - 顯示名來自 template.attributes.{roles,targets}[].description；無則用 key
    - 不含 role./target. token 的字串原樣回傳
    """
    if not description:
        return description

    def _role_repl(m: re.Match) -> str:
        return f"您的 {_attr_display_name(template.attributes.roles, m.group(1))}"

    def _target_repl(m: re.Match) -> str:
        return f"該對象的 {_attr_display_name(template.attributes.targets, m.group(1))}"

    out = ROLE_PATTERN.sub(_role_repl, description)
    out = TARGET_PATTERN.sub(_target_repl, out)
    return out


_MECHANISM_LABELS = {
    "M0": "純抽籤",
    "M1": "輪流挑",
    "M2": "依志願先後填滿",
}

_MECHANISM_DESCRIPTIONS = {
    "M0": "所有人不填志願、完全公平隨機（適合：分組順序無偏好的場景）",
    "M1": "按隨機順序，每個人輪流挑自己最高志願（適合：研習分組、社團選填）",
    "M2": "先把每組的第一志願填滿，剩下的人再填第二志願⋯（適合：志願清楚分高低的場景）",
}


def mechanism_description(mechanism: str) -> str:
    return _MECHANISM_DESCRIPTIONS.get(mechanism, "")


def mechanism_label(mechanism: str) -> str:
    """機制代號 → 顯示名。未知值原樣回傳。"""
    return _MECHANISM_LABELS.get(mechanism, mechanism)


def target_summary(target: dict) -> str:
    """填志願頁的「候選對象」段與下拉選項文字。

    格式：「<name>（容量 <N> 人）」；無 name 用 id；無 capacity 僅顯示名。
    """
    name = target.get("name") or target.get("id", "")
    capacity = target.get("capacity")
    if capacity is None:
        return name
    return f"{name}（容量 {capacity} 人）"


def preference_rank_display(
    mechanism: str,
    preference_rank: int | None,
    fallback_random_index: int | None,
) -> str | None:
    """志願排名欄文案；M0 路徑回 None（呼叫端應隱藏整欄）。"""
    if mechanism == "M0":
        return None
    if preference_rank is not None:
        return f"第 {preference_rank} 志願"
    if fallback_random_index is not None:
        return "抽籤"
    return ""
