"""US2：M1 拒絕邏輯。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_m1_with_empty_preferences_rejected(tmp_path: Path):
    """M1 + 全空 prefs → exit 40。"""
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster", str(ROOT / "examples" / "study-group" / "roster.yaml"),
        "--seed", "1",
        "--mechanism", "M1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 40
    msg = r.output + (r.stderr or "")
    assert "M1 需要至少一位角色提供志願" in msg
    assert ("--mechanism M0" in msg) or ("mechanism=M0" in msg)


def test_unsupported_mechanism_value(tmp_path: Path):
    """--mechanism M5 → exit 2。"""
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster", str(ROOT / "examples" / "study-group" / "roster.yaml"),
        "--seed", "1",
        "--mechanism", "M5",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 2
    msg = r.output + (r.stderr or "")
    assert "不支援的機制" in msg
    assert "M5" in msg
    assert "M0、M1" in msg


def test_m0_with_nonempty_prefs_still_rejected(tmp_path: Path):
    """M0 + roster 含非空 prefs → exit 17（向後相容）。"""
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "1",
        "--mechanism", "M0",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 17
    msg = r.output + (r.stderr or "")
    assert "M0 純抽籤" in msg
