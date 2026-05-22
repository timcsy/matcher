"""YAML 載入：ruleset / roster / preferences。

使用 yaml.safe_load 避免任意 Python 物件構造。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from matcher.roster import Roster, parse_roster
from matcher.rules import Ruleset, parse_ruleset
from matcher.template import Template
from matcher.template_loader import load_template_file as _load_template_file


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ruleset(path: str | Path) -> Ruleset:
    data = _load_yaml(Path(path))
    if not isinstance(data, dict):
        raise ValueError(f"規則檔 `{path}` 根層級必須為 mapping")
    return parse_ruleset(data)


def load_roster(path: str | Path) -> Roster:
    data = _load_yaml(Path(path))
    if not isinstance(data, dict):
        raise ValueError(f"名單檔 `{path}` 根層級必須為 mapping")
    return parse_roster(data)


def load_template(path: str | Path) -> Template:
    """載入外部模板檔。"""
    return _load_template_file(path)


def load_preferences(path: str | Path | None) -> dict:
    """載入 preferences YAML；回傳空 dict 表示無偏好。

    若 path 為 None 或檔案內容為 None/空，回傳 {}。
    """
    if path is None:
        return {}
    data = _load_yaml(Path(path))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"志願檔 `{path}` 根層級必須為 mapping（或空檔）")
    return dict(data)
