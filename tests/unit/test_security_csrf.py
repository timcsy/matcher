"""Feature 014：CSRF token。"""

from __future__ import annotations

from matcher.web.security import generate_csrf, validate_csrf


def test_generated_token_nonempty_and_unique():
    a = generate_csrf()
    b = generate_csrf()
    assert a and b and a != b


def test_matching_tokens_pass():
    t = generate_csrf()
    assert validate_csrf(t, t) is True


def test_mismatch_or_missing_rejected():
    t = generate_csrf()
    assert validate_csrf(t, "other") is False
    assert validate_csrf(None, t) is False
    assert validate_csrf(t, None) is False
    assert validate_csrf(None, None) is False
