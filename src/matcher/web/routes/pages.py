"""頁面路由：首頁、模板列表、模板詳情、模板創作工具（feature 011）。"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from matcher.errors import TemplateNotFound
from matcher.template_loader import (
    TemplateRegistry,
    dump_template_yaml,
    parse_template,
)
from matcher.web.template_form import SCENARIO_TEMPLATES, assemble_template_yaml

router = APIRouter()

# Module-level singleton：所有 routes 共用同一 registry instance，
# 寫入後 invalidate() 立即生效。
_registry = TemplateRegistry()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _reg() -> TemplateRegistry:
    return _registry


@router.get("/")
async def index(request: Request):
    return _templates(request).TemplateResponse(request, "index.html", {})


@router.get("/templates")
async def templates_list(request: Request):
    reg = _reg()
    items = [
        {"tpl": reg.get(tid), "is_builtin": reg.is_builtin(tid)}
        for tid in reg.list_ids()
    ]
    return _templates(request).TemplateResponse(
        request, "templates_list.html", {"templates": items}
    )


@router.get("/templates/new")
async def template_new(
    request: Request,
    scenario: Optional[str] = None,
    mode: str = "simple",
    fork: Optional[str] = None,
    edit_id: Optional[str] = None,
):
    """新增模板頁；可預填場景樣板、fork 內建模板、或編輯既有模板的最新版本。"""
    reg = _reg()
    prefill: dict = {}
    if edit_id and not reg.is_builtin(edit_id):
        # 編輯模式：載入最新版本
        try:
            latest_v = max(reg.list_versions(edit_id))
            tpl = reg.get_version(edit_id, latest_v)
            prefill = _template_to_form_dict(tpl)
        except (ValueError, TemplateNotFound):
            raise HTTPException(404, "找不到自訂模板")
    elif fork and reg.is_builtin(fork):
        tpl = reg.get(fork)
        prefill = _template_to_form_dict(tpl)
        prefill["template_id"] = f"{fork}-fork"
    elif scenario and scenario in SCENARIO_TEMPLATES:
        prefill = dict(SCENARIO_TEMPLATES[scenario])

    # Feature 011 動態表單：依 prefill 計算每段初始要 render 幾行
    import re as _re
    def _max_idx(prefix: str) -> int:
        out = -1
        for k in prefill:
            m = _re.match(rf"^{prefix}_(\d+)_", k)
            if m:
                out = max(out, int(m.group(1)))
        return out

    return _templates(request).TemplateResponse(
        request, "template_authoring.html",
        {
            "mode": mode,
            "scenarios": list(SCENARIO_TEMPLATES.keys()),
            "prefill": prefill,
            "edit_id": edit_id,
            "fork_from": fork,
            "role_attr_count": max(1, _max_idx("role_attr") + 1),
            "target_attr_count": max(1, _max_idx("target_attr") + 1),
            "rule_count": max(1, _max_idx("rule") + 1),
            "target_count": max(1, _max_idx("target") + 1),
        },
    )


def _template_to_form_dict(tpl) -> dict:
    """Template → form-shape dict（給 fork / edit 預填用）。"""
    out = {
        "template_id": tpl.id,
        "template_name": tpl.name,
        "template_description": tpl.description,
    }
    for i, attr in enumerate(tpl.attributes.roles):
        out[f"role_attr_{i}_key"] = attr.key
        out[f"role_attr_{i}_type"] = attr.type
        out[f"role_attr_{i}_required"] = "on" if attr.required else ""
        out[f"role_attr_{i}_description"] = attr.description or ""
        out[f"role_attr_{i}_aliases"] = ", ".join(attr.aliases or [])
    for i, attr in enumerate(tpl.attributes.targets):
        out[f"target_attr_{i}_key"] = attr.key
        out[f"target_attr_{i}_type"] = attr.type
        out[f"target_attr_{i}_required"] = "on" if attr.required else ""
        out[f"target_attr_{i}_description"] = attr.description or ""
        out[f"target_attr_{i}_aliases"] = ", ".join(attr.aliases or [])
    if tpl.preferences_schema:
        out["prefs_enabled"] = "on"
        out["prefs_max_choices"] = str(tpl.preferences_schema.max_choices)
        out["prefs_description"] = tpl.preferences_schema.description or ""
    return out


def _validate_id_format(tpl_id: str) -> None:
    import re as _re
    if not tpl_id:
        raise ValueError("模板 id 不可為空")
    if not _re.fullmatch(r"[a-z0-9-]+", tpl_id):
        raise ValueError(f"模板 id `{tpl_id}` 格式不合法；僅允許小寫英數字與連字號")


def _build_tpl_dict_from_form(form: dict) -> dict:
    """簡單 vs 進階模式分派。"""
    mode = form.get("mode", "simple")
    if mode == "advanced":
        raw = form.get("raw_yaml", "")
        if not raw.strip():
            raise ValueError("YAML 內容為空")
        return yaml.safe_load(raw)
    return assemble_template_yaml(form)


@router.post("/templates/validate")
async def template_validate(request: Request):
    form = dict(await request.form())
    try:
        tpl_dict = _build_tpl_dict_from_form(form)
        _validate_id_format(tpl_dict.get("id", ""))
        tpl = parse_template(tpl_dict)
    except yaml.YAMLError as e:
        return JSONResponse({"ok": False, "errors": [f"YAML 語法錯誤：{e}"]})
    except (ValueError, Exception) as e:
        return JSONResponse({"ok": False, "errors": [str(e)]})

    summary = {
        "id": tpl.id,
        "name": tpl.name,
        "attribute_count": {
            "roles": len(tpl.attributes.roles),
            "targets": len(tpl.attributes.targets),
        },
        "rule_count": len(tpl.ruleset.rules),
        "has_preferences_schema": tpl.preferences_schema is not None,
    }
    return JSONResponse({"ok": True, "summary": summary})


@router.post("/templates/save")
async def template_save(request: Request):
    form = dict(await request.form())
    try:
        tpl_dict = _build_tpl_dict_from_form(form)
    except yaml.YAMLError as e:
        return JSONResponse({"ok": False, "errors": [f"YAML 語法錯誤：{e}"]}, status_code=400)
    except ValueError as e:
        return JSONResponse({"ok": False, "errors": [str(e)]}, status_code=400)

    try:
        tpl_id, version = _reg().save_custom(tpl_dict)
    except ValueError as e:
        msg = str(e)
        if "內建模板" in msg:
            return JSONResponse({"ok": False, "errors": [msg]}, status_code=409)
        return JSONResponse({"ok": False, "errors": [msg]}, status_code=400)
    return JSONResponse({
        "ok": True, "id": tpl_id, "version": version,
        "redirect_to": f"/templates/{tpl_id}",
    })


@router.get("/templates/authoring-guide.txt")
async def template_authoring_guide():
    """提供 docs/template-authoring-guide.md 內容（給前端 JS fetch 用）。"""
    from pathlib import Path as _P
    guide = _P(__file__).resolve().parents[4] / "docs" / "template-authoring-guide.md"
    if not guide.exists():
        raise HTTPException(404, "找不到 docs/template-authoring-guide.md")
    return Response(content=guide.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")


@router.get("/templates/{template_id}/versions/{version}")
async def template_get_version(template_id: str, version: int):
    reg = _reg()
    if reg.is_builtin(template_id):
        raise HTTPException(404, "內建模板沒有版本概念")
    try:
        tpl = reg.get_version(template_id, version)
    except TemplateNotFound as e:
        raise HTTPException(404, str(e))
    yaml_text = yaml.safe_dump(_template_to_yaml_dict(tpl), allow_unicode=True, sort_keys=False)
    return Response(
        content=yaml_text, media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{template_id}-v{version}.yaml"'},
    )


def _template_to_yaml_dict(tpl) -> dict:
    """Template → 完整 YAML dict（給版本歷史查看）。複用 dump_template_yaml 邏輯但回 dict。"""
    # dump_template_yaml 寫檔；這裡需 dict
    import io
    from pathlib import Path as _P
    import tempfile as _t
    with _t.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        tmp_path = _P(tmp.name)
    dump_template_yaml(tpl, tmp_path)
    with tmp_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
    tmp_path.unlink(missing_ok=True)
    return result


@router.get("/templates/{template_id}")
async def template_detail(request: Request, template_id: str):
    reg = _reg()
    try:
        tpl = reg.get(template_id)
    except TemplateNotFound as e:
        return _templates(request).TemplateResponse(
            request,
            "error_page.html",
            {"error_type": "TemplateNotFound", "error_message": str(e)},
            status_code=404,
        )
    is_builtin = reg.is_builtin(template_id)
    versions = []
    if not is_builtin:
        for v in reg.list_versions(template_id):
            path = reg._custom_dir / template_id / f"v{v}.yaml"
            mtime = _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if path.exists() else ""
            versions.append({"n": v, "mtime": mtime})
    current_version = max((v["n"] for v in versions), default=None)
    return _templates(request).TemplateResponse(
        request, "template_detail.html",
        {
            "tpl": tpl,
            "is_builtin": is_builtin,
            "versions": versions,
            "current_version": current_version,
        },
    )


@router.get("/templates/{template_id}/edit")
async def template_edit(request: Request, template_id: str):
    reg = _reg()
    if reg.is_builtin(template_id):
        raise HTTPException(403, "內建模板不可編輯；請使用 Fork 為自訂模板")
    if not reg.has(template_id):
        raise HTTPException(404, "找不到自訂模板")
    return await template_new(request, edit_id=template_id)
