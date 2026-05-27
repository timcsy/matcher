"""Feature 017：安全加固的純函式單元測試。"""

from __future__ import annotations

import pytest

from matcher.web.routes.auth import _email_allowed, _safe_next
from matcher.web.security import (
    sign_role_token,
    verify_role_token,
)
from matcher.web.store import safe_fs_id


@pytest.mark.parametrize("bad", [
    "https://evil.example", "//evil.example", "/\\evil", "javascript:alert(1)",
    "http://x", "ftp://x", "", None,
])
def test_safe_next_rejects_external(bad):
    assert _safe_next(bad) == "/"


@pytest.mark.parametrize("good", ["/", "/matches", "/match/new", "/templates/x"])
def test_safe_next_keeps_local(good):
    assert _safe_next(good) == good


def test_email_allowed_empty_env_allows_all(monkeypatch):
    monkeypatch.delenv("ALLOWED_EMAIL_DOMAINS", raising=False)
    assert _email_allowed("anyone@gmail.com") is True


def test_email_allowed_restricts_to_domains(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "school.edu, ccsh.tp.edu.tw")
    assert _email_allowed("teacher@school.edu") is True
    assert _email_allowed("a@CCSH.TP.EDU.TW") is True  # 不分大小寫
    assert _email_allowed("stranger@gmail.com") is False
    assert _email_allowed("no-at-sign") is False


@pytest.mark.parametrize("bad", [
    "../etc/passwd", "a/b", "a\\b", "..", "", " x", "x\x00y",
])
def test_safe_fs_id_rejects_traversal(bad):
    with pytest.raises(ValueError):
        safe_fs_id(bad)


def test_safe_fs_id_accepts_normal_ids():
    assert safe_fs_id("2026-05-27T08-20-00-deadbeef") == "2026-05-27T08-20-00-deadbeef"
    assert safe_fs_id("teacher-class") == "teacher-class"


def test_role_token_roundtrip():
    tok = sign_role_token("m1", "R001")
    assert verify_role_token(tok) == ("m1", "R001")


def test_role_token_tampered_rejected():
    tok = sign_role_token("m1", "R001")
    assert verify_role_token(tok + "x") is None
    assert verify_role_token("not-a-token") is None


def test_role_token_expires(monkeypatch):
    tok = sign_role_token("m1", "R001")
    # 效期設 -1 秒 → 必定過期 → None（不依賴測試執行時間）
    monkeypatch.setenv("ROLE_TOKEN_MAX_AGE", "-1")
    assert verify_role_token(tok) is None
