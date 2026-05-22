"""FastAPI app 工廠。"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from matcher.web.errors import MatchRecordNotFound, UploadInvalidMime, UploadTooLarge


def _resources_dir(name: str) -> Path:
    """以 importlib.resources 解析套件內資源路徑。"""
    return Path(str(resources.files("matcher.web") / name))


def create_app() -> FastAPI:
    app = FastAPI(title="matcher", openapi_url=None)

    static_dir = _resources_dir("static")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates_dir = _resources_dir("templates")
    templates = Jinja2Templates(directory=str(templates_dir))

    # Jinja2 filter：規則描述代名詞替換
    from matcher.web.humanize import humanize_rule_description
    templates.env.filters["humanize_rule"] = humanize_rule_description

    app.state.templates = templates

    # Routes — 延遲匯入以避免循環
    from matcher.web.routes import match, pages, records

    app.include_router(pages.router)
    app.include_router(match.router)
    app.include_router(records.router)

    @app.exception_handler(MatchRecordNotFound)
    async def _record_not_found(request: Request, exc: MatchRecordNotFound) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "error_page.html",
            {"error_type": "MatchRecordNotFound", "error_message": str(exc)},
            status_code=404,
        )

    @app.exception_handler(UploadTooLarge)
    async def _too_large(request: Request, exc: UploadTooLarge) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "error_page.html",
            {"error_type": "UploadTooLarge", "error_message": str(exc)},
            status_code=400,
        )

    @app.exception_handler(UploadInvalidMime)
    async def _invalid_mime(request: Request, exc: UploadInvalidMime) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "error_page.html",
            {"error_type": "UploadInvalidMime", "error_message": str(exc)},
            status_code=400,
        )

    return app


app = create_app()
