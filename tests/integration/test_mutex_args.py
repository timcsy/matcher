"""Polish：--template / --template-file / --rules 三組互斥（SC-008）。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]

ROSTER = ROOT / "examples" / "teacher-class" / "roster.yaml"
RULES = ROOT / "examples" / "teacher-class" / "rules.yaml"


def test_template_and_rules_mutex():
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--rules", str(RULES),
        "--roster", str(ROSTER),
        "--seed", "1",
    ])
    assert r.exit_code == 2
    assert "互斥" in (r.output + (r.stderr or ""))


def test_template_and_template_file_mutex(tmp_path: Path):
    # 先匯出一個檔案
    runner.invoke(app, ["template", "export", "teacher-class", "--output", str(tmp_path / "t.yaml")])
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--template-file", str(tmp_path / "t.yaml"),
        "--roster", str(ROSTER),
        "--seed", "1",
    ])
    assert r.exit_code == 2
    assert "互斥" in (r.output + (r.stderr or ""))


def test_no_source_provided():
    r = runner.invoke(app, [
        "run",
        "--roster", str(ROSTER),
        "--seed", "1",
    ])
    assert r.exit_code == 2
    assert "請提供" in (r.output + (r.stderr or ""))
