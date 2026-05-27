"""安全工具：個別連結簽章 token + CSRF token。

設計（research D3/D5）：
- 個別連結用 itsdangerous URLSafeSerializer 簽章 (match_id, participant_id) → 無狀態、不可偽造、不可枚舉
- CSRF 用綁 session 的隨機 token，雙重提交比對
皆只依賴 itsdangerous（純 Python），不引入 DB。
"""

from __future__ import annotations

import os
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

_PARTICIPANT_LINK_SALT = "participant-link"

# 預設個別連結效期（秒）；可由 PARTICIPANT_TOKEN_MAX_AGE 覆寫。
# 預設 180 天：涵蓋一學期，讓家長 / 老師的連結不會用到一半失效，
# 又不至於永久有效（過期可重發）。
DEFAULT_PARTICIPANT_TOKEN_MAX_AGE = 180 * 24 * 3600

# 已知不安全的開發預設金鑰（production 不應使用）
DEV_SECRET = "dev-only-insecure-secret-change-me"


def _secret() -> str:
    """讀 SESSION_SECRET；本機開發給預設，production 應由環境變數提供。"""
    return os.environ.get("SESSION_SECRET", DEV_SECRET)


def _participant_token_max_age() -> int:
    try:
        return int(os.environ.get("PARTICIPANT_TOKEN_MAX_AGE", DEFAULT_PARTICIPANT_TOKEN_MAX_AGE))
    except ValueError:
        return DEFAULT_PARTICIPANT_TOKEN_MAX_AGE


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret(), salt=_PARTICIPANT_LINK_SALT)


def sign_participant_token(match_id: str, participant_id: str) -> str:
    """把 (match_id, participant_id) 簽成不可偽造的 token（含時戳，可設定效期）。"""
    return _serializer().dumps([match_id, participant_id])


def verify_participant_token(token: str) -> tuple[str, str] | None:
    """驗章成功回 (match_id, participant_id)；竄改 / 亂猜 / 格式錯 / 過期 → None。"""
    try:
        data = _serializer().loads(token, max_age=_participant_token_max_age())
    except BadSignature:
        return None
    except Exception:
        # 含 SignatureExpired（itsdangerous 子類）：過期一律當無效
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
