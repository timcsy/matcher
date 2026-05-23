"""US3：study-group + 含 preferences 的名單在 M0 下被拒絕。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_nonempty_preferences_in_roster_rejected(tmp_path: Path):
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster", str(ROOT / "examples" / "study-group" / "roster-with-preferences.yaml"),
        "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 17
    msg = r.output + (r.stderr or "")
    assert "M0 純抽籤" in msg
    assert "不接受志願輸入" in msg
    # 階段 6 改：M1 已啟用，訊息現在指引「改用 --mechanism M1」
    assert ("--mechanism M1" in msg) or ("階段 4" in msg)


def test_empty_preferences_in_roster_passes(tmp_path: Path):
    out = tmp_path / "a.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster", str(ROOT / "examples" / "study-group" / "roster.yaml"),
        "--seed", "2026",
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    assert out.exists()
