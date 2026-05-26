"""Google OAuth 登入 + session 身分。

設計（research D1/D2）：Authlib 接 Google OIDC；登入後把 email 寫進簽章 cookie session
（Starlette SessionMiddleware），無伺服器端 session 儲存、無 DB。

測試策略：callback 用 `oauth.google.authorize_access_token` 取 userinfo；
測試以 monkeypatch 該方法回傳假 userinfo，不打真 Google。
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from matcher.web.security import generate_csrf

_oauth = None  # 延遲初始化（avoid import-time env requirement）


def session_secret() -> str:
    """簽章 session cookie 的金鑰。production 缺值時應由部署者提供。"""
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    # 本機開發 fallback（非 production）
    return "dev-only-insecure-secret-change-me"


def add_session_middleware(app) -> None:
    """掛上簽章 cookie session（Secure / HttpOnly / SameSite=Lax）。"""
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret(),
        session_cookie="matcher_session",
        https_only=os.environ.get("MATCHER_INSECURE_COOKIE") != "1",  # 測試/本機可關
        same_site="lax",
    )


def get_oauth():
    """延遲建立 Authlib OAuth registry（Google）。"""
    global _oauth
    if _oauth is None:
        from authlib.integrations.starlette_client import OAuth
        oauth = OAuth()
        oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            client_kwargs={"scope": "openid email profile"},
        )
        _oauth = oauth
    return _oauth


def current_email(request: Request) -> Optional[str]:
    """目前登入者 email；未登入回 None。"""
    try:
        return request.session.get("email")
    except (AssertionError, AttributeError):
        # SessionMiddleware 未掛載（理論上不會）
        return None


def login_user(request: Request, email: str) -> None:
    """把使用者寫進 session，並確保有 CSRF token。"""
    request.session["email"] = email
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = generate_csrf()


def logout_user(request: Request) -> None:
    request.session.clear()


def require_login(request: Request) -> str:
    """FastAPI 依賴：未登入 → 拋出導向登入的例外；登入回 email。"""
    email = current_email(request)
    if not email:
        from fastapi import HTTPException
        # 303 See Other：未登入導向登入頁（強制 GET），帶 next
        raise HTTPException(
            status_code=303,
            headers={"Location": f"/login?next={request.url.path}"},
        )
    return email


def csrf_token(request: Request) -> str:
    """取得（或產生）目前 session 的 CSRF token，供樣板嵌入表單。"""
    try:
        token = request.session.get("csrf_token")
        if not token:
            token = generate_csrf()
            request.session["csrf_token"] = token
        return token
    except (AssertionError, AttributeError):
        return ""
