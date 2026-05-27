"""登入 / 登出 / OAuth callback 路由。"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from matcher.web.auth import current_email, get_oauth, login_user, logout_user
from matcher.web.ratelimit import rate_limit
from matcher.web.security import validate_csrf

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _safe_next(next: str | None) -> str:
    """只接受站內相對路徑，擋開放重導向（//evil、https://evil、javascript: 等）。

    合法：單一前導斜線的路徑（如 /matches、/match/new）。其餘一律退回 "/"。
    """
    if not next or not next.startswith("/") or next.startswith("//") or next.startswith("/\\"):
        return "/"
    return next


def _email_allowed(email: str) -> bool:
    """ALLOWED_EMAIL_DOMAINS（逗號分隔）非空時，只放行這些網域的 email；留空＝放行任何帳號。"""
    raw = os.environ.get("ALLOWED_EMAIL_DOMAINS", "").strip()
    if not raw:
        return True
    allowed = {d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip()}
    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    return domain in allowed


@router.get("/login")
async def login_page(request: Request, next: str = "/"):
    if current_email(request):
        return RedirectResponse(url="/", status_code=303)
    return _templates(request).TemplateResponse(
        request, "login.html",
        {"next": _safe_next(next), "error": request.query_params.get("error")},
    )


@router.get("/auth/login")
async def auth_login(request: Request, next: str = "/",
                     _rl=Depends(rate_limit("auth", 30, 60))):
    """啟動 Google OAuth。"""
    request.session["oauth_next"] = _safe_next(next)
    redirect_uri = request.url_for("auth_callback")
    return await get_oauth().google.authorize_redirect(request, str(redirect_uri))


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    """Google 導回：取 userinfo、寫 session。"""
    try:
        token = await get_oauth().google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/login?error=登入失敗，請再試一次", status_code=303)

    userinfo = token.get("userinfo") if isinstance(token, dict) else None
    email = (userinfo or {}).get("email") if userinfo else None
    if not email:
        return RedirectResponse(url="/login?error=無法取得 Google 帳號資訊", status_code=303)

    if not _email_allowed(email):
        return RedirectResponse(
            url="/login?error=此帳號不在允許的網域內，請用學校帳號登入", status_code=303,
        )

    login_user(request, email)
    nxt = _safe_next(request.session.pop("oauth_next", "/"))
    return RedirectResponse(url=nxt, status_code=303)


@router.post("/logout")
async def logout(request: Request):
    # CSRF 防護
    form = await request.form()
    if not validate_csrf(request.session.get("csrf_token"), form.get("csrf_token")):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="CSRF 驗證失敗")
    logout_user(request)
    return RedirectResponse(url="/login", status_code=303)
