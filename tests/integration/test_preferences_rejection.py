"""US3：preferences 拒絕邏輯。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
F = Path(__file__).resolve().parents[1] / "fixtures" / "edge_cases"


def _invoke(*args: str):
    return runner.invoke(app, list(args))


def test_nonempty_preferences_rejected():
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
        "--seed", "1",
        "--preferences", str(F / "preferences_nonempty.yaml"),
    )
    assert r.exit_code == 17
    msg = r.output + (r.stderr or "")
    assert "純抽籤" in msg
    assert "不接受志願輸入" in msg
    assert "輪流挑" in msg or "依志願先後填滿" in msg


def test_empty_preferences_passes():
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
        "--seed", "1",
        "--preferences", str(F / "preferences_empty.yaml"),
        "--output", "/tmp/test_pref_empty.json",
    )
    assert r.exit_code == 0, r.output


def test_no_preferences_flag_passes(tmp_path: Path):
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
        "--seed", "1",
        "--output", str(tmp_path / "audit.json"),
    )
    assert r.exit_code == 0, r.output
