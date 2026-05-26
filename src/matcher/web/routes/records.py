"""媒合紀錄列表路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from matcher.template_loader import TemplateRegistry
from matcher.web.auth import require_login
from matcher.web.store import MatchStore

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/matches")
async def records_list(request: Request, email: str = Depends(require_login)):
    store = MatchStore()
    records = store.list(limit=50, owner=email)
    # 取得模板名稱以顯示
    reg = TemplateRegistry()
    template_names: dict = {}
    for tid in reg.list_ids():
        template_names[tid] = reg.get(tid).name
    mechanism_labels = {"M0": "純抽籤", "M1": "輪流挑", "M2": "依志願先後填滿"}
    return _templates(request).TemplateResponse(
        request, "records_list.html",
        {"records": records, "template_names": template_names,
         "mechanism_labels": mechanism_labels},
    )
