"""pytest root conftest：跨平台環境設定。"""

from __future__ import annotations

import os
import platform


def pytest_configure(config):
    """macOS：為 WeasyPrint 設定 DYLD_FALLBACK_LIBRARY_PATH 以找到 Homebrew 安裝的 libgobject 等。

    非 macOS 平台或已設定者跳過。Linux 通常透過 ld.so 自動找到 /usr/lib/x86_64-linux-gnu/。
    """
    if platform.system() == "Darwin":
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        brew_lib = "/opt/homebrew/lib"
        if brew_lib not in existing:
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{brew_lib}:{existing}" if existing else brew_lib
            )
    # Feature 014：TestClient 走 http，session cookie 不能設 Secure，否則不會被保存
    os.environ.setdefault("MATCHER_INSECURE_COOKIE", "1")
    os.environ.setdefault("SESSION_SECRET", "test-secret-fixed")
