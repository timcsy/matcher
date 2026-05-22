"""媒合路由：新建媒合（含向導）、執行、結果頁、下載 audit。"""

from __future__ import annotations

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
from matcher.web.individual import build_individual_audit_subset
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIMES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",  # 某些瀏覽器對 .xlsx 仍回 ms-excel
}


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/match/new")
async def new_match(request: Request, template_id: Optional[str] = None):
    reg = TemplateRegistry()
    items = [reg.get(tid) for tid in reg.list_ids()]
    return _templates(request).TemplateResponse(
        request, "new_match.html",
        {"templates": items, "selected_id": template_id},
    )


@router.post("/match/run")
async def run(
    request: Request,
    template_id: str = Form(...),
    seed: int = Form(...),
    roster: UploadFile = File(...),
):
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
    try:
        reg = TemplateRegistry()
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
        mechanism="M0",
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

            result = run_match(MatcherInput(
                ruleset=tpl.ruleset,
                roster=ro,
                seed=seed,
                preferences=None,
                mechanism="M0",
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


@router.get("/match/{record_id}")
async def match_detail(request: Request, record_id: str):
    store = MatchStore()
    record = store.get(record_id)

    roles_for_links: list = []
    if record.status == "success" and record.audit:
        roles_for_links = [
            {"id": r["id"], "name": r.get("attributes", {}).get("name", r["id"])}
            for r in record.audit.get("roster_snapshot", {}).get("roles", [])
        ]
    return _templates(request).TemplateResponse(
        request, "match_result.html",
        {"record": record, "roles_for_links": roles_for_links},
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
    reg = TemplateRegistry()
    try:
        template = reg.get(record.template_id)
    except TemplateNotFound:
        template = None

    subset = build_individual_audit_subset(record.audit, role_id)

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
