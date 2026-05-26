"""安全工具：個別連結簽章 token + CSRF token。

設計（research D3/D5）：
- 個別連結用 itsdangerous URLSafeSerializer 簽章 (match_id, role_id) → 無狀態、不可偽造、不可枚舉
- CSRF 用綁 session 的隨機 token，雙重提交比對
皆只依賴 itsdangerous（純 Python），不引入 DB。
"""

from __future__ import annotations

import os
import secrets

from itsdangerous import BadSignature, URLSafeSerializer

_ROLE_LINK_SALT = "role-link"


def _secret() -> str:
    """讀 SESSION_SECRET；本機開發給預設，production 應由環境變數提供。"""
    return os.environ.get("SESSION_SECRET", "dev-only-insecure-secret-change-me")


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(_secret(), salt=_ROLE_LINK_SALT)


def sign_role_token(match_id: str, role_id: str) -> str:
    """把 (match_id, role_id) 簽成不可偽造的 token。"""
    return _serializer().dumps([match_id, role_id])


def verify_role_token(token: str) -> tuple[str, str] | None:
    """驗章成功回 (match_id, role_id)；竄改 / 亂猜 / 格式錯 → None。"""
    try:
        data = _serializer().loads(token)
    except BadSignature:
        return None
    except Exception:
        return None
    if (
        isinstance(data, list)
        and len(data) == 2
        and all(isinstance(x, str) for x in data)
    ):
        return data[0], data[1]
    return None


# ── CSRF ─────────────────────────────────────────────────────────────

def generate_csrf() -> str:
    """產生一個 CSRF token（放進 session）。"""
    return secrets.token_urlsafe(32)


def validate_csrf(session_token: str | None, form_token: str | None) -> bool:
    """雙重提交比對：session 與 form 的 token 都在且相等才通過。"""
    if not session_token or not form_token:
        return False
    return secrets.compare_digest(session_token, form_token)
