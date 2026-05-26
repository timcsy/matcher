"""Feature 014：.env 自動載入（純標準庫）。"""

from __future__ import annotations

import os
from pathlib import Path

from matcher.web.app import load_dotenv


def test_loads_env_file(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        'FOO_VAR=hello\nBAR_VAR="quoted value"\n# comment\n\nBAZ_VAR=42\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FOO_VAR", raising=False)
    monkeypatch.delenv("BAR_VAR", raising=False)
    monkeypatch.delenv("BAZ_VAR", raising=False)
    load_dotenv()
    assert os.environ["FOO_VAR"] == "hello"
    assert os.environ["BAR_VAR"] == "quoted value"
    assert os.environ["BAZ_VAR"] == "42"


def test_setdefault_does_not_override_existing(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text("ALREADY_SET=from_env_file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALREADY_SET", "from_shell")
    load_dotenv()
    # 已存在的不被 .env 覆蓋
    assert os.environ["ALREADY_SET"] == "from_shell"


def test_no_env_file_is_noop(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    load_dotenv()  # 不應拋例外
