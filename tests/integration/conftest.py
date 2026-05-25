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
