"""範本擁有者 / 可見性 meta（web 層 sidecar，不動核心 template_loader）。

存於 `<custom_dir>/<tpl_id>/meta.json`：{"owner": email, "visibility": "private"|"public"}。
內建範本無 meta：視為「對所有登入者可見、可複製、不可編輯」。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

DEFAULT_VISIBILITY = "private"


def _meta_path(custom_dir, tpl_id: str) -> Path:
    from matcher.web.store import safe_fs_id
    return Path(custom_dir) / safe_fs_id(tpl_id) / "meta.json"


def read_meta(custom_dir, tpl_id: str) -> dict:
    try:
        p = _meta_path(custom_dir, tpl_id)
    except ValueError:
        return {"owner": None, "visibility": DEFAULT_VISIBILITY}
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            return {
                "owner": d.get("owner"),
                "visibility": d.get("visibility", DEFAULT_VISIBILITY),
            }
        except (ValueError, OSError):
            pass
    return {"owner": None, "visibility": DEFAULT_VISIBILITY}


def write_meta(custom_dir, tpl_id: str, owner: Optional[str], visibility: str) -> None:
    p = _meta_path(custom_dir, tpl_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"owner": owner, "visibility": visibility}, ensure_ascii=False),
        encoding="utf-8",
    )


def can_view(reg, tpl_id: str, email: Optional[str]) -> bool:
    """誰能看：內建 / 公開 / 自己擁有。"""
    if reg.is_builtin(tpl_id):
        return True
    meta = read_meta(reg._custom_dir, tpl_id)
    return meta["visibility"] == "public" or (email is not None and meta["owner"] == email)


def is_owner(reg, tpl_id: str, email: Optional[str]) -> bool:
    if email is None or reg.is_builtin(tpl_id):
        return False
    return read_meta(reg._custom_dir, tpl_id)["owner"] == email
