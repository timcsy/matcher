"""US2：M2 拒絕邏輯。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_m2_with_empty_preferences_rejected(tmp_path: Path):
    """M2 + 全空 prefs → exit 40，訊息含 M2。"""
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster", str(ROOT / "examples" / "study-group" / "roster.yaml"),
        "--seed", "1",
        "--mechanism", "M2",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 40
    msg = r.output + (r.stderr or "")
    assert "「依志願先後填滿」需要至少一位填了志願" in msg


def test_m1_reject_message_still_mentions_m1(tmp_path: Path):
    """M1 + 全空 prefs 訊息現在動態填入「M1」。"""
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
    assert "「輪流挑」需要至少一位填了志願" in msg


def test_unsupported_mechanism_m3(tmp_path: Path):
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "1",
        "--mechanism", "M3",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 2
    msg = r.output + (r.stderr or "")
    assert "不支援的抽籤方式" in msg
    assert "M3" in msg
    assert "純抽籤" in msg
