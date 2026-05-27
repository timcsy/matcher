"""稽核 / PDF 下載路由：完整 audit、個別 audit 子集、admin + individual PDF。

從 match.py 拆出（Feature 017）。三組 /r/{token} 下載端點共用 _record_participant_from_token
做「驗 token → 取 record → 參與者存在」的重複檢查。授權檢查 _owner_or_403 由 match.py 提供。
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from matcher.errors import TemplateNotFound
from matcher.template_loader import TemplateRegistry
from matcher.web.auth import require_login
from matcher.web.errors import MatchRecordNotFound
from matcher.web.individual import build_individual_audit_subset
from matcher.web.pdf import PdfRenderUnavailable, render_match_report_pdf
from matcher.web.routes.match import _owner_or_403
from matcher.web.security import verify_participant_token
from matcher.web.store import MatchStore

router = APIRouter()


def _record_participant_from_token(token: str):
    """驗 token → 取 record → 確認參與者存在；任一失敗拋 HTTPException(404)。回 (record, participant_id)。"""
    verified = verify_participant_token(token)
    if verified is None:
        raise HTTPException(status_code=404, detail="連結無效")
    record_id, participant_id = verified
    try:
        record = MatchStore().get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="無個別查詢資料")
    participant_exists = any(
        r["id"] == participant_id for r in record.audit.get("roster_snapshot", {}).get("participants", [])
    )
    if not participant_exists:
        raise HTTPException(status_code=404, detail="找不到對應參與者")
    return record, participant_id


def _individual_audit_payload(record, participant_id: str) -> str:
    subset = build_individual_audit_subset(record.audit, participant_id)
    return json.dumps(subset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _audit_json_response(record_id: str, participant_id: str, payload: str) -> Response:
    return Response(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record_id}-{participant_id}.individual.json"'},
    )


@router.get("/match/{record_id}/participant/{participant_id}/audit.json")
async def individual_audit_download(request: Request, record_id: str, participant_id: str,
                                    email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次配對執行失敗，無個別查詢資料")
    participant_exists = any(
        r["id"] == participant_id for r in record.audit.get("roster_snapshot", {}).get("participants", [])
    )
    if not participant_exists:
        raise HTTPException(status_code=404, detail="您不在這次配對的清單中")
    return _audit_json_response(record_id, participant_id, _individual_audit_payload(record, participant_id))


@router.get("/r/{token}/audit.json")
async def individual_audit_by_token(request: Request, token: str):
    record, participant_id = _record_participant_from_token(token)
    return _audit_json_response(record.id, participant_id, _individual_audit_payload(record, participant_id))


@router.get("/match/{record_id}/audit")
async def download_audit(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    record = store.get(record_id)
    _owner_or_403(request, record)
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該配對執行失敗，無稽核紀錄可下載")
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
async def download_report_pdf(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)

    # 失敗 record 也能出失敗版 PDF；audit 為 None 時樣板會走 failed 分支
    audit_for_pdf = record.audit if record.audit is not None else {
        "assignment": {}, "roster_snapshot": {"participants": [], "targets": []}, "mechanism": "M0",
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


def _individual_pdf_response(record, participant_id: str):
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次配對執行失敗，無個別查詢資料")
    participant_exists = any(
        r["id"] == participant_id for r in record.audit.get("roster_snapshot", {}).get("participants", [])
    )
    if not participant_exists:
        raise HTTPException(status_code=404, detail="您不在這次配對的清單中")
    try:
        tpl = TemplateRegistry().get(record.template_id)
    except TemplateNotFound:
        tpl = None
    try:
        pdf_bytes = render_match_report_pdf(
            record.audit, record_meta=_record_meta_for_pdf(record),
            participant_id=participant_id, template=tpl,
        )
    except PdfRenderUnavailable as e:
        return Response(
            content=f"PDF 渲染功能不可用——{str(e)}（請見 README 安裝指引）",
            status_code=503, media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record.id}-{participant_id}.report.pdf"'},
    )


@router.get("/match/{record_id}/participant/{participant_id}/report.pdf")
async def download_individual_report_pdf(request: Request, record_id: str, participant_id: str,
                                         email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)
    return _individual_pdf_response(record, participant_id)


@router.get("/r/{token}/report.pdf")
async def individual_report_pdf_by_token(request: Request, token: str):
    record, participant_id = _record_participant_from_token(token)
    return _individual_pdf_response(record, participant_id)
