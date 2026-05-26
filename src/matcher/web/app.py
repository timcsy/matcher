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


def load_dotenv() -> None:
    """從 cwd 往上找 .env，注入環境變數（純標準庫；setdefault 不覆蓋已存在者）。

    setdefault 語意確保：已由 shell / 測試 conftest 設好的變數不會被 .env 蓋掉。
    """
    import os

    cur = Path.cwd()
    for d in [cur, *cur.parents][:5]:
        env_path = d / ".env"
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
        return


def create_app() -> FastAPI:
    load_dotenv()
    app = FastAPI(title="matcher", openapi_url=None)

    static_dir = _resources_dir("static")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates_dir = _resources_dir("templates")
    templates = Jinja2Templates(directory=str(templates_dir))

    # Jinja2 filter：規則描述代名詞替換
    from matcher.web.humanize import humanize_rule_description
    templates.env.filters["humanize_rule"] = humanize_rule_description

    # Jinja2 filter：ISO timestamp → 「YYYY-MM-DD HH:MM」本地時區
    from datetime import datetime
    def _format_local(iso_str: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return iso_str
    templates.env.filters["local_time"] = _format_local

    # Jinja2 filter：物件 → JSON，保留中文可讀 + HTML 跳脫（可安全放進單引號屬性給 Alpine x-data）
    import json as _json
    from markupsafe import Markup, escape as _escape
    def _tojson_attr(obj) -> Markup:
        return Markup(_escape(_json.dumps(obj, ensure_ascii=False)))
    templates.env.filters["tojson_attr"] = _tojson_attr

    # Jinja2 全域：登入者 email + CSRF token（樣板可直接用 current_email(request) / csrf_token(request)）
    from matcher.web.auth import current_email, csrf_token
    templates.env.globals["current_email"] = current_email
    templates.env.globals["csrf_token"] = csrf_token

    app.state.templates = templates

    # session middleware（簽章 cookie，Secure/HttpOnly/SameSite）
    from matcher.web.auth import add_session_middleware
    add_session_middleware(app)

    # Routes — 延遲匯入以避免循環
    from matcher.web.routes import auth, match, pages, records

    app.include_router(auth.router)
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
