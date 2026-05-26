"""Feature 014 測試共用：以 monkeypatch 模擬 Google OAuth callback 完成登入。"""

from __future__ import annotations


def fake_oauth_login(monkeypatch, email: str):
    """讓 get_oauth().google.authorize_access_token 回傳指定 email 的 userinfo。"""
    import matcher.web.auth as auth_mod

    class _FakeGoogle:
        async def authorize_access_token(self, request):
            return {"userinfo": {"email": email}}

        async def authorize_redirect(self, request, uri):
            from starlette.responses import RedirectResponse
            return RedirectResponse(url="/auth/callback", status_code=303)

    class _FakeOAuth:
        google = _FakeGoogle()

    monkeypatch.setattr(auth_mod, "get_oauth", lambda: _FakeOAuth())
    # 也 patch routes.auth 內已綁定的名稱
    import matcher.web.routes.auth as routes_auth
    monkeypatch.setattr(routes_auth, "get_oauth", lambda: _FakeOAuth())


def login(client, monkeypatch, email: str):
    """完成一次登入；之後該 client 的請求都帶 session。回傳 callback response。"""
    fake_oauth_login(monkeypatch, email)
    return client.get("/auth/callback", follow_redirects=False)
