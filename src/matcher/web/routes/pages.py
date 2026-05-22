"""頁面路由：首頁、模板列表、模板詳情。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from matcher.errors import TemplateNotFound
from matcher.template_loader import TemplateRegistry

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/")
async def index(request: Request):
    return _templates(request).TemplateResponse(request, "index.html", {})


@router.get("/templates")
async def templates_list(request: Request):
    reg = TemplateRegistry()
    items = [reg.get(tid) for tid in reg.list_ids()]
    return _templates(request).TemplateResponse(
        request, "templates_list.html", {"templates": items}
    )


@router.get("/templates/{template_id}")
async def template_detail(request: Request, template_id: str):
    reg = TemplateRegistry()
    try:
        tpl = reg.get(template_id)
    except TemplateNotFound as e:
        return _templates(request).TemplateResponse(
            request,
            "error_page.html",
            {"error_type": "TemplateNotFound", "error_message": str(e)},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        request, "template_detail.html", {"tpl": tpl}
    )
