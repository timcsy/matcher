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


# 內容安全政策（CSP）：
#   - script 不允許 inline（擋反射型 XSS 注入的 <script>）；保留 'unsafe-eval'
#     因 Alpine.js / Tailwind Play CDN 在瀏覽器端需要 Function 求值。
#   - 允許的外部 script 來源限於本專案實際使用的三個 CDN。
#   - style 允許 'unsafe-inline'（樣板大量 inline style= 與 Tailwind 動態注入）。
#   - frame-ancestors 'none' + X-Frame-Options DENY：防點擊劫持。
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data:; "
    "connect-src 'self' https://cdn.tailwindcss.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def _install_security_headers(app: FastAPI) -> None:
    """為所有回應加上安全標頭（公開網路 + 學生個資的基本加固）。"""
    import os

    # 僅在 https 部署（非本機 insecure 模式）才送 HSTS，避免本機 http 被瀏覽器鎖成 https
    hsts_on = os.environ.get("MATCHER_INSECURE_COOKIE") != "1"

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("Content-Security-Policy", _CSP)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        if hsts_on:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def _check_secret() -> None:
    """SESSION_SECRET 為開發預設值時：production 拒絕啟動、其餘大聲警告。

    SESSION_SECRET 同時簽 session cookie 與個別連結 token——用預設值＝兩者皆可偽造。
    以 MATCHER_ENV=production 作為「正式部署」訊號，避免誤用預設金鑰上線。
    """
    import logging
    import os

    from matcher.web.security import DEV_SECRET

    if os.environ.get("SESSION_SECRET", DEV_SECRET) == DEV_SECRET:
        if os.environ.get("MATCHER_ENV") == "production":
            raise RuntimeError(
                "SESSION_SECRET 未設定或仍為開發預設值，production 不得啟動。"
                "請設定一個長亂碼："
                'python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        logging.getLogger("matcher").warning(
            "SESSION_SECRET 使用開發預設值——session 與個別連結 token 皆可被偽造，"
            "請勿用於正式部署。"
        )


def create_app() -> FastAPI:
    load_dotenv()
    _check_secret()
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

    _install_security_headers(app)

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
