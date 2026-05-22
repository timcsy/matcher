"""媒合紀錄列表路由。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from matcher.template_loader import TemplateRegistry
from matcher.web.store import MatchStore

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/matches")
async def records_list(request: Request):
    store = MatchStore()
    records = store.list(limit=50)
    # 取得模板名稱以顯示
    reg = TemplateRegistry()
    template_names: dict = {}
    for tid in reg.list_ids():
        template_names[tid] = reg.get(tid).name
    return _templates(request).TemplateResponse(
        request, "records_list.html",
        {"records": records, "template_names": template_names},
    )
