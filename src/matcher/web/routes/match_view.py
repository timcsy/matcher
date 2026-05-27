"""配對結果檢視路由：admin 結果頁、個別查詢（登入預覽 + /r/{token} 免登入）。

從 match.py 拆出（Feature 017）。共用的 _templates / _owner_or_403 仍由 match.py 提供，
讓 conftest 對 match 模組的 monkeypatch（current_email）持續涵蓋授權檢查。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from matcher.errors import TemplateNotFound
from matcher.web.auth import require_login
from matcher.web.errors import MatchRecordNotFound
from matcher.web.humanize import mechanism_label, preference_rank_display
from matcher.web.individual import build_individual_audit_subset
from matcher.web.routes.match import _owner_or_403, _templates
from matcher.web.security import sign_participant_token, verify_participant_token
from matcher.web.store import MatchStore

router = APIRouter()


@router.get("/match/{record_id}")
async def match_detail(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    record = store.get(record_id)
    _owner_or_403(request, record)

    participants_for_links: list = []
    mechanism = "M0"
    processing_order_display = None
    rank_display_by_participant: dict = {}
    if record.status == "success" and record.audit:
        participants_for_links = [
            {"id": r["id"], "name": r.get("attributes", {}).get("name", r["id"]),
             "token": sign_participant_token(record.id, r["id"])}
            for r in record.audit.get("roster_snapshot", {}).get("participants", [])
        ]
        mechanism = record.audit.get("mechanism", "M0")
        # 處理順序段（M1/M2 才注入；M0 audit.processing_order 為 null）
        po = record.audit.get("processing_order")
        if po:
            name_by_id = {r["id"]: r.get("attributes", {}).get("name", r["id"])
                          for r in record.audit.get("roster_snapshot", {}).get("participants", [])}
            processing_order_display = [(rid, name_by_id.get(rid, rid)) for rid in po]
        # 志願排名欄（M1/M2）
        for entry in record.audit.get("allocation_trace", []):
            display = preference_rank_display(
                mechanism,
                entry.get("preference_rank"),
                entry.get("fallback_random_index"),
            )
            if display is not None:
                rank_display_by_participant[entry["participant_id"]] = display
    return _templates(request).TemplateResponse(
        request, "match_result.html",
        {
            "record": record,
            "participants_for_links": participants_for_links,
            "mechanism": mechanism,
            "mechanism_label": mechanism_label(mechanism),
            "processing_order_display": processing_order_display,
            "rank_display_by_participant": rank_display_by_participant,
        },
    )


def _individual_error(request: Request, message: str) -> Response:
    return _templates(request).TemplateResponse(
        request, "individual_error.html",
        {"message": message},
        status_code=404,
    )


def _render_individual(request: Request, record, participant_id: str):
    """渲染個別查詢頁（被舊 admin 路徑與 /r/{token} 共用）。"""
    if record.status == "failed" or record.audit is None:
        return _individual_error(request, "該次配對執行失敗，無個別查詢資料")

    participant = next(
        (r for r in record.audit.get("roster_snapshot", {}).get("participants", []) if r["id"] == participant_id),
        None,
    )
    if participant is None:
        return _individual_error(request, "您不在這次配對的清單中")

    # 載入模板（用於 humanize 規則描述）
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    reg = _shared_reg()
    try:
        template = reg.get(record.template_id)
    except TemplateNotFound:
        template = None

    subset = build_individual_audit_subset(record.audit, participant_id)

    # US2：志願滿足度
    mechanism = record.audit.get("mechanism", "M0")
    preference_rank = None
    fallback_random_index = None
    for entry in record.audit.get("allocation_trace", []):
        if entry.get("participant_id") == participant_id:
            preference_rank = entry.get("preference_rank")
            fallback_random_index = entry.get("fallback_random_index")
            break
    preferred_count = len(participant.get("preferences", []) or [])

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
            "participant": participant,
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


@router.get("/match/{record_id}/participant/{participant_id}")
async def individual_view(request: Request, record_id: str, participant_id: str,
                          email: str = Depends(require_login)):
    """舊個別路徑：Feature 014 改為僅擁有者（登入）可看（行政預覽用）。
    匿名當事人請改用 /r/{token}。"""
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        return _individual_error(request, "找不到該次配對的紀錄")
    _owner_or_403(request, record)
    return _render_individual(request, record, participant_id)


@router.get("/r/{token}")
async def individual_view_by_token(request: Request, token: str):
    """Feature 014：當事人用不可猜 token 看自己結果，免登入。"""
    verified = verify_participant_token(token)
    if verified is None:
        return _individual_error(request, "連結無效或已失效")
    record_id, participant_id = verified
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        return _individual_error(request, "找不到該次配對的紀錄")
    return _render_individual(request, record, participant_id)
