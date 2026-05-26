"""最小記憶體 rate-limit（FR-016）。

開放任何 Google 帳號登入 + 公開網路 → 對敏感端點加基本限流，降低濫用。
單機記憶體計數（重啟歸零）；多副本部署需共享儲存，屬階段 5 部署範疇。
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request

# key（ip + bucket）→ 最近請求時間戳 deque
_HITS: dict[str, deque] = {}


def _client_ip(request: Request) -> str:
    # 反向代理後取 X-Forwarded-For 首段；否則用連線 IP
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, max_hits: int, window_sec: float):
    """回傳一個 FastAPI 依賴：同 IP 在 window 內超過 max_hits 次 → 429。"""

    def _dep(request: Request) -> None:
        now = time.monotonic()
        key = f"{bucket}:{_client_ip(request)}"
        dq = _HITS.setdefault(key, deque())
        # 清掉視窗外的
        while dq and now - dq[0] > window_sec:
            dq.popleft()
        if len(dq) >= max_hits:
            raise HTTPException(status_code=429, detail="請求太頻繁，請稍後再試。")
        dq.append(now)

    return _dep


def reset() -> None:
    """測試用：清空計數。"""
    _HITS.clear()
