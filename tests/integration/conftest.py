"""Feature 013：tests/integration 共用 fixture。

`autouse` 攔截 TestClient.post 到 /match/run 的呼叫，
若呼叫者提供 `roster` 但未提供 `targets_yaml`，且 form data 的 template_id 是內建範本，
則自動附上對應的 sidecar bytes。避免逐一改 35 個測試呼叫點。

新撰寫的測試若要明確測試「缺 sidecar」，請手動傳 targets_yaml=("", b"", "application/x-yaml")
或 form 帶 `_skip_auto_sidecar=1`。
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SIDECARS = {
    "teacher-class": (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes(),
    "study-group": (ROOT / "examples" / "study-group" / "roster.targets.yaml").read_bytes(),
}

# Feature 014：auth 行為由這些測試檔自己驗證，不套用「自動登入」bypass
_REAL_AUTH_MODULES = {
    "test_web_auth_flow",
    "test_web_auth_ownership",
    "test_web_token_link",
    "test_web_template_visibility",
}


@pytest.fixture(autouse=True)
def _auto_login(request, monkeypatch):
    """Feature 014：既有 web 測試未登入，加 require_login 後會 302。

    autouse 把 current_email 與 CSRF 驗證 patch 成「已登入的測試使用者 + CSRF 永過」，
    讓既有測試沿用。auth 專屬測試檔（_REAL_AUTH_MODULES）opt-out 以驗真實行為。
    """
    mod = request.module.__name__.rsplit(".", 1)[-1]
    if mod in _REAL_AUTH_MODULES:
        yield
        return
    import matcher.web.auth as auth_mod
    import matcher.web.routes.match as match_mod
    monkeypatch.setattr(auth_mod, "current_email", lambda request: "test@example.com")
    monkeypatch.setattr(match_mod, "current_email", lambda request: "test@example.com")
    monkeypatch.setattr(match_mod, "validate_csrf", lambda a, b: True)
    yield


@pytest.fixture(autouse=True)
def _auto_inject_sidecar(monkeypatch):
    """攔截 TestClient.post，自動補 targets_yaml sidecar 給內建範本上傳。"""
    from starlette.testclient import TestClient as _TC
    original_post = _TC.post

    def patched_post(self, url, *args, **kwargs):
        if url == "/match/run":
            files = kwargs.get("files")
            data = kwargs.get("data") or {}
            if (
                files is not None
                and "roster" in files
                and "targets_yaml" not in files
            ):
                tpl_id = data.get("template_id") if isinstance(data, dict) else None
                skip = isinstance(data, dict) and data.get("_skip_auto_sidecar")
                if tpl_id in SIDECARS and not skip:
                    new_files = dict(files)
                    new_files["targets_yaml"] = (
                        "roster.targets.yaml",
                        SIDECARS[tpl_id],
                        "application/x-yaml",
                    )
                    kwargs["files"] = new_files
        return original_post(self, url, *args, **kwargs)

    monkeypatch.setattr(_TC, "post", patched_post)
    yield
