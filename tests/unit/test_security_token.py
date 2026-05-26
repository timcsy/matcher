"""Feature 014：個別連結簽章 token。"""

from __future__ import annotations

from matcher.web.security import sign_role_token, verify_role_token


def test_sign_verify_round_trip():
    token = sign_role_token("2026-abc", "T01")
    assert verify_role_token(token) == ("2026-abc", "T01")


def test_tampered_token_rejected():
    token = sign_role_token("2026-abc", "T01")
    # 改動 token 任一字元 → 驗章失敗
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert verify_role_token(bad) is None


def test_random_garbage_rejected():
    assert verify_role_token("not-a-real-token") is None
    assert verify_role_token("") is None


def test_token_binds_single_role():
    """A 角色的 token 解出只含 A，無法挪用看 B。"""
    a = sign_role_token("M1", "A")
    assert verify_role_token(a) == ("M1", "A")
    # 不同角色簽出不同 token
    b = sign_role_token("M1", "B")
    assert a != b


def test_token_unguessable_without_secret(monkeypatch):
    """換掉 secret 後，舊 token 驗不過（證明安全性來自 secret）。"""
    token = sign_role_token("M1", "A")
    monkeypatch.setenv("SESSION_SECRET", "a-totally-different-secret")
    assert verify_role_token(token) is None
