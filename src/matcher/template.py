"""模板資料模型（dataclass）。

依 data-model.md 欄位定義；解析器在 template_loader.py。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from matcher.rules import Ruleset


@dataclass(frozen=True)
class AttributeDecl:
    key: str
    type: Literal["str", "int", "list_str"]
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class AttributeSchema:
    roles: tuple = ()
    targets: tuple = ()


@dataclass(frozen=True)
class UIFieldDecl:
    key: str
    label: str
    type: Literal["text", "number", "select", "multiselect", "textarea"]
    required: bool = True
    options: Optional[tuple] = None
    placeholder: Optional[str] = None
    help: Optional[str] = None


@dataclass(frozen=True)
class ReportFieldDecl:
    key: str
    label: str
    source: str


@dataclass(frozen=True)
class PreferencesSchema:
    max_choices: int
    required: bool
    description: str


@dataclass(frozen=True)
class Template:
    schema_version: str
    id: str
    name: str
    description: str
    attributes: AttributeSchema
    ruleset: Ruleset
    ui_fields: tuple = ()
    report_fields: tuple = ()
    preferences_schema: Optional[PreferencesSchema] = None
