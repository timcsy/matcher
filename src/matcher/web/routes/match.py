"""媒合路由：新建媒合（含向導）、執行、結果頁、下載 audit。"""

from __future__ import annotations

import base64
import dataclasses
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from matcher.data_import import load_roster_csv, load_roster_xlsx
from matcher.errors import MatcherError, SeedMissing, TemplateNotFound
from matcher.pipeline import MatcherInput, run_match
from matcher.template_loader import TemplateRegistry
from matcher.web.errors import MatchRecordNotFound, UploadInvalidMime, UploadTooLarge
from matcher.web.humanize import mechanism_label, preference_rank_display, target_summary
from matcher.web.individual import build_individual_audit_subset
from matcher.web.pdf import PdfRenderUnavailable, render_match_report_pdf
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

MECHANISMS = [
    ("M0", "M0 純抽籤"),
    ("M1", "M1 RSD（隨機輪流挑）"),
    ("M2", "M2 Boston（層級填滿）"),
]
VALID_MECHANISMS = {value for value, _ in MECHANISMS}
ALLOWED_MIMES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",  # 某些瀏覽器對 .xlsx 仍回 ms-excel
}


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/match/new")
async def new_match(request: Request, template_id: Optional[str] = None):
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    reg = _shared_reg()
    items = [reg.get(tid) for tid in reg.list_ids()]
    return _templates(request).TemplateResponse(
        request, "new_match.html",
        {
            "templates": items,
            "selected_id": template_id,
            "mechanisms": MECHANISMS,
            "default_mechanism": "M0",
        },
    )


@router.post("/match/run")
async def run(
    request: Request,
    template_id: str = Form(...),
    seed: int = Form(...),
    roster: UploadFile = File(...),
    mechanism: str = Form("M0"),
):
    # 驗證機制
    mechanism = (mechanism or "M0").strip().upper()
    if mechanism not in VALID_MECHANISMS:
        return _templates(request).TemplateResponse(
            request, "error_page.html",
            {
                "error_type": "InvalidMechanism",
                "error_message": f"不支援的機制：{mechanism}（請選 M0、M1、M2）",
            },
            status_code=400,
        )

    # 驗證大小
    data = await roster.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadTooLarge(
            f"上傳檔過大（{len(data)} bytes，上限 {MAX_UPLOAD_BYTES} bytes / 5 MB）。\n"
            f"建議：縮減檔案後重新上傳，或拆分成多次媒合。"
        )

    # 驗證 MIME
    if roster.content_type not in ALLOWED_MIMES:
        raise UploadInvalidMime(
            f"上傳檔類型不支援：{roster.content_type}。\n"
            f"細節：僅接受 CSV（text/csv）與 Excel（.xlsx）。\n"
            f"建議：另存為 CSV 或 .xlsx 後重新上傳。"
        )

    # 載入模板
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    try:
        reg = _shared_reg()
        tpl = reg.get(template_id)
    except TemplateNotFound as e:
        return _templates(request).TemplateResponse(
            request, "error_page.html",
            {"error_type": "TemplateNotFound", "error_message": str(e)},
            status_code=404,
        )

    # 寫到 tmp 並讀取
    suffix = Path(roster.filename or "upload").suffix.lower()
    is_xlsx = suffix == ".xlsx" or "spreadsheetml" in (roster.content_type or "")

    store = MatchStore()
    record_id = MatchRecord.new_id()
    now = datetime.now(timezone.utc).isoformat()
    common = dict(
        schema_version=SCHEMA_VERSION,
        id=record_id,
        created_at=now,
        template_id=template_id,
        seed=seed,
        input_file=roster.filename,
        mechanism=mechanism,
    )

    with tempfile.NamedTemporaryFile(suffix=suffix or (".xlsx" if is_xlsx else ".csv"), delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        try:
            if is_xlsx:
                ro, import_meta = load_roster_xlsx(tmp_path, tpl)
            else:
                ro, import_meta = load_roster_csv(tmp_path, tpl)

            # 修正 import_metadata 中的 basename 為原檔名（避免暴露 tmp 路徑）
            import_meta["file_basename"] = roster.filename or import_meta["file_basename"]

            # Feature 009：偵測「需要使用者填志願」→ 跳到中介頁，不執行 pipeline
            if (
                tpl.preferences_schema is not None
                and mechanism in ("M1", "M2")
                and all(not role.preferences for role in ro.roles)
            ):
                tmp_path.unlink(missing_ok=True)
                return _render_preferences_form(
                    request, template_id=template_id, template_name=tpl.name,
                    mechanism=mechanism, seed=seed,
                    roster_bytes=data, roster_filename=roster.filename or "roster.csv",
                    roles=ro.roles, default_targets=tpl.default_targets,
                    max_choices=tpl.preferences_schema.max_choices,
                )

            result = run_match(MatcherInput(
                ruleset=tpl.ruleset,
                roster=ro,
                seed=seed,
                preferences=None,
                mechanism=mechanism,
                template=tpl,
                import_metadata=import_meta,
            ))
            record = MatchRecord(**common, status="success", audit=result.audit, error=None)
        except MatcherError as e:
            record = MatchRecord(
                **common, status="failed", audit=None,
                error={"type": type(e).__name__, "exit_code": e.exit_code, "message": str(e)},
            )
    finally:
        tmp_path.unlink(missing_ok=True)

    store.save(record)
    return RedirectResponse(url=f"/match/{record.id}", status_code=303)


# ── Feature 009：填志願表單中介頁面 ────────────────────────────

def _render_preferences_form(
    request: Request,
    *,
    template_id: str,
    template_name: str,
    mechanism: str,
    seed: int,
    roster_bytes: bytes,
    roster_filename: str,
    roles,
    default_targets,
    max_choices: int,
    form_errors: Optional[list] = None,
    previous_form_values: Optional[dict] = None,
    status_code: int = 200,
):
    """渲染填志願中介頁面。default_targets 為空 tuple → 樣板顯示錯誤段。"""
    targets_for_options = None
    if default_targets:
        targets_for_options = [
            {
                "id": t.id,
                "name": (t.attributes or {}).get("name", t.id),
                "capacity": t.capacity,
                "summary": target_summary({
                    "id": t.id,
                    "name": (t.attributes or {}).get("name", t.id),
                    "capacity": t.capacity,
                }),
            }
            for t in default_targets
        ]
    roles_for_form = [
        {"id": r.id, "display_name": (r.attributes or {}).get("name", r.id)}
        for r in roles
    ]
    return _templates(request).TemplateResponse(
        request, "preferences_form.html",
        {
            "template_id": template_id,
            "template_name": template_name,
            "mechanism": mechanism,
            "mechanism_label": mechanism_label(mechanism),
            "seed": seed,
            "roster_bytes_b64": base64.b64encode(roster_bytes).decode("ascii"),
            "roster_filename": roster_filename,
            "roles_for_form": roles_for_form,
            "targets_for_options": targets_for_options,
            "max_choices": max_choices,
            "form_errors": form_errors or [],
            "previous_form_values": previous_form_values or {},
        },
        status_code=status_code,
    )


def _error_page(request: Request, error_type: str, message: str, status_code: int = 400):
    return _templates(request).TemplateResponse(
        request, "error_page.html",
        {"error_type": error_type, "error_message": message},
        status_code=status_code,
    )


@router.post("/match/preferences")
async def submit_preferences(request: Request):
    form = await request.form()
    try:
        template_id = form["template_id"]
        mechanism = (form["mechanism"] or "M0").strip().upper()
        seed = int(form["seed"])
        roster_bytes_b64 = form["roster_bytes_b64"]
        roster_filename = form["roster_filename"]
        action = form.get("_action", "submit")
    except (KeyError, ValueError):
        return _error_page(request, "PreferencesFormCorrupt", "填志願表單資料異常，請回到上一步重新上傳。")

    try:
        roster_bytes = base64.b64decode(roster_bytes_b64)
    except Exception:
        return _error_page(request, "PreferencesFormCorrupt", "填志願表單資料異常，請回到上一步重新上傳。")

    try:
        from matcher.web.routes.pages import _reg as _shared_reg
        tpl = _shared_reg().get(template_id)
    except TemplateNotFound as e:
        return _error_page(request, "TemplateNotFound", str(e), status_code=404)

    suffix = Path(roster_filename).suffix.lower()
    is_xlsx = suffix == ".xlsx"

    with tempfile.NamedTemporaryFile(suffix=suffix or ".csv", delete=False) as tmp:
        tmp.write(roster_bytes)
        tmp_path = Path(tmp.name)

    try:
        try:
            if is_xlsx:
                ro, import_meta = load_roster_xlsx(tmp_path, tpl)
            else:
                ro, import_meta = load_roster_csv(tmp_path, tpl)
            import_meta["file_basename"] = roster_filename
        except MatcherError as e:
            return _error_page(request, type(e).__name__, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    max_choices = tpl.preferences_schema.max_choices if tpl.preferences_schema else 0
    valid_target_ids = {t.id for t in tpl.default_targets}

    # _action == "submit"：驗證 + 組裝；"skip"：保留空 prefs 直接跑
    form_errors: list[str] = []
    previous_form_values: dict[str, str] = {}
    if action == "submit":
        new_roles = []
        any_pref = False
        for role in ro.roles:
            prefs: list[str] = []
            for rank in range(1, max_choices + 1):
                field = f"pref_{role.id}_{rank}"
                value = (form.get(field) or "").strip()
                previous_form_values[field] = value
                if value:
                    if value not in valid_target_ids:
                        form_errors.append(f"角色 {role.id} 的第 {rank} 志願選了無效的對象「{value}」。")
                        continue
                    prefs.append(value)
            if len(set(prefs)) != len(prefs):
                form_errors.append(f"角色 {role.id} 的志願中有重複——同列不可重複選同對象。")
            if prefs:
                any_pref = True
            new_roles.append(dataclasses.replace(role, preferences=tuple(prefs)))

        if form_errors:
            return _render_preferences_form(
                request,
                template_id=template_id, template_name=tpl.name,
                mechanism=mechanism, seed=seed,
                roster_bytes=roster_bytes, roster_filename=roster_filename,
                roles=ro.roles, default_targets=tpl.default_targets,
                max_choices=max_choices,
                form_errors=form_errors,
                previous_form_values=previous_form_values,
            )

        if not any_pref:
            form_errors.append("請至少為一位角色填寫 1 個志願；若確實沒有志願，請點「跳過此步驟」。")
            return _render_preferences_form(
                request,
                template_id=template_id, template_name=tpl.name,
                mechanism=mechanism, seed=seed,
                roster_bytes=roster_bytes, roster_filename=roster_filename,
                roles=ro.roles, default_targets=tpl.default_targets,
                max_choices=max_choices,
                form_errors=form_errors,
                previous_form_values=previous_form_values,
            )

        ro = dataclasses.replace(ro, roles=tuple(new_roles))
    # action == "skip" → ro 不動（preferences 全空），交由 pipeline reject

    # 跑 pipeline 並寫 record
    store = MatchStore()
    record_id = MatchRecord.new_id()
    now = datetime.now(timezone.utc).isoformat()
    common = dict(
        schema_version=SCHEMA_VERSION,
        id=record_id, created_at=now,
        template_id=template_id, seed=seed,
        input_file=roster_filename, mechanism=mechanism,
    )
    try:
        result = run_match(MatcherInput(
            ruleset=tpl.ruleset, roster=ro, seed=seed, preferences=None,
            mechanism=mechanism, template=tpl, import_metadata=import_meta,
        ))
        record = MatchRecord(**common, status="success", audit=result.audit, error=None)
    except MatcherError as e:
        record = MatchRecord(
            **common, status="failed", audit=None,
            error={"type": type(e).__name__, "exit_code": e.exit_code, "message": str(e)},
        )
    store.save(record)
    return RedirectResponse(url=f"/match/{record.id}", status_code=303)


@router.get("/match/{record_id}")
async def match_detail(request: Request, record_id: str):
    store = MatchStore()
    record = store.get(record_id)

    roles_for_links: list = []
    mechanism = "M0"
    processing_order_display = None
    rank_display_by_role: dict = {}
    if record.status == "success" and record.audit:
        roles_for_links = [
            {"id": r["id"], "name": r.get("attributes", {}).get("name", r["id"])}
            for r in record.audit.get("roster_snapshot", {}).get("roles", [])
        ]
        mechanism = record.audit.get("mechanism", "M0")
        # 處理順序段（M1/M2 才注入；M0 audit.processing_order 為 null）
        po = record.audit.get("processing_order")
        if po:
            name_by_id = {r["id"]: r.get("attributes", {}).get("name", r["id"])
                          for r in record.audit.get("roster_snapshot", {}).get("roles", [])}
            processing_order_display = [(rid, name_by_id.get(rid, rid)) for rid in po]
        # 志願排名欄（M1/M2）
        for entry in record.audit.get("allocation_trace", []):
            display = preference_rank_display(
                mechanism,
                entry.get("preference_rank"),
                entry.get("fallback_random_index"),
            )
            if display is not None:
                rank_display_by_role[entry["role_id"]] = display
    return _templates(request).TemplateResponse(
        request, "match_result.html",
        {
            "record": record,
            "roles_for_links": roles_for_links,
            "mechanism": mechanism,
            "mechanism_label": mechanism_label(mechanism),
            "processing_order_display": processing_order_display,
            "rank_display_by_role": rank_display_by_role,
        },
    )


def _individual_error(request: Request, message: str) -> Response:
    return _templates(request).TemplateResponse(
        request, "individual_error.html",
        {"message": message},
        status_code=404,
    )


@router.get("/match/{record_id}/role/{role_id}")
async def individual_view(request: Request, record_id: str, role_id: str):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        return _individual_error(request, "找不到該次媒合的紀錄")

    if record.status == "failed" or record.audit is None:
        return _individual_error(request, "該次媒合執行失敗，無個別查詢資料")

    role = next(
        (r for r in record.audit.get("roster_snapshot", {}).get("roles", []) if r["id"] == role_id),
        None,
    )
    if role is None:
        return _individual_error(request, "您不在這次媒合的名單中")

    # 載入模板（用於 humanize 規則描述）
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    reg = _shared_reg()
    try:
        template = reg.get(record.template_id)
    except TemplateNotFound:
        template = None

    subset = build_individual_audit_subset(record.audit, role_id)

    # US2：志願滿足度
    mechanism = record.audit.get("mechanism", "M0")
    preference_rank = None
    fallback_random_index = None
    for entry in record.audit.get("allocation_trace", []):
        if entry.get("role_id") == role_id:
            preference_rank = entry.get("preference_rank")
            fallback_random_index = entry.get("fallback_random_index")
            break
    preferred_count = len(role.get("preferences", []) or [])

    rules_lookup = {
        r["id"]: r["description"]
        for r in record.audit.get("rules_snapshot", {}).get("rules", [])
    }
    target_lookup = {
        t["id"]: t.get("attributes", {})
        for t in record.audit.get("roster_snapshot", {}).get("targets", [])
    }

    return _templates(request).TemplateResponse(
        request, "individual_view.html",
        {
            "record": record,
            "role": role,
            "subset": subset,
            "template": template,
            "rules_lookup": rules_lookup,
            "target_lookup": target_lookup,
            "mechanism": mechanism,
            "preference_rank": preference_rank,
            "fallback_random_index": fallback_random_index,
            "preferred_count": preferred_count,
        },
    )


@router.get("/match/{record_id}/role/{role_id}/audit.json")
async def individual_audit_download(request: Request, record_id: str, role_id: str):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次媒合的紀錄")

    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次媒合執行失敗，無個別查詢資料")

    role_exists = any(
        r["id"] == role_id
        for r in record.audit.get("roster_snapshot", {}).get("roles", [])
    )
    if not role_exists:
        raise HTTPException(status_code=404, detail="您不在這次媒合的名單中")

    subset = build_individual_audit_subset(record.audit, role_id)
    body = json.dumps(subset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{record_id}-{role_id}.individual.json"'
        },
    )


@router.get("/match/{record_id}/audit")
async def download_audit(request: Request, record_id: str):
    store = MatchStore()
    record = store.get(record_id)
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該媒合執行失敗，無稽核紀錄可下載")
    body = json.dumps(record.audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.audit.json"'},
    )


# ── Feature 010：PDF 報告匯出 ───────────────────────────────────

def _record_meta_for_pdf(record) -> dict:
    return {
        "id": record.id,
        "created_at": record.created_at,
        "input_file": record.input_file,
        "status": record.status,
        "error": record.error,
    }


@router.get("/match/{record_id}/report.pdf")
async def download_report_pdf(record_id: str):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次媒合的紀錄")

    # 失敗 record 也能出失敗版 PDF；audit 為 None 時樣板會走 failed 分支
    audit_for_pdf = record.audit if record.audit is not None else {
        "assignment": {}, "roster_snapshot": {"roles": [], "targets": []}, "mechanism": "M0",
    }
    try:
        pdf_bytes = render_match_report_pdf(audit_for_pdf, record_meta=_record_meta_for_pdf(record))
    except PdfRenderUnavailable as e:
        return Response(
            content=f"PDF 渲染功能不可用——{str(e)}（請見 README 安裝指引）",
            status_code=503, media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.report.pdf"'},
    )


@router.get("/match/{record_id}/role/{role_id}/report.pdf")
async def download_individual_report_pdf(record_id: str, role_id: str):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次媒合的紀錄")
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次媒合執行失敗，無個別查詢資料")
    role_exists = any(
        r["id"] == role_id for r in record.audit.get("roster_snapshot", {}).get("roles", [])
    )
    if not role_exists:
        raise HTTPException(status_code=404, detail="您不在這次媒合的名單中")

    try:
        tpl = TemplateRegistry().get(record.template_id)
    except TemplateNotFound:
        tpl = None
    try:
        pdf_bytes = render_match_report_pdf(
            record.audit, record_meta=_record_meta_for_pdf(record),
            role_id=role_id, template=tpl,
        )
    except PdfRenderUnavailable as e:
        return Response(
            content=f"PDF 渲染功能不可用——{str(e)}（請見 README 安裝指引）",
            status_code=503, media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record_id}-{role_id}.report.pdf"'},
    )
