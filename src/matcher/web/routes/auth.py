"""登入 / 登出 / OAuth callback 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from matcher.web.auth import current_email, get_oauth, login_user, logout_user
from matcher.web.security import validate_csrf

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/login")
async def login_page(request: Request, next: str = "/"):
    if current_email(request):
        return RedirectResponse(url="/", status_code=303)
    return _templates(request).TemplateResponse(
        request, "login.html", {"next": next, "error": request.query_params.get("error")},
    )


@router.get("/auth/login")
async def auth_login(request: Request, next: str = "/"):
    """啟動 Google OAuth。"""
    request.session["oauth_next"] = next
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

    login_user(request, email)
    nxt = request.session.pop("oauth_next", "/")
    return RedirectResponse(url=nxt or "/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    # CSRF 防護
    form = await request.form()
    if not validate_csrf(request.session.get("csrf_token"), form.get("csrf_token")):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="CSRF 驗證失敗")
    logout_user(request)
    return RedirectResponse(url="/login", status_code=303)
