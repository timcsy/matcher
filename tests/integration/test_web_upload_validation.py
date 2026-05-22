"""US1：上傳驗證測試。"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def test_upload_too_large(tmp_path: Path):
    c = _client(tmp_path)
    big = io.BytesIO(b"x" * (5 * 1024 * 1024 + 1))  # 5 MB + 1 byte
    r = c.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "1"},
        files={"roster": ("big.csv", big, "text/csv")},
    )
    assert r.status_code == 400
    assert "過大" in r.text


def test_upload_invalid_mime(tmp_path: Path):
    c = _client(tmp_path)
    r = c.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "1"},
        files={"roster": ("bad.txt", io.BytesIO(b"abc"), "text/plain")},
    )
    assert r.status_code == 400
    assert "類型不支援" in r.text


def test_seed_must_be_integer(tmp_path: Path):
    c = _client(tmp_path)
    csv = io.BytesIO(b"id,name,speciality,seniority\nT01,A,B,3\n")
    r = c.post(
        "/match/run",
        data={"template_id": "teacher-class", "seed": "not-an-int"},
        files={"roster": ("r.csv", csv, "text/csv")},
    )
    # FastAPI 表單驗證會回 422
    assert r.status_code in (400, 422)
